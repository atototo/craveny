"""
DART (금융감독원 전자공시시스템) 크롤러

전자공시시스템의 공시 정보를 수집합니다.
DART Open API 사용: https://opendart.fss.or.kr/
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import requests

from backend.crawlers.base_crawler import NewsArticleData
from backend.config import settings


logger = logging.getLogger(__name__)


class DartCrawler:
    """DART 공시 크롤러"""

    BASE_URL = "https://opendart.fss.or.kr/api"

    # 공시 유형별 한글명
    DISCLOSURE_TYPES = {
        "A001": "정기공시",      # 사업보고서, 반기보고서, 분기보고서
        "A002": "주요사항보고",   # 합병, 분할, 자본 감소 등
        "A003": "발행공시",      # 유상증자, 무상증자, 전환사채 등
        "A004": "지분공시",      # 주식 등의 대량보유 상황 보고
        "A005": "기타공시",      # 기타 법령에 의한 공시
        "A006": "외부감사관련", # 감사보고서 제출
        "A007": "펀드공시",      # 펀드 관련
        "A008": "자산유동화",    # 자산유동화 관련
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DART API 키 (None이면 설정에서 로드)
        """
        self.api_key = api_key or getattr(settings, "DART_API_KEY", None)

        if not self.api_key:
            logger.warning("DART API 키가 설정되지 않았습니다. 공시 크롤링을 사용하려면 DART_API_KEY 환경변수를 설정하세요.")
            logger.warning("API 키 발급: https://opendart.fss.or.kr/")

    def _make_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        """
        DART API 요청

        Args:
            endpoint: API 엔드포인트
            params: 요청 파라미터

        Returns:
            응답 데이터 또는 None
        """
        if not self.api_key:
            logger.error("DART API 키가 없어 요청할 수 없습니다")
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        params["crtfc_key"] = self.api_key

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 에러 체크
            if data.get("status") != "000":
                error_message = data.get("message", "알 수 없는 오류")
                logger.error(f"DART API 오류: {error_message}")
                return None

            return data

        except requests.RequestException as e:
            logger.error(f"DART API 요청 실패: {e}")
            return None

    def fetch_disclosures(
        self,
        corp_code: Optional[str] = None,
        stock_code: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        disclosure_type: Optional[str] = None,
    ) -> List[NewsArticleData]:
        """
        특정 기업의 공시 목록을 가져옵니다.

        Args:
            corp_code: 기업 고유번호 (8자리) - 선택사항
            stock_code: 주식 코드 (6자리) - 선택사항
            start_date: 시작 날짜
            end_date: 종료 날짜
            disclosure_type: 공시 유형 (A001~A008)

        Returns:
            공시 리스트
        """
        # 기본값: 최근 7일
        if not start_date:
            start_date = datetime.now() - timedelta(days=7)
        if not end_date:
            end_date = datetime.now()

        params = {
            "bgn_de": start_date.strftime("%Y%m%d"),
            "end_de": end_date.strftime("%Y%m%d"),
        }

        # corp_code 또는 stock_code 중 하나만 사용
        if corp_code:
            params["corp_code"] = corp_code
        elif stock_code:
            params["corp_code"] = stock_code  # DART API는 corp_code 파라미터에 주식코드도 허용
        else:
            logger.error("corp_code 또는 stock_code 중 하나는 필수입니다")
            return []

        if disclosure_type:
            params["pblntf_ty"] = disclosure_type

        data = self._make_request("list.json", params)

        if not data or "list" not in data:
            return []

        disclosures = []

        for item in data["list"]:
            try:
                # 공시 정보 파싱
                title = item.get("report_nm", "")
                corp_name = item.get("corp_name", "")

                # 공시 내용 요약
                content = f"[{corp_name}] {title}\n\n"
                content += f"공시일: {item.get('rcept_dt', '')}\n"
                content += f"공시 제출인: {item.get('flr_nm', '')}\n"

                # 상세 URL
                rcept_no = item.get("rcept_no", "")
                detail_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                content += f"\n상세보기: {detail_url}"

                # 공시일자 파싱
                rcept_dt = item.get("rcept_dt", "")
                try:
                    published_at = datetime.strptime(rcept_dt, "%Y%m%d")
                except:
                    published_at = datetime.now()

                disclosure = NewsArticleData(
                    title=f"[공시] {title}",
                    content=content,
                    published_at=published_at,
                    source="DART(금융감독원)",
                    company_name=corp_name,
                )

                disclosures.append(disclosure)

            except Exception as e:
                logger.error(f"공시 파싱 실패: {e}")

        logger.info(f"{corp_name} 공시 수집 완료: {len(disclosures)}건")
        return disclosures

    def search_company_by_stock_code(self, stock_code: str) -> Optional[str]:
        """
        주식 코드로 기업 고유번호(corp_code)를 검색합니다.

        Args:
            stock_code: 주식 코드 (6자리)

        Returns:
            기업 고유번호 (8자리) 또는 None
        """
        params = {
            "stock_code": stock_code,
        }

        data = self._make_request("company.json", params)

        if not data:
            return None

        return data.get("corp_code")

    def fetch_disclosures_by_stock_code(
        self,
        stock_code: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        disclosure_type: Optional[str] = None,
    ) -> List[NewsArticleData]:
        """
        주식 코드로 공시를 검색합니다.

        Args:
            stock_code: 주식 코드 (6자리)
            start_date: 시작 날짜
            end_date: 종료 날짜
            disclosure_type: 공시 유형

        Returns:
            공시 리스트
        """
        # 직접 주식 코드로 공시 조회
        return self.fetch_disclosures(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            disclosure_type=disclosure_type,
        )
