"""
시장 지수 수집 크롤러

KOSPI, KOSDAQ 지수 데이터를 수집하여 DB에 저장합니다.
FinanceDataReader를 사용하여 일봉 데이터를 수집합니다.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import FinanceDataReader as fdr
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


class MarketIndexCrawler:
    """시장 지수 크롤러"""

    def __init__(self):
        self.indices = {
            "KOSPI": "KS11",  # FinanceDataReader 심볼
            "KOSDAQ": "KQ11",
        }
        self.retry_delay = 2  # 재시도 간격 (초)
        self.max_retries = 3  # 최대 재시도 횟수

    def collect_index_data(
        self, index_name: str, symbol: str, days: int = 30, db: Optional[Session] = None
    ) -> int:
        """
        지수 데이터 수집

        Args:
            index_name: 지수 이름 (KOSPI, KOSDAQ)
            symbol: FinanceDataReader 심볼 (KS11, KQ11)
            days: 수집할 일수 (기본 30일)
            db: DB 세션 (optional)

        Returns:
            저장된 레코드 수
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            # 수집 기간 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            logger.info(
                f"{index_name} 지수 수집 시작: {start_date.date()} ~ {end_date.date()}"
            )

            # FinanceDataReader로 데이터 수집 (재시도 로직 포함)
            df = None
            for attempt in range(self.max_retries):
                try:
                    df = fdr.DataReader(symbol, start_date.strftime("%Y-%m-%d"))
                    if df is not None and not df.empty:
                        break
                    logger.warning(f"{index_name} 데이터 없음 (시도 {attempt + 1}/{self.max_retries})")
                except Exception as e:
                    logger.warning(
                        f"{index_name} 수집 실패 (시도 {attempt + 1}/{self.max_retries}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))  # 점진적 지연

            if df is None or df.empty:
                logger.error(f"{index_name} 데이터 수집 최종 실패")
                return 0

            # 중복 방지: 이미 저장된 날짜 확인
            existing_dates_result = db.execute(
                text(
                    """
                    SELECT DISTINCT DATE(date) as date
                    FROM market_indices
                    WHERE index_name = :index_name
                    AND date >= :start_date
                """
                ),
                {"index_name": index_name, "start_date": start_date},
            )
            existing_dates = {row[0] for row in existing_dates_result}

            # 데이터 저장
            saved_count = 0
            for date, row in df.iterrows():
                # 날짜 변환 (pandas Timestamp → datetime)
                date_obj = date.to_pydatetime() if hasattr(date, "to_pydatetime") else date

                # 중복 체크
                if date_obj.date() in existing_dates:
                    continue

                # 변동률 계산
                change_pct = None
                if "Change" in row:
                    change_pct = float(row["Change"])
                elif "Close" in row and len(df) > 0:
                    # 전일 종가 대비 변동률 계산
                    prev_close = df.iloc[max(0, df.index.get_loc(date) - 1)]["Close"]
                    if prev_close > 0:
                        change_pct = ((row["Close"] - prev_close) / prev_close) * 100

                # DB에 저장
                db.execute(
                    text(
                        """
                        INSERT INTO market_indices
                        (index_name, date, open, high, low, close, volume, change_pct)
                        VALUES
                        (:index_name, :date, :open, :high, :low, :close, :volume, :change_pct)
                    """
                    ),
                    {
                        "index_name": index_name,
                        "date": date_obj,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]) if "Volume" in row else None,
                        "change_pct": change_pct,
                    },
                )
                saved_count += 1

            db.commit()
            logger.info(f"✅ {index_name} 지수 {saved_count}건 저장 완료")
            return saved_count

        except Exception as e:
            logger.error(f"❌ {index_name} 지수 수집 실패: {e}")
            db.rollback()
            raise
        finally:
            if close_db:
                db.close()

    def collect_all_indices(self, days: int = 30) -> Dict[str, int]:
        """
        모든 지수 데이터 수집

        Args:
            days: 수집할 일수 (기본 30일)

        Returns:
            {지수명: 저장된 레코드 수}
        """
        results = {}
        db = SessionLocal()

        try:
            for i, (index_name, symbol) in enumerate(self.indices.items()):
                # 지수 간 수집 지연 (rate limit 방지)
                if i > 0:
                    time.sleep(self.retry_delay)

                try:
                    count = self.collect_index_data(index_name, symbol, days, db)
                    results[index_name] = count
                except Exception as e:
                    logger.error(f"{index_name} 수집 중 오류: {e}")
                    results[index_name] = 0

            return results
        finally:
            db.close()

    def get_latest_index(self, index_name: str) -> Optional[Dict]:
        """
        최신 지수 데이터 조회

        Args:
            index_name: 지수 이름 (KOSPI, KOSDAQ)

        Returns:
            최신 지수 데이터 (dict) 또는 None
        """
        db = SessionLocal()
        try:
            result = db.execute(
                text(
                    """
                    SELECT index_name, date, close, change_pct
                    FROM market_indices
                    WHERE index_name = :index_name
                    ORDER BY date DESC
                    LIMIT 1
                """
                ),
                {"index_name": index_name},
            )
            row = result.fetchone()

            if row:
                return {
                    "index_name": row[0],
                    "date": row[1],
                    "close": row[2],
                    "change_pct": row[3],
                }
            return None
        finally:
            db.close()


def main():
    """테스트용 메인 함수"""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    crawler = MarketIndexCrawler()

    print("🚀 시장 지수 수집 시작...\n")

    # 최근 30일 데이터 수집
    results = crawler.collect_all_indices(days=30)

    print("\n📊 수집 결과:")
    for index_name, count in results.items():
        print(f"  {index_name}: {count}건 저장")

    # 최신 데이터 확인
    print("\n📈 최신 지수:")
    for index_name in ["KOSPI", "KOSDAQ"]:
        latest = crawler.get_latest_index(index_name)
        if latest:
            print(
                f"  {latest['index_name']}: {latest['close']:.2f} "
                f"({latest['change_pct']:+.2f}%) - {latest['date']}"
            )

    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
