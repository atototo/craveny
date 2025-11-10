"""
KIS API 일봉 데이터 수집기

매일 장 마감 후(15:40) 50개 종목의 일봉 데이터를 자동 수집
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from backend.crawlers.kis_client import get_kis_client
from backend.db.models.stock import Stock, StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class KISDailyCrawler:
    """KIS API 일봉 수집기"""

    def __init__(self):
        self.source = "kis"

    async def fetch_daily_prices(
        self,
        stock_code: str,
        start_date: datetime,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        KIS API로 일봉 데이터 조회

        Args:
            stock_code: 종목 코드 (6자리)
            start_date: 시작 날짜
            end_date: 종료 날짜 (기본: 오늘)

        Returns:
            DataFrame (columns: date, open, high, low, close, volume)
        """
        if end_date is None:
            end_date = datetime.now()

        try:
            client = await get_kis_client()

            # KIS API 호출
            response = await client.get_daily_prices(
                stock_code=stock_code,
                start_date=start_date,
                end_date=end_date
            )

            # 응답 파싱
            output = response.get("output2", [])

            if not output:
                logger.warning(f"데이터 없음: {stock_code}")
                return None

            # DataFrame 변환
            data = []
            for item in output:
                data.append({
                    "date": datetime.strptime(item["stck_bsop_date"], "%Y%m%d"),
                    "open": float(item["stck_oprc"]),
                    "high": float(item["stck_hgpr"]),
                    "low": float(item["stck_lwpr"]),
                    "close": float(item["stck_clpr"]),
                    "volume": int(item["acml_vol"])
                })

            df = pd.DataFrame(data)
            df = df.sort_values("date").reset_index(drop=True)

            logger.info(f"✅ {stock_code} 일봉 데이터 조회 성공: {len(df)}건")
            return df

        except Exception as e:
            logger.error(f"❌ {stock_code} 일봉 데이터 조회 실패: {e}")
            return None

    def save_to_db(
        self,
        stock_code: str,
        df: pd.DataFrame,
        db: Session
    ) -> int:
        """
        일봉 데이터를 DB에 저장

        Args:
            stock_code: 종목 코드
            df: 일봉 DataFrame
            db: 데이터베이스 세션

        Returns:
            저장된 레코드 수
        """
        saved_count = 0

        try:
            for _, row in df.iterrows():
                # 중복 체크
                existing = db.query(StockPrice).filter(
                    StockPrice.stock_code == stock_code,
                    StockPrice.date == row["date"],
                    StockPrice.source == self.source
                ).first()

                if existing:
                    # 기존 데이터 업데이트
                    existing.open = row["open"]
                    existing.high = row["high"]
                    existing.low = row["low"]
                    existing.close = row["close"]
                    existing.volume = row["volume"]
                    logger.debug(f"업데이트: {stock_code} {row['date'].date()}")
                else:
                    # 새 데이터 삽입
                    price = StockPrice(
                        stock_code=stock_code,
                        date=row["date"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                        source=self.source
                    )
                    db.add(price)
                    logger.debug(f"삽입: {stock_code} {row['date'].date()}")

                saved_count += 1

            db.commit()
            logger.info(f"✅ {stock_code} DB 저장 완료: {saved_count}건")

        except Exception as e:
            db.rollback()
            logger.error(f"❌ {stock_code} DB 저장 실패: {e}")
            return 0

        return saved_count

    async def collect_stock(
        self,
        stock_code: str,
        days: int = 30,
        db: Optional[Session] = None
    ) -> Dict:
        """
        단일 종목 일봉 수집

        Args:
            stock_code: 종목 코드
            days: 수집 기간 (일)
            db: 데이터베이스 세션

        Returns:
            수집 결과 딕셔너리
        """
        start_date = datetime.now() - timedelta(days=days)

        # 데이터 조회
        df = await self.fetch_daily_prices(stock_code, start_date)

        if df is None or df.empty:
            return {
                "stock_code": stock_code,
                "status": "failed",
                "count": 0,
                "error": "No data"
            }

        # DB 저장
        db_session = db or SessionLocal()
        should_close = db is None

        try:
            saved_count = self.save_to_db(stock_code, df, db_session)

            return {
                "stock_code": stock_code,
                "status": "success",
                "count": saved_count
            }

        finally:
            if should_close:
                db_session.close()

    async def collect_all_stocks(
        self,
        days: int = 30,
        batch_size: int = 10
    ) -> Dict:
        """
        전체 활성 종목 일봉 수집

        Args:
            days: 수집 기간 (일)
            batch_size: 배치 크기 (동시 처리 종목 수)

        Returns:
            수집 결과 요약
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"KIS API 일봉 데이터 수집 시작 (과거 {days}일)")
        logger.info(f"{'='*80}\n")

        db = SessionLocal()

        try:
            # 활성 종목 조회
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            stock_codes = [stock.code for stock in stocks]

            logger.info(f"수집 대상: {len(stock_codes)}개 종목")

            results = []
            success_count = 0
            total_saved = 0

            # 배치 처리
            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]

                logger.info(f"\n📦 배치 {i//batch_size + 1} 시작: {len(batch)}개 종목")

                # 배치 내 종목 병렬 수집
                tasks = [
                    self.collect_stock(code, days=days, db=db)
                    for code in batch
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"예외 발생: {result}")
                        continue

                    results.append(result)

                    if result["status"] == "success":
                        success_count += 1
                        total_saved += result["count"]

                # Rate limiting 고려 (배치 간 잠시 대기)
                if i + batch_size < len(stock_codes):
                    await asyncio.sleep(0.5)

            # 결과 요약
            success_rate = (success_count / len(stock_codes)) * 100 if stock_codes else 0

            summary = {
                "total_stocks": len(stock_codes),
                "success_count": success_count,
                "failed_count": len(stock_codes) - success_count,
                "success_rate": success_rate,
                "total_saved": total_saved,
                "results": results
            }

            logger.info(f"\n{'='*80}")
            logger.info(f"수집 완료!")
            logger.info(f"  - 전체: {len(stock_codes)}개")
            logger.info(f"  - 성공: {success_count}개 ({success_rate:.1f}%)")
            logger.info(f"  - 실패: {len(stock_codes) - success_count}개")
            logger.info(f"  - 저장: {total_saved}건")
            logger.info(f"{'='*80}\n")

            return summary

        finally:
            db.close()

    async def backfill_historical_data(self, days: int = 90) -> Dict:
        """
        과거 데이터 백필

        Args:
            days: 백필 기간 (일)

        Returns:
            백필 결과
        """
        logger.info(f"🔙 과거 {days}일 데이터 백필 시작...")

        return await self.collect_all_stocks(days=days, batch_size=10)


# 싱글톤 인스턴스
_crawler: Optional[KISDailyCrawler] = None


def get_kis_daily_crawler() -> KISDailyCrawler:
    """KIS 일봉 수집기 싱글톤 반환"""
    global _crawler
    if _crawler is None:
        _crawler = KISDailyCrawler()
    return _crawler
