"""
KIS (한국투자증권) API Client

OAuth 2.0 인증, Rate Limiting, Token 자동 갱신 기능 포함
"""
import logging
import asyncio
import time
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
import redis
from backend.config import settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate Limiter (Sliding Window 알고리즘)"""

    def __init__(self, max_requests: int = 20, window_seconds: float = 1.0):
        """
        Args:
            max_requests: 시간 창 내 최대 요청 수
            window_seconds: 시간 창 (초)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Rate limit 획득 (필요 시 대기)"""
        async with self.lock:
            now = time.time()

            # 시간 창 밖의 요청 제거
            self.requests = [
                req_time for req_time in self.requests
                if now - req_time < self.window_seconds
            ]

            # 제한 확인
            if len(self.requests) >= self.max_requests:
                # 가장 오래된 요청이 만료될 때까지 대기
                oldest = self.requests[0]
                wait_time = self.window_seconds - (now - oldest)

                if wait_time > 0:
                    logger.debug(f"Rate limit 대기: {wait_time:.2f}초")
                    await asyncio.sleep(wait_time)

                # 재확인
                now = time.time()
                self.requests = [
                    req_time for req_time in self.requests
                    if now - req_time < self.window_seconds
                ]

            # 현재 요청 추가
            self.requests.append(now)


class TokenManager:
    """OAuth 2.0 Token 관리자 (싱글톤, Redis 기반)"""

    _instance = None
    _lock = asyncio.Lock()
    REDIS_KEY = "kis:access_token"
    REDIS_EXPIRY_KEY = "kis:token_expires_at"

    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_key: str, app_secret: str, base_url: str, mock_mode: bool):
        # 이미 초기화되었으면 스킵
        if hasattr(self, 'initialized') and self.initialized:
            return

        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url
        self.mock_mode = mock_mode

        # Redis 클라이언트 초기화
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        self.initialized = True
        logger.info("🔑 TokenManager 싱글톤 초기화 완료 (Redis 연동)")

    async def get_access_token(self) -> str:
        """
        Access Token 조회 (필요 시 자동 갱신)

        Redis에서 토큰을 조회하고, 없거나 만료 임박 시 갱신

        Returns:
            유효한 Access Token
        """
        async with TokenManager._lock:
            try:
                # Redis에서 토큰 조회
                access_token = self.redis_client.get(self.REDIS_KEY)
                token_expires_at_str = self.redis_client.get(self.REDIS_EXPIRY_KEY)

                if access_token and token_expires_at_str:
                    token_expires_at = datetime.fromisoformat(token_expires_at_str)
                    remaining = (token_expires_at - datetime.now()).total_seconds()

                    # 만료 5분 전에 갱신
                    if remaining > 300:  # 5분 = 300초
                        logger.debug(f"✅ Redis에서 토큰 조회 (유효시간: {remaining/3600:.1f}시간)")
                        return access_token
                    else:
                        logger.info(f"⏰ 토큰 만료 임박 (남은 시간: {remaining:.0f}초), 갱신 필요")

            except redis.RedisError as e:
                logger.warning(f"⚠️  Redis 조회 실패, 토큰 재발급: {e}")

            # 토큰 갱신
            logger.info("🔑 Access Token 갱신 중...")
            await self._refresh_token()

            # Redis에서 다시 조회하여 반환
            access_token = self.redis_client.get(self.REDIS_KEY)
            return access_token

    async def _refresh_token(self):
        """Access Token 갱신 및 Redis 저장"""
        url = f"{self.base_url}/oauth2/tokenP"

        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

                if response.status_code != 200:
                    raise Exception(f"Token 발급 실패: {response.status_code}, {response.text}")

                data = response.json()

                access_token = data["access_token"]
                expires_in = int(data.get("expires_in", 86400))  # 기본 24시간
                token_expires_at = datetime.now() + timedelta(seconds=expires_in)

                # Redis에 저장
                try:
                    self.redis_client.set(self.REDIS_KEY, access_token)
                    self.redis_client.set(self.REDIS_EXPIRY_KEY, token_expires_at.isoformat())

                    # TTL 설정 (만료 시간 + 버퍼 10분)
                    ttl_seconds = expires_in + 600
                    self.redis_client.expire(self.REDIS_KEY, ttl_seconds)
                    self.redis_client.expire(self.REDIS_EXPIRY_KEY, ttl_seconds)

                    logger.info(
                        f"✅ Access Token 발급 및 Redis 저장 완료 "
                        f"(만료: {token_expires_at.strftime('%Y-%m-%d %H:%M:%S')})"
                    )

                except redis.RedisError as e:
                    logger.error(f"❌ Redis 저장 실패: {e}")
                    raise

        except Exception as e:
            logger.error(f"❌ Token 발급 실패: {e}")
            raise


class KISClient:
    """KIS API Client"""

    def __init__(self):
        """KIS API Client 초기화"""
        # 설정
        self.app_key = settings.KIS_APP_KEY
        self.app_secret = settings.KIS_APP_SECRET
        self.base_url = settings.KIS_BASE_URL
        self.mock_mode = settings.KIS_MOCK_MODE

        # Token Manager
        self.token_manager = TokenManager(
            app_key=self.app_key,
            app_secret=self.app_secret,
            base_url=self.base_url,
            mock_mode=self.mock_mode
        )

        # Rate Limiter
        if self.mock_mode:
            # 모의투자: 초당 5건
            self.rate_limiter = RateLimiter(max_requests=5, window_seconds=1.0)
        else:
            # 실전투자: 초당 20건
            self.rate_limiter = RateLimiter(max_requests=20, window_seconds=1.0)

        logger.info(
            f"KIS API Client 초기화 완료 "
            f"(모드: {'모의투자' if self.mock_mode else '실전투자'})"
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        tr_id: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        KIS API 요청 (Rate Limiting + 자동 재시도)

        Args:
            method: HTTP 메서드 (GET, POST)
            endpoint: API 엔드포인트 (예: /uapi/domestic-stock/v1/quotations/inquire-price)
            tr_id: 거래 ID (예: FHKST01010100)
            params: Query 파라미터
            data: Request Body
            max_retries: 최대 재시도 횟수

        Returns:
            API 응답 (JSON)
        """
        # Rate Limiting
        await self.rate_limiter.acquire()

        # Access Token 획득
        access_token = await self.token_manager.get_access_token()

        # Headers
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "authorization": f"Bearer {access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }

        # URL
        url = f"{self.base_url}{endpoint}"

        # 재시도 로직 (Exponential Backoff)
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    if method.upper() == "GET":
                        response = await client.get(
                            url,
                            headers=headers,
                            params=params,
                            timeout=30.0
                        )
                    elif method.upper() == "POST":
                        response = await client.post(
                            url,
                            headers=headers,
                            json=data,
                            timeout=30.0
                        )
                    else:
                        raise ValueError(f"지원하지 않는 HTTP 메서드: {method}")

                    # 응답 처리
                    if response.status_code == 200:
                        result = response.json()

                        # API 성공 여부 확인
                        rt_cd = result.get("rt_cd", "1")
                        if rt_cd == "0":
                            return result
                        else:
                            # API 에러
                            msg1 = result.get("msg1", "")
                            msg_cd = result.get("msg_cd", "")
                            raise Exception(
                                f"API 에러: rt_cd={rt_cd}, msg_cd={msg_cd}, msg1={msg1}, "
                                f"response={result}"
                            )

                    elif response.status_code == 429:
                        # Rate Limit 초과
                        wait_time = 2 ** attempt  # Exponential Backoff
                        logger.warning(f"Rate Limit 초과, {wait_time}초 대기 중...")
                        await asyncio.sleep(wait_time)
                        continue

                    else:
                        raise Exception(
                            f"HTTP 에러: {response.status_code}, {response.text}"
                        )

            except Exception as e:
                if attempt == max_retries - 1:
                    # 최종 실패
                    logger.error(f"❌ API 요청 실패 ({max_retries}회 재시도): {e}")
                    raise

                # 재시도
                wait_time = 2 ** attempt
                logger.warning(
                    f"⚠️  API 요청 실패 ({attempt + 1}/{max_retries}), "
                    f"{wait_time}초 후 재시도: {e}"
                )
                await asyncio.sleep(wait_time)

        raise Exception("API 요청 실패 (최대 재시도 횟수 초과)")

    async def get_daily_prices(
        self,
        stock_code: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        일봉 데이터 조회

        Args:
            stock_code: 종목 코드 (6자리)
            start_date: 시작 날짜
            end_date: 종료 날짜 (기본: 오늘)

        Returns:
            일봉 데이터 (JSON)
        """
        if end_date is None:
            end_date = datetime.now()

        # TR_ID 결정 (모의투자 vs 실전투자)
        tr_id = "FHKST03010100" if self.mock_mode else "FHKST03010100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date.strftime("%Y%m%d"),
            "FID_INPUT_DATE_2": end_date.strftime("%Y%m%d"),
            "FID_PERIOD_DIV_CODE": "D",  # 기간 구분 (D: 일봉)
            "FID_ORG_ADJ_PRC": "0"  # 수정주가 (0: 원주가, 1: 수정주가)
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            tr_id=tr_id,
            params=params
        )

    async def get_current_price(self, stock_code: str) -> Dict[str, Any]:
        """
        현재가 조회

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            현재가 데이터 (JSON)
        """
        tr_id = "FHKST01010100" if self.mock_mode else "FHKST01010100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id=tr_id,
            params=params
        )

    async def get_minute_prices(
        self,
        stock_code: str,
        start_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        1분봉 데이터 조회 (당일)

        Args:
            stock_code: 종목 코드 (6자리)
            start_time: 시작 시간 (HHMMSS, 기본: 090000)

        Returns:
            1분봉 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output1": {"prdt_type_cd": "300"},
                "output2": [
                    {
                        "stck_bsop_date": "20251109",
                        "stck_cntg_hour": "153000",
                        "stck_prpr": "59000",
                        "stck_oprc": "59100",
                        "stck_hgpr": "59200",
                        "stck_lwpr": "58900",
                        "cntg_vol": "123456"
                    }
                ]
            }
        """
        if start_time is None:
            start_time = "090000"  # 장 시작 시간

        # TR_ID 결정 (모의투자 vs 실전투자)
        tr_id = "FHKST03010200" if self.mock_mode else "FHKST03010200"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_HOUR_1": start_time,  # 시작 시간 (HHMMSS)
            "FID_ETC_CLS_CODE": "",  # 기타 구분 코드 (공백)
            "FID_PW_DATA_INCU_YN": "Y"  # 과거 데이터 포함 여부 (Y: 포함)
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            tr_id=tr_id,
            params=params
        )

    async def get_daily_minute_prices(
        self,
        stock_code: str,
        target_date: str,
        start_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        일별 1분봉 데이터 조회 (과거 일자 조회 가능)

        Args:
            stock_code: 종목 코드 (6자리)
            target_date: 조회 일자 (YYYYMMDD)
            start_time: 시작 시간 (HHMMSS, 기본: 090000)

        Returns:
            1분봉 데이터 (JSON)

        Note:
            - 실전투자 전용 API (모의투자 미지원)
            - 한 번에 최대 120건 조회 가능
            - 최대 1년치 과거 분봉 보관
            - TR_ID: FHKST03010230
            - Endpoint: /uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice

        Example Response:
            {
                "rt_cd": "0",
                "output1": {"prdt_type_cd": "300"},
                "output2": [
                    {
                        "stck_bsop_date": "20251107",
                        "stck_cntg_hour": "090100",
                        "stck_prpr": "59000",
                        "stck_oprc": "59100",
                        "stck_hgpr": "59200",
                        "stck_lwpr": "58900",
                        "cntg_vol": "123456"
                    }
                ]
            }
        """
        if self.mock_mode:
            raise ValueError("일별 1분봉 조회는 모의투자에서 지원하지 않습니다 (실전투자 전용)")

        if start_time is None:
            start_time = "090000"  # 장 시작 시간

        # TR_ID: FHKST03010230 (실전투자 전용)
        tr_id = "FHKST03010230"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": target_date,  # 조회 일자 (YYYYMMDD)
            "FID_INPUT_HOUR_1": start_time,  # 시작 시간 (HHMMSS)
            "FID_PW_DATA_INCU_YN": "Y"  # 과거 데이터 포함 여부 (Y: 포함)
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice",
            tr_id=tr_id,
            params=params
        )

    async def get_orderbook(self, stock_code: str) -> Dict[str, Any]:
        """
        호가 데이터 조회 (매수/매도 10호가)

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            호가 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output1": {
                    "askp1": "59100",  # 매도 1호가
                    "askp_rsqn1": "1234",  # 매도 1호가 잔량
                    "bidp1": "59000",  # 매수 1호가
                    "bidp_rsqn1": "5678",  # 매수 1호가 잔량
                    ... (10호가까지)
                    "total_askp_rsqn": "12345",  # 총 매도 잔량
                    "total_bidp_rsqn": "67890",  # 총 매수 잔량
                }
            }
        """
        # TR_ID: FHKST01010200 (모의/실전 공통)
        tr_id = "FHKST01010200"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
            tr_id=tr_id,
            params=params
        )

    async def get_current_price(self, stock_code: str) -> Dict[str, Any]:
        """
        현재가 시세 조회 (체결가, 체결량 포함)

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            현재가 시세 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output": {
                    "stck_prpr": "59000",  # 현재가
                    "prdy_vrss": "500",  # 전일 대비
                    "prdy_vrss_sign": "2",  # 전일 대비 부호 (1:상한, 2:상승, 3:보합, 4:하한, 5:하락)
                    "prdy_ctrt": "0.85",  # 전일 대비율
                    "acml_vol": "1234567",  # 누적 거래량
                    "acml_tr_pbmn": "73000000000",  # 누적 거래대금
                    "hts_kor_isnm": "삼성전자",  # 종목명
                    "stck_oprc": "58500",  # 시가
                    "stck_hgpr": "59500",  # 고가
                    "stck_lwpr": "58300",  # 저가
                    "stck_mxpr": "76700",  # 상한가
                    "stck_llam": "41300",  # 하한가
                    "per": "15.23",  # PER
                    "pbr": "1.45",  # PBR
                    "eps": "3876",  # EPS
                    "bps": "40678",  # BPS
                    "hts_avls": "353000000000000"  # 시가총액
                }
            }
        """
        # TR_ID: FHKST01010100 (모의/실전 공통)
        tr_id = "FHKST01010100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id=tr_id,
            params=params
        )

    async def get_investor_trading(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        투자자별 매매동향 조회 (기관, 외국인, 개인 등)

        Args:
            stock_code: 종목 코드 (6자리)
            start_date: 시작 날짜 (YYYYMMDD, 기본: 최근 30일 전)
            end_date: 종료 날짜 (YYYYMMDD, 기본: 오늘)

        Returns:
            투자자별 매매동향 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output": [
                    {
                        "stck_bsop_date": "20251109",  # 영업일자
                        "stck_clpr": "59000",  # 종가
                        "prsn_ntby_qty": "-12345",  # 개인 순매수 수량
                        "frgn_ntby_qty": "5678",  # 외국인 순매수 수량
                        "orgn_ntby_qty": "6667",  # 기관 순매수 수량
                        "prsn_ntby_tr_pbmn": "-728505000",  # 개인 순매수 거래대금
                        "frgn_ntby_tr_pbmn": "335002000",  # 외국인 순매수 거래대금
                        "orgn_ntby_tr_pbmn": "393353000"  # 기관 순매수 거래대금
                    }
                ]
            }
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        # TR_ID: FHKST01010900 (모의/실전 공통)
        tr_id = "FHKST01010900"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code,
            "FID_INPUT_DATE_1": start_date,
            "FID_INPUT_DATE_2": end_date,
            "FID_PERIOD_DIV_CODE": "D"  # 기간 구분 (D: 일별)
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-investor",
            tr_id=tr_id,
            params=params
        )

    async def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        종목 기본정보 조회 (업종, 상장주식수, 자본금 등)

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            종목 기본정보 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output": {
                    "std_idst_clsf_cd": "Q02",  # 표준산업분류코드
                    "std_idst_clsf_cd_name": "반도체",  # 업종명
                    "bstp_kor_isnm": "삼성전자",  # 종목명
                    "hts_avls": "353000000000000",  # 시가총액
                    "lstn_stcn": "5969782550",  # 상장주식수
                    "cpfn": "897514000000",  # 자본금
                    "issu_issu_ddpr": "19751029",  # 상장일
                    "ssts": "101"  # 결산월
                }
            }
        """
        # TR_ID: FHKST01010300 (모의/실전 공통)
        tr_id = "FHKST01010300"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/search-stock-info",
            tr_id=tr_id,
            params=params
        )

    async def get_sector_index(
        self,
        sector_code: str = "0001"  # 0001: KOSPI, 1001: KOSDAQ
    ) -> Dict[str, Any]:
        """
        업종 지수 조회

        Args:
            sector_code: 업종 코드
                - 0001: KOSPI
                - 1001: KOSDAQ
                - 0050: KOSPI IT
                - 0051: KOSPI 금융
                - 0052: KOSPI 산업재
                - 기타 업종 코드...

        Returns:
            업종 지수 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output": {
                    "bstp_nmix_prpr": "2485.71",  # 업종 현재지수
                    "bstp_nmix_prdy_vrss": "15.23",  # 전일 대비
                    "prdy_vrss_sign": "2",  # 전일 대비 부호
                    "bstp_nmix_prdy_ctrt": "0.62",  # 전일 대비율
                    "acml_vol": "12345678",  # 누적 거래량
                    "acml_tr_pbmn": "15000000000"  # 누적 거래대금
                }
            }
        """
        # TR_ID: FHKUP03500100 (모의/실전 공통)
        tr_id = "FHKUP03500100"

        params = {
            "FID_COND_MRKT_DIV_CODE": "U",  # 시장 구분 (U: 업종)
            "FID_INPUT_ISCD": sector_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-index-price",
            tr_id=tr_id,
            params=params
        )

    async def get_index_daily_price(
        self,
        index_code: str,
        start_date: Optional[str] = None,
        period_div_code: str = "D"
    ) -> Dict[str, Any]:
        """
        업종 일자별 지수 조회 (과거 데이터, 최대 100건)

        Args:
            index_code: 업종 코드
                - 0001: KOSPI
                - 1001: KOSDAQ
                - 2001: KOSPI200
                - 기타 업종 코드 (포탈 FAQ - 업종코드 참조)
            start_date: 조회 시작일 (YYYYMMDD, 기본: 오늘부터 역순 100일)
            period_div_code: 기간 구분 (D:일별, W:주별, M:월별)

        Returns:
            업종 일자별 지수 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output1": {
                    "bstp_nmix_prpr": "2485.71",  # 현재 업종지수
                    "bstp_nmix_prdy_vrss": "15.23",  # 전일대비
                    "prdy_vrss_sign": "2",  # 전일대비 부호
                    "bstp_nmix_prdy_ctrt": "0.62",  # 전일대비율
                    "acml_vol": "12345678",  # 누적 거래량
                    "bstp_nmix_oprc": "2470.48",  # 시가
                    "bstp_nmix_hgpr": "2490.12",  # 최고가
                    "bstp_nmix_lwpr": "2468.30"  # 최저가
                },
                "output2": [
                    {
                        "stck_bsop_date": "20251109",  # 영업일자
                        "bstp_nmix_prpr": "2485.71",  # 지수
                        "prdy_vrss_sign": "2",  # 부호
                        "bstp_nmix_prdy_vrss": "15.23",  # 전일대비
                        "bstp_nmix_prdy_ctrt": "0.62",  # 전일대비율
                        "bstp_nmix_oprc": "2470.48",  # 시가
                        "bstp_nmix_hgpr": "2490.12",  # 최고가
                        "bstp_nmix_lwpr": "2468.30",  # 최저가
                        "acml_vol": "12345678",  # 누적 거래량
                        "acml_tr_pbmn": "15000000000"  # 누적 거래대금
                    }
                ]
            }
        """
        if start_date is None:
            start_date = datetime.now().strftime("%Y%m%d")

        # TR_ID: FHPUP02120000 (실전만, 모의투자 미지원)
        tr_id = "FHPUP02120000"

        params = {
            "FID_PERIOD_DIV_CODE": period_div_code,  # D:일별, W:주별, M:월별
            "FID_COND_MRKT_DIV_CODE": "U",  # U: 업종
            "FID_INPUT_ISCD": index_code,
            "FID_INPUT_DATE_1": start_date
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-index-daily-price",
            tr_id=tr_id,
            params=params
        )

    async def get_overtime_price(self, stock_code: str) -> Dict[str, Any]:
        """
        시간외 현재가 조회 (실시간)

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            시간외 현재가 데이터 (JSON)

        Example Response:
            {
                "rt_cd": "0",
                "output": {
                    "ovtm_untp_prpr": "58000",  # 시간외 단일가 현재가
                    "ovtm_untp_prdy_vrss": "1000",  # 전일 대비
                    "prdy_vrss_sign": "2",  # 전일 대비 부호
                    "ovtm_untp_prdy_ctrt": "1.75",  # 전일 대비율
                    "acml_vol": "123456",  # 누적 거래량
                    "ovtm_untp_antc_cnpr": "58100",  # 예상 체결가
                }
            }
        """
        # TR_ID: FHPST02300000 (실전만, 모의투자 미지원)
        tr_id = "FHPST02300000"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-overtime-price",
            tr_id=tr_id,
            params=params
        )

    async def get_overtime_daily_prices(
        self,
        stock_code: str
    ) -> Dict[str, Any]:
        """
        시간외 일자별 주가 조회 (과거 데이터)

        Args:
            stock_code: 종목 코드 (6자리)

        Returns:
            시간외 일자별 주가 데이터 (JSON)

        Note:
            - 최근 30건만 조회 가능
            - output1: 기본정보 (현재 시간외 가격)
            - output2: 일자별 정보 (배열)

        Example Response:
            {
                "rt_cd": "0",
                "output1": {
                    "ovtm_untp_prpr": "58000",  # 현재 시간외 단일가
                    "ovtm_untp_prdy_vrss": "1000",  # 전일 대비
                },
                "output2": [
                    {
                        "stck_bsop_date": "20241109",  # 영업일자
                        "ovtm_untp_prpr": "57500",  # 시간외 단일가
                        "ovtm_untp_prdy_vrss": "500",  # 전일 대비
                        "ovtm_untp_prdy_ctrt": "0.88",  # 전일 대비율
                        "acml_vol": "98765",  # 누적 거래량
                        "acml_tr_pbmn": "5678901234",  # 누적 거래대금
                    }
                ]
            }
        """
        # TR_ID: FHPST02320000 (실전/모의 공통)
        tr_id = "FHPST02320000"

        params = {
            "FID_COND_MRKT_DIV_CODE": "J",  # 시장 구분 (J: 주식)
            "FID_INPUT_ISCD": stock_code
        }

        return await self.request(
            method="GET",
            endpoint="/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice",
            tr_id=tr_id,
            params=params
        )

    async def close(self):
        """리소스 정리"""
        logger.info("KIS API Client 종료")


# 싱글톤 인스턴스
_kis_client: Optional[KISClient] = None


async def get_kis_client() -> KISClient:
    """
    KIS Client 싱글톤 인스턴스 반환

    Returns:
        KISClient 인스턴스
    """
    global _kis_client
    if _kis_client is None:
        _kis_client = KISClient()
    return _kis_client
