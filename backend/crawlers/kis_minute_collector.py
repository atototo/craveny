"""
KIS API 1분봉 데이터 수집기

장중 실시간으로 1분봉 OHLCV 데이터를 수집하여 DB에 저장합니다.
"""
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock, StockPriceMinute
from backend.crawlers.kis_client import get_kis_client


logger = logging.getLogger(__name__)


class MinutePriceCollector:
    """1분봉 데이터 수집기"""

    def __init__(self, batch_size: int = 10):
        """
        Args:
            batch_size: 배치 크기 (동시 수집 종목 수)
        """
        self.batch_size = batch_size
        self.collected_count = 0
        self.failed_count = 0
        self.skipped_count = 0

    async def collect_minute_data(self, stock_code: str) -> Dict[str, Any]:
        """
        단일 종목의 1분봉 데이터 수집

        Args:
            stock_code: 종목 코드

        Returns:
            수집 결과 딕셔너리
        """
        try:
            # KIS Client
            client = await get_kis_client()

            # 1분봉 조회
            result = await client.get_minute_prices(stock_code=stock_code)

            # output2 확인
            output2 = result.get("output2", [])

            if not output2:
                logger.warning(f"⚠️  {stock_code}: 1분봉 데이터 없음")
                self.skipped_count += 1
                return {
                    "stock_code": stock_code,
                    "status": "skipped",
                    "saved": 0,
                    "error": "No data"
                }

            # DB 저장
            saved_count = await self._save_to_db(stock_code, output2)

            self.collected_count += saved_count
            logger.info(f"✅ {stock_code}: {saved_count}건 저장")

            return {
                "stock_code": stock_code,
                "status": "success",
                "saved": saved_count
            }

        except Exception as e:
            self.failed_count += 1
            logger.error(f"❌ {stock_code}: 수집 실패 - {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "saved": 0,
                "error": str(e)
            }

    async def _save_to_db(self, stock_code: str, data: List[Dict[str, Any]]) -> int:
        """
        1분봉 데이터를 DB에 저장

        Args:
            stock_code: 종목 코드
            data: 1분봉 데이터 리스트

        Returns:
            저장된 레코드 수
        """
        db = SessionLocal()
        saved_count = 0

        try:
            for bar in data:
                # datetime 파싱
                date_str = bar.get("stck_bsop_date")  # YYYYMMDD
                time_str = bar.get("stck_cntg_hour")  # HHMMSS

                if not date_str or not time_str or len(time_str) < 6:
                    continue

                dt = datetime.strptime(
                    f"{date_str}{time_str}",
                    "%Y%m%d%H%M%S"
                )

                # OHLCV 파싱
                open_price = float(bar.get("stck_oprc", 0))
                high_price = float(bar.get("stck_hgpr", 0))
                low_price = float(bar.get("stck_lwpr", 0))
                close_price = float(bar.get("stck_prpr", 0))
                volume = int(bar.get("cntg_vol", 0))

                # 중복 체크
                existing = db.query(StockPriceMinute).filter(
                    StockPriceMinute.stock_code == stock_code,
                    StockPriceMinute.datetime == dt
                ).first()

                if existing:
                    # 이미 존재하면 스킵
                    continue

                # 새 레코드 생성
                minute_price = StockPriceMinute(
                    stock_code=stock_code,
                    datetime=dt,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    source="kis"
                )

                db.add(minute_price)
                saved_count += 1

            # 커밋
            db.commit()
            return saved_count

        except IntegrityError as e:
            db.rollback()
            logger.warning(f"⚠️  {stock_code}: 중복 데이터 스킵 - {e}")
            return 0

        except Exception as e:
            db.rollback()
            logger.error(f"❌ {stock_code}: DB 저장 실패 - {e}")
            raise

        finally:
            db.close()

    async def collect_all_stocks(self, stock_codes: List[str]) -> Dict[str, Any]:
        """
        모든 종목의 1분봉 데이터 수집 (배치 처리)

        Args:
            stock_codes: 종목 코드 리스트

        Returns:
            수집 결과 요약
        """
        logger.info("=" * 80)
        logger.info(f"🚀 1분봉 데이터 수집 시작 ({len(stock_codes)}개 종목)")
        logger.info("=" * 80)

        results = []

        # 배치 처리
        for i in range(0, len(stock_codes), self.batch_size):
            batch = stock_codes[i:i + self.batch_size]

            logger.info(f"\n📦 배치 {i // self.batch_size + 1}: {len(batch)}개 종목 수집 중...")

            # 병렬 수집
            tasks = [self.collect_minute_data(code) for code in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            results.extend(batch_results)

            # Rate limiting (배치 간 대기)
            if i + self.batch_size < len(stock_codes):
                await asyncio.sleep(0.5)

        # 결과 요약
        logger.info("\n" + "=" * 80)
        logger.info("📊 수집 결과 요약")
        logger.info("=" * 80)
        logger.info(f"총 종목 수: {len(stock_codes)}개")
        logger.info(f"저장 건수: {self.collected_count}건")
        logger.info(f"실패: {self.failed_count}개")
        logger.info(f"스킵: {self.skipped_count}개")

        return {
            "total_stocks": len(stock_codes),
            "total_saved": self.collected_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "results": results
        }


async def run_minute_collector():
    """1분봉 수집기 실행 (스케줄러용)"""
    logger.info("⏰ 1분봉 수집기 시작")

    db = SessionLocal()

    try:
        # 활성 종목 조회 (priority 순)
        stocks = db.query(Stock).filter(
            Stock.is_active == True
        ).order_by(Stock.priority).all()

        stock_codes = [stock.code for stock in stocks]

        if not stock_codes:
            logger.warning("⚠️  활성 종목 없음")
            return

        # 수집기 실행
        collector = MinutePriceCollector(batch_size=10)
        result = await collector.collect_all_stocks(stock_codes)

        logger.info(f"✅ 1분봉 수집 완료: {result['total_saved']}건")

    except Exception as e:
        logger.error(f"❌ 1분봉 수집 실패: {e}", exc_info=True)

    finally:
        db.close()


# 싱글톤 인스턴스
_collector: MinutePriceCollector = None


def get_minute_collector() -> MinutePriceCollector:
    """
    MinutePriceCollector 싱글톤 인스턴스 반환

    Returns:
        MinutePriceCollector 인스턴스
    """
    global _collector
    if _collector is None:
        _collector = MinutePriceCollector(batch_size=10)
    return _collector
