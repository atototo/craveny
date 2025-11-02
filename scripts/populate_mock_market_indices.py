"""
임시 시장 지수 데이터 삽입 스크립트

FinanceDataReader API가 rate limit 중이므로,
테스트용 mock 데이터를 삽입하여 시스템 통합 테스트를 진행합니다.

TODO: FinanceDataReader API 안정화 후 실제 데이터 수집으로 교체
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from backend.db.session import engine


def insert_mock_market_indices(days: int = 30):
    """테스트용 시장 지수 mock 데이터 삽입"""

    with engine.connect() as conn:
        print("🚀 Mock 시장 지수 데이터 삽입 시작...\n")

        # 기준값
        base_kospi = 2500.0
        base_kosdaq = 850.0

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        inserted_count = {"KOSPI": 0, "KOSDAQ": 0}

        # 날짜별로 데이터 생성
        current_date = start_date
        while current_date <= end_date:
            # 주말 제외
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue

            # KOSPI 데이터 생성
            kospi_close = base_kospi + random.uniform(-50, 50)
            kospi_open = kospi_close + random.uniform(-10, 10)
            kospi_high = max(kospi_open, kospi_close) + random.uniform(0, 15)
            kospi_low = min(kospi_open, kospi_close) - random.uniform(0, 15)
            kospi_change = random.uniform(-1.5, 1.5)

            conn.execute(
                text(
                    """
                    INSERT INTO market_indices
                    (index_name, date, open, high, low, close, volume, change_pct)
                    VALUES
                    (:index_name, :date, :open, :high, :low, :close, :volume, :change_pct)
                    ON CONFLICT DO NOTHING
                """
                ),
                {
                    "index_name": "KOSPI",
                    "date": current_date,
                    "open": kospi_open,
                    "high": kospi_high,
                    "low": kospi_low,
                    "close": kospi_close,
                    "volume": random.randint(300000000, 500000000),
                    "change_pct": kospi_change,
                },
            )
            inserted_count["KOSPI"] += 1

            # KOSDAQ 데이터 생성
            kosdaq_close = base_kosdaq + random.uniform(-30, 30)
            kosdaq_open = kosdaq_close + random.uniform(-5, 5)
            kosdaq_high = max(kosdaq_open, kosdaq_close) + random.uniform(0, 10)
            kosdaq_low = min(kosdaq_open, kosdaq_close) - random.uniform(0, 10)
            kosdaq_change = random.uniform(-2.0, 2.0)

            conn.execute(
                text(
                    """
                    INSERT INTO market_indices
                    (index_name, date, open, high, low, close, volume, change_pct)
                    VALUES
                    (:index_name, :date, :open, :high, :low, :close, :volume, :change_pct)
                    ON CONFLICT DO NOTHING
                """
                ),
                {
                    "index_name": "KOSDAQ",
                    "date": current_date,
                    "open": kosdaq_open,
                    "high": kosdaq_high,
                    "low": kosdaq_low,
                    "close": kosdaq_close,
                    "volume": random.randint(800000000, 1200000000),
                    "change_pct": kosdaq_change,
                },
            )
            inserted_count["KOSDAQ"] += 1

            current_date += timedelta(days=1)

        conn.commit()

        print("📊 삽입 결과:")
        print(f"  KOSPI: {inserted_count['KOSPI']}건")
        print(f"  KOSDAQ: {inserted_count['KOSDAQ']}건")

        # 최신 데이터 확인
        print("\n📈 최신 데이터:")
        for index_name in ["KOSPI", "KOSDAQ"]:
            result = conn.execute(
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
                print(
                    f"  {row[0]}: {row[2]:.2f} ({row[3]:+.2f}%) - {row[1].strftime('%Y-%m-%d')}"
                )

        print("\n✅ Mock 데이터 삽입 완료!")
        print("\n⚠️  주의: 이 데이터는 테스트용 mock 데이터입니다.")
        print("   FinanceDataReader API 안정화 후 실제 데이터로 교체 필요")


if __name__ == "__main__":
    insert_mock_market_indices(days=30)
