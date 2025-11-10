"""
가격 조회 서비스

시간대에 따라 적절한 가격을 반환합니다:
- 장중 (09:00~15:30): KIS API 실시간 조회 (시가/고가/저가 포함)
- 장전 시간외 (08:30~09:00): 시간외 가격 (StockOvertimePrice)
- 장후 시간외 (15:30~18:00): 시간외 가격 (StockOvertimePrice)
- 기타 시간: 전일 종가 (StockPrice)
"""
import logging
import asyncio
from datetime import datetime, time, date
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.db.models.stock import StockPrice
from backend.db.models.market_data import StockCurrentPrice, StockOvertimePrice
from backend.crawlers.kis_client import KISClient
from backend.config import settings


logger = logging.getLogger(__name__)


# KIS Client 싱글톤
_kis_client = None

def get_kis_client() -> KISClient:
    """KIS Client 싱글톤 인스턴스 반환"""
    global _kis_client
    if _kis_client is None:
        _kis_client = KISClient()
    return _kis_client


class PriceService:
    """시간대별 가격 조회 서비스"""

    # 시장 시간 정의
    MARKET_OPEN = time(9, 0)  # 09:00
    MARKET_CLOSE = time(15, 30)  # 15:30

    PRE_MARKET_START = time(8, 30)  # 08:30
    PRE_MARKET_END = time(9, 0)  # 09:00

    POST_MARKET_START = time(15, 30)  # 15:30
    POST_MARKET_END = time(18, 0)  # 18:00

    @classmethod
    def get_market_status(cls, now: Optional[datetime] = None) -> str:
        """
        현재 시장 상태 반환

        Returns:
            'market': 장중
            'pre_market': 장전 시간외
            'post_market': 장후 시간외
            'closed': 장마감
        """
        if now is None:
            now = datetime.now()

        current_time = now.time()

        # 장중
        if cls.MARKET_OPEN <= current_time < cls.MARKET_CLOSE:
            return 'market'

        # 장전 시간외
        if cls.PRE_MARKET_START <= current_time < cls.PRE_MARKET_END:
            return 'pre_market'

        # 장후 시간외
        if cls.POST_MARKET_START <= current_time < cls.POST_MARKET_END:
            return 'post_market'

        # 장마감
        return 'closed'

    @classmethod
    async def get_current_price(
        cls,
        stock_code: str,
        db: Session,
        now: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        시간대에 맞는 현재가 조회

        Args:
            stock_code: 종목 코드
            db: DB 세션
            now: 현재 시간 (테스트용)

        Returns:
            가격 정보 딕셔너리 또는 None
        """
        if now is None:
            now = datetime.now()

        market_status = cls.get_market_status(now)
        today = now.date()

        try:
            # 1. 장중: 실시간 현재가
            if market_status == 'market':
                return await cls._get_realtime_price_async(stock_code, db, today)

            # 2. 시간외 (장전/장후): 시간외 가격
            if market_status in ['pre_market', 'post_market']:
                overtime_price = cls._get_overtime_price(stock_code, db, today)
                if overtime_price:
                    return overtime_price
                # 시간외 가격 없으면 전일 종가로 fallback

            # 3. 장마감 또는 시간외 가격 없을 때: 전일 종가
            return cls._get_latest_close_price(stock_code, db)

        except Exception as e:
            logger.error(f"가격 조회 실패 ({stock_code}): {e}", exc_info=True)
            return None

    @classmethod
    async def _get_realtime_price_async(
        cls,
        stock_code: str,
        db: Session,
        today: date
    ) -> Optional[Dict[str, Any]]:
        """실시간 현재가 조회 (KIS API 직접 호출)"""
        try:
            # KIS API 호출 (async)
            kis_client = get_kis_client()
            response = await kis_client.get_current_price(stock_code)

            # 응답 파싱
            if response and response.get("rt_cd") == "0":
                output = response.get("output", {})

                # 가격 데이터 파싱
                stck_prpr = float(output.get("stck_prpr", 0))  # 현재가
                stck_oprc = float(output.get("stck_oprc", 0))  # 시가
                stck_hgpr = float(output.get("stck_hgpr", 0))  # 고가
                stck_lwpr = float(output.get("stck_lwpr", 0))  # 저가

                prdy_vrss = float(output.get("prdy_vrss", 0))  # 전일 대비
                prdy_ctrt = float(output.get("prdy_ctrt", 0))  # 전일 대비율
                prdy_vrss_sign = output.get("prdy_vrss_sign", "3")  # 전일 대비 부호

                acml_vol = int(output.get("acml_vol", 0))  # 누적 거래량
                acml_tr_pbmn = int(output.get("acml_tr_pbmn", 0))  # 누적 거래대금

                return {
                    "close": stck_prpr,
                    "price": stck_prpr,  # backward compatibility
                    "open": stck_oprc if stck_oprc > 0 else None,
                    "high": stck_hgpr if stck_hgpr > 0 else None,
                    "low": stck_lwpr if stck_lwpr > 0 else None,
                    "change": prdy_vrss,
                    "change_rate": prdy_ctrt,
                    "change_sign": prdy_vrss_sign,
                    "volume": acml_vol,
                    "trading_value": acml_tr_pbmn,
                    "datetime": datetime.now().isoformat(),
                    "source": "kis_api",
                    "market_status": "market",
                }
            else:
                logger.warning(f"KIS API 응답 실패: {response}")

        except Exception as e:
            logger.error(f"KIS API 호출 실패 ({stock_code}): {e}", exc_info=True)

        # API 실패 시 DB에서 조회 (fallback)
        current_price = db.query(StockCurrentPrice).filter(
            StockCurrentPrice.stock_code == stock_code,
            StockCurrentPrice.datetime >= datetime.combine(today, time.min),
            StockCurrentPrice.datetime < datetime.combine(today, time.max)
        ).order_by(StockCurrentPrice.datetime.desc()).first()

        if current_price:
            logger.info(f"KIS API 실패, DB 데이터 사용: {stock_code}")
            return {
                "close": current_price.stck_prpr,
                "price": current_price.stck_prpr,
                "open": None,
                "high": None,
                "low": None,
                "change": current_price.prdy_vrss,
                "change_rate": current_price.prdy_ctrt,
                "change_sign": current_price.prdy_vrss_sign,
                "volume": current_price.acml_vol,
                "trading_value": current_price.acml_tr_pbmn,
                "datetime": current_price.datetime.isoformat() if current_price.datetime else None,
                "source": "db_fallback",
                "market_status": "market",
            }

        # DB에도 없으면 전일 종가
        return cls._get_latest_close_price(stock_code, db)

    @classmethod
    def _get_overtime_price(
        cls,
        stock_code: str,
        db: Session,
        today: date
    ) -> Optional[Dict[str, Any]]:
        """시간외 가격 조회 (StockOvertimePrice)"""
        overtime_price = db.query(StockOvertimePrice).filter(
            StockOvertimePrice.stock_code == stock_code,
            StockOvertimePrice.date == today
        ).first()

        if overtime_price and overtime_price.ovtm_untp_prpr:
            market_status = cls.get_market_status()

            return {
                "close": overtime_price.ovtm_untp_prpr,
                "price": overtime_price.ovtm_untp_prpr,  # backward compatibility
                "open": None,  # 시간외 데이터에는 시가 정보 없음
                "high": None,
                "low": None,
                "change": overtime_price.ovtm_untp_prdy_vrss,
                "change_rate": overtime_price.ovtm_untp_prdy_ctrt,
                "change_sign": overtime_price.prdy_vrss_sign,
                "volume": overtime_price.acml_vol,
                "trading_value": overtime_price.acml_tr_pbmn,
                "datetime": datetime.combine(overtime_price.date, time(18, 0)).isoformat(),
                "source": "overtime",
                "market_status": market_status,
            }

        return None

    @classmethod
    def _get_latest_close_price(
        cls,
        stock_code: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """최신 종가 조회 (StockPrice - 일봉)"""
        latest_price = db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code
        ).order_by(StockPrice.date.desc()).first()

        if latest_price:
            # 전일 대비 계산
            previous_price = db.query(StockPrice).filter(
                StockPrice.stock_code == stock_code,
                StockPrice.date < latest_price.date
            ).order_by(StockPrice.date.desc()).first()

            change = 0.0
            change_rate = 0.0
            if previous_price and previous_price.close > 0:
                change = latest_price.close - previous_price.close
                change_rate = (change / previous_price.close) * 100

            return {
                "close": latest_price.close,
                "price": latest_price.close,  # backward compatibility
                "open": latest_price.open,
                "high": latest_price.high,
                "low": latest_price.low,
                "change": change,
                "change_rate": round(change_rate, 2),
                "change_sign": "2" if change > 0 else "5" if change < 0 else "3",
                "volume": latest_price.volume,
                "datetime": latest_price.date.isoformat() if latest_price.date else None,
                "source": "daily_close",
                "market_status": "closed",
            }

        return None


async def get_current_price(
    stock_code: str,
    db: Session,
    now: Optional[datetime] = None
) -> Optional[Dict[str, Any]]:
    """
    시간대에 맞는 현재가 조회 (헬퍼 함수)

    Args:
        stock_code: 종목 코드
        db: DB 세션
        now: 현재 시간 (테스트용)

    Returns:
        가격 정보 딕셔너리 또는 None
    """
    return await PriceService.get_current_price(stock_code, db, now)


def get_market_status(now: Optional[datetime] = None) -> str:
    """
    현재 시장 상태 반환 (헬퍼 함수)

    Returns:
        'market', 'pre_market', 'post_market', 'closed'
    """
    return PriceService.get_market_status(now)
