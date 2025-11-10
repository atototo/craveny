"""
업종/지수 일자별 데이터 수집기 (KIS API)

KOSPI, KOSDAQ 및 주요 업종 지수의 일봉 데이터를 수집합니다.
"""
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from backend.crawlers.kis_client import get_kis_client
from backend.db.session import SessionLocal
from backend.db.models.market_data import IndexDailyPrice


logger = logging.getLogger(__name__)


class IndexDailyCollector:
    """업종/지수 일자별 데이터 수집기"""

    def __init__(self, batch_size: int = 5):
        """
        Args:
            batch_size: 배치 크기 (동시 수집 개수)
        """
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0

        # 수집 대상 지수 목록 (코드: 이름)
        self.indices = {
            # 주요 지수
            "0001": "KOSPI",
            "1001": "KOSDAQ",
            "2001": "KOSPI200",

            # KOSPI 업종 지수 (17개)
            "1010": "에너지",
            "1011": "화학",
            "1012": "비금속",
            "1013": "철강",
            "1014": "기계",
            "1015": "전기전자",
            "1016": "의료정밀",
            "1017": "운수장비",
            "1018": "유통",
            "1019": "건설",
            "1020": "운수창고",
            "1021": "통신업",
            "1022": "금융",
            "1023": "증권",
            "1024": "보험",
            "1025": "서비스",
            "1026": "제조",
        }

    async def collect_index_daily(
        self,
        index_code: str,
        index_name: str,
        start_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        단일 지수의 일자별 데이터 수집

        Args:
            index_code: 지수 코드
            index_name: 지수명
            start_date: 시작 날짜 (YYYYMMDD, 기본: 오늘)

        Returns:
            수집 결과 딕셔너리
        """
        try:
            client = await get_kis_client()
            logger.info(f"📊 {index_name}({index_code}) 지수 수집 시작")

            # API 호출
            result = await client.get_index_daily_price(
                index_code=index_code,
                start_date=start_date
            )

            if result.get("rt_cd") != "0":
                error_msg = result.get("msg1", "Unknown error")
                logger.error(f"❌ {index_name} API 오류: {error_msg}")
                self.failed_count += 1
                return {"index_code": index_code, "status": "error", "message": error_msg}

            # output2에서 일자별 데이터 추출
            output2 = result.get("output2", [])

            if not output2:
                logger.warning(f"⚠️  {index_name} 데이터 없음")
                return {"index_code": index_code, "status": "no_data", "saved": 0}

            # DB 저장
            saved_count = await self._save_to_db(index_code, index_name, output2)

            self.collected_count += saved_count
            logger.info(f"✅ {index_name}({index_code}) 저장 완료: {saved_count}건")

            return {
                "index_code": index_code,
                "index_name": index_name,
                "status": "success",
                "saved": saved_count
            }

        except Exception as e:
            logger.error(f"❌ {index_name}({index_code}) 수집 실패: {e}", exc_info=True)
            self.failed_count += 1
            return {"index_code": index_code, "status": "error", "message": str(e)}

    async def _save_to_db(
        self,
        index_code: str,
        index_name: str,
        data_list: List[Dict[str, Any]]
    ) -> int:
        """
        지수 데이터 DB 저장

        Args:
            index_code: 지수 코드
            index_name: 지수명
            data_list: API 응답 데이터 리스트 (output2)

        Returns:
            저장된 레코드 수
        """
        db = SessionLocal()
        saved_count = 0

        try:
            for item in data_list:
                try:
                    # 날짜 파싱
                    date_str = item.get("stck_bsop_date")  # YYYYMMDD
                    if not date_str:
                        continue

                    date_obj = datetime.strptime(date_str, "%Y%m%d").date()

                    # 기존 데이터 확인
                    existing = db.query(IndexDailyPrice).filter(
                        IndexDailyPrice.index_code == index_code,
                        IndexDailyPrice.date == date_obj
                    ).first()

                    if existing:
                        continue  # 이미 있으면 스킵

                    # 새 레코드 생성
                    index_daily = IndexDailyPrice(
                        index_code=index_code,
                        index_name=index_name,
                        date=date_obj,
                        open=float(item.get("bstp_nmix_oprc", 0)) or None,
                        high=float(item.get("bstp_nmix_hgpr", 0)) or None,
                        low=float(item.get("bstp_nmix_lwpr", 0)) or None,
                        close=float(item.get("bstp_nmix_prpr", 0)),
                        volume=int(item.get("acml_vol", 0)) or None,
                        trading_value=int(item.get("acml_tr_pbmn", 0)) or None,
                        change=float(item.get("bstp_nmix_prdy_vrss", 0)) or None,
                        change_rate=float(item.get("bstp_nmix_prdy_ctrt", 0)) or None,
                        change_sign=item.get("prdy_vrss_sign"),
                    )

                    db.add(index_daily)
                    saved_count += 1

                except Exception as e:
                    logger.error(f"데이터 파싱 오류: {e} - {item}")
                    continue

            db.commit()
            return saved_count

        except Exception as e:
            db.rollback()
            logger.error(f"❌ DB 저장 실패: {e}", exc_info=True)
            raise

        finally:
            db.close()

    async def collect_today(self) -> Dict[str, Any]:
        """
        오늘 날짜의 전체 지수 데이터 수집

        Returns:
            수집 결과 요약
        """
        logger.info("=" * 80)
        logger.info("📊 업종/지수 일자별 데이터 수집 시작 (당일)")
        logger.info("=" * 80)

        self.collected_count = 0
        self.failed_count = 0

        # 오늘 날짜
        today = datetime.now().strftime("%Y%m%d")

        # 배치 처리
        index_codes = list(self.indices.keys())
        results = []

        for i in range(0, len(index_codes), self.batch_size):
            batch = index_codes[i:i + self.batch_size]
            tasks = [
                self.collect_index_daily(
                    index_code=code,
                    index_name=self.indices[code],
                    start_date=today
                )
                for code in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info("=" * 80)
        logger.info(f"✅ 수집 완료: 성공 {self.collected_count}건, 실패 {self.failed_count}건")
        logger.info("=" * 80)

        return {
            "collected": self.collected_count,
            "failed": self.failed_count,
            "results": results
        }

    async def collect_range(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        max_days: int = 100
    ) -> Dict[str, Any]:
        """
        기간별 전체 지수 데이터 수집 (백필용)

        KIS API는 한 번에 최대 100건을 반환하므로,
        100일 단위로 분할하여 수집합니다.

        Args:
            start_date: 시작 날짜 (YYYYMMDD)
            end_date: 종료 날짜 (YYYYMMDD, 기본: 오늘)
            max_days: 최대 수집 일수 (기본: 100일)

        Returns:
            수집 결과 요약
        """
        logger.info("=" * 80)
        logger.info(f"📊 업종/지수 일자별 데이터 수집 시작 ({start_date} ~ {end_date or 'today'})")
        logger.info("=" * 80)

        self.collected_count = 0
        self.failed_count = 0

        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # 날짜 범위 계산
        start_dt = datetime.strptime(start_date, "%Y%m%d")
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        total_days = (end_dt - start_dt).days + 1

        logger.info(f"📅 총 기간: {total_days}일 (최대 {max_days}일 수집)")

        # 100일 단위로 분할
        results = []
        index_codes = list(self.indices.keys())

        for i in range(0, len(index_codes), self.batch_size):
            batch = index_codes[i:i + self.batch_size]
            tasks = [
                self.collect_index_daily(
                    index_code=code,
                    index_name=self.indices[code],
                    start_date=end_date  # 최신 날짜부터 역순 100일
                )
                for code in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

            # Rate limiting
            await asyncio.sleep(0.5)

        logger.info("=" * 80)
        logger.info(f"✅ 수집 완료: 성공 {self.collected_count}건, 실패 {self.failed_count}건")
        logger.info("=" * 80)

        return {
            "collected": self.collected_count,
            "failed": self.failed_count,
            "results": results
        }
