"""
통합 지수 크롤러 (시장 지수 + 섹터 지수)

pykrx를 사용하여 KOSPI, KOSDAQ, 섹터별 지수를 수집합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pykrx import stock
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


class IndexCrawler:
    """통합 지수 크롤러 (시장 + 섹터)"""

    def __init__(self):
        # 시장 지수
        self.market_indices = {
            "KOSPI": "1001",  # KOSPI 지수 코드
            "KOSDAQ": "2001",  # KOSDAQ 지수 코드
        }

        # 섹터 지수 (KOSPI 업종 지수)
        self.sector_indices = {
            "에너지": "1010",
            "화학": "1011",
            "비금속": "1012",
            "철강": "1013",
            "기계": "1014",
            "전기전자": "1015",
            "의료정밀": "1016",
            "운수장비": "1017",
            "유통": "1018",
            "건설": "1019",
            "운수창고": "1020",
            "통신업": "1021",
            "금융": "1022",
            "증권": "1023",
            "보험": "1024",
            "서비스": "1025",
            "제조": "1026",
        }

    def collect_market_indices(self, days: int = 30) -> Dict[str, int]:
        """
        시장 지수 수집 (KOSPI, KOSDAQ)

        Args:
            days: 수집할 일수 (기본 30일)

        Returns:
            {지수명: 저장된 레코드 수}
        """
        db = SessionLocal()
        results = {}

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            for index_name, index_code in self.market_indices.items():
                try:
                    logger.info(f"{index_name} 지수 수집: {start_date.date()} ~ {end_date.date()}")

                    # pykrx로 데이터 수집
                    df = stock.get_index_ohlcv_by_date(start_str, end_str, index_code)

                    if df is None or df.empty:
                        logger.warning(f"{index_name} 데이터 없음")
                        results[index_name] = 0
                        continue

                    # 기존 날짜 조회
                    existing_dates_result = db.execute(
                        text("""
                            SELECT DISTINCT DATE(date) as date
                            FROM market_indices
                            WHERE index_name = :index_name
                            AND date >= :start_date
                        """),
                        {"index_name": index_name, "start_date": start_date}
                    )
                    existing_dates = {row[0] for row in existing_dates_result}

                    # 데이터 저장
                    saved_count = 0
                    for date_idx, row in df.iterrows():
                        date_obj = date_idx.to_pydatetime()

                        if date_obj.date() in existing_dates:
                            continue

                        # 변동률 계산
                        change_pct = None
                        if len(df) > 1:
                            idx = df.index.get_loc(date_idx)
                            if idx > 0:
                                prev_close = df.iloc[idx - 1]['종가']
                                if prev_close > 0:
                                    change_pct = ((row['종가'] - prev_close) / prev_close) * 100

                        db.execute(
                            text("""
                                INSERT INTO market_indices
                                (index_name, date, open, high, low, close, volume, change_pct)
                                VALUES
                                (:index_name, :date, :open, :high, :low, :close, :volume, :change_pct)
                            """),
                            {
                                "index_name": index_name,
                                "date": date_obj,
                                "open": float(row['시가']),
                                "high": float(row['고가']),
                                "low": float(row['저가']),
                                "close": float(row['종가']),
                                "volume": int(row['거래량']) if '거래량' in row else None,
                                "change_pct": change_pct,
                            }
                        )
                        saved_count += 1

                    db.commit()
                    logger.info(f"✅ {index_name} 지수 {saved_count}건 저장")
                    results[index_name] = saved_count

                except Exception as e:
                    logger.error(f"❌ {index_name} 수집 실패: {e}")
                    db.rollback()
                    results[index_name] = 0

            return results

        finally:
            db.close()

    def collect_sector_indices(self, days: int = 30) -> Dict[str, int]:
        """
        섹터 지수 수집

        Args:
            days: 수집할 일수 (기본 30일)

        Returns:
            {섹터명: 저장된 레코드 수}
        """
        db = SessionLocal()
        results = {}

        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            for sector_name, sector_code in self.sector_indices.items():
                try:
                    logger.info(f"{sector_name} 섹터 지수 수집: {start_date.date()} ~ {end_date.date()}")

                    # pykrx로 데이터 수집
                    df = stock.get_index_ohlcv_by_date(start_str, end_str, sector_code)

                    if df is None or df.empty:
                        logger.warning(f"{sector_name} 데이터 없음")
                        results[sector_name] = 0
                        continue

                    # 기존 날짜 조회
                    existing_dates_result = db.execute(
                        text("""
                            SELECT DISTINCT DATE(date) as date
                            FROM sector_indices
                            WHERE sector_name = :sector_name
                            AND date >= :start_date
                        """),
                        {"sector_name": sector_name, "start_date": start_date}
                    )
                    existing_dates = {row[0] for row in existing_dates_result}

                    # 데이터 저장
                    saved_count = 0
                    for date_idx, row in df.iterrows():
                        date_obj = date_idx.to_pydatetime()

                        if date_obj.date() in existing_dates:
                            continue

                        # 변동률 계산
                        change_pct = None
                        if len(df) > 1:
                            idx = df.index.get_loc(date_idx)
                            if idx > 0:
                                prev_close = df.iloc[idx - 1]['종가']
                                if prev_close > 0:
                                    change_pct = ((row['종가'] - prev_close) / prev_close) * 100

                        db.execute(
                            text("""
                                INSERT INTO sector_indices
                                (sector_name, date, open, high, low, close, volume, change_pct)
                                VALUES
                                (:sector_name, :date, :open, :high, :low, :close, :volume, :change_pct)
                            """),
                            {
                                "sector_name": sector_name,
                                "date": date_obj,
                                "open": float(row['시가']),
                                "high": float(row['고가']),
                                "low": float(row['저가']),
                                "close": float(row['종가']),
                                "volume": int(row['거래량']) if '거래량' in row else None,
                                "change_pct": change_pct,
                            }
                        )
                        saved_count += 1

                    db.commit()
                    logger.info(f"✅ {sector_name} 섹터 {saved_count}건 저장")
                    results[sector_name] = saved_count

                except Exception as e:
                    logger.error(f"❌ {sector_name} 수집 실패: {e}")
                    db.rollback()
                    results[sector_name] = 0

            return results

        finally:
            db.close()

    def collect_all_indices(self, days: int = 30) -> Dict[str, Dict[str, int]]:
        """
        모든 지수 데이터 수집 (시장 + 섹터)

        Args:
            days: 수집할 일수

        Returns:
            {"market": {...}, "sector": {...}}
        """
        logger.info(f"📊 지수 데이터 수집 시작 (최근 {days}일)")

        market_results = self.collect_market_indices(days)
        sector_results = self.collect_sector_indices(days)

        return {
            "market": market_results,
            "sector": sector_results
        }


def main():
    """테스트용 메인 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    crawler = IndexCrawler()

    print("🚀 통합 지수 크롤러 시작\n")
    print("="*80)

    # 최근 30일 데이터 수집
    results = crawler.collect_all_indices(days=30)

    print("\n" + "="*80)
    print("\n📊 수집 결과:")

    print("\n1️⃣  시장 지수:")
    for index_name, count in results["market"].items():
        print(f"  {index_name}: {count}건")

    print("\n2️⃣  섹터 지수:")
    for sector_name, count in results["sector"].items():
        print(f"  {sector_name}: {count}건")

    total_market = sum(results["market"].values())
    total_sector = sum(results["sector"].values())

    print("\n" + "="*80)
    print(f"\n✅ 완료! (시장: {total_market}건, 섹터: {total_sector}건)")


if __name__ == "__main__":
    main()
