"""
시장 지수 및 종목 펀더멘털 테이블 추가 마이그레이션

Phase 2에서 추가되는 테이블:
1. market_indices: KOSPI, KOSDAQ 지수 데이터
2. sector_indices: 섹터별 지수 데이터 (선택적)
3. stocks 테이블에 펀더멘털 컬럼 추가 (market_cap, sector, per, pbr)
4. news_stock_match 테이블에 시계열 컬럼 추가 (price_change_2d, 10d, 20d)
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from backend.db.session import engine


def run_migration():
    """마이그레이션 실행"""

    with engine.connect() as conn:
        print("🚀 Phase 2 마이그레이션 시작...\n")

        # 1. market_indices 테이블 생성
        print("1. market_indices 테이블 생성 중...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS market_indices (
                id SERIAL PRIMARY KEY,
                index_name VARCHAR(50) NOT NULL,
                date TIMESTAMP NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT,
                change_pct FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_market_indices_name_date
            ON market_indices (index_name, date DESC);
        """))
        print("✅ market_indices 테이블 생성 완료\n")

        # 2. sector_indices 테이블 생성 (선택적)
        print("2. sector_indices 테이블 생성 중...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sector_indices (
                id SERIAL PRIMARY KEY,
                sector_name VARCHAR(100) NOT NULL,
                date TIMESTAMP NOT NULL,
                close FLOAT NOT NULL,
                change_pct FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sector_indices_name_date
            ON sector_indices (sector_name, date DESC);
        """))
        print("✅ sector_indices 테이블 생성 완료\n")

        # 3. stocks 테이블에 컬럼 추가
        print("3. stocks 테이블에 펀더멘털 컬럼 추가 중...")

        # 이미 존재하는 컬럼인지 확인
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'stocks' AND column_name IN ('market_cap', 'sector', 'per', 'pbr');
        """))
        existing_columns = [row[0] for row in result]

        if 'market_cap' not in existing_columns:
            conn.execute(text("ALTER TABLE stocks ADD COLUMN market_cap BIGINT;"))
            print("  ✅ market_cap 컬럼 추가")
        else:
            print("  ⏭️  market_cap 컬럼 이미 존재")

        if 'sector' not in existing_columns:
            conn.execute(text("ALTER TABLE stocks ADD COLUMN sector VARCHAR(100);"))
            print("  ✅ sector 컬럼 추가")
        else:
            print("  ⏭️  sector 컬럼 이미 존재")

        if 'per' not in existing_columns:
            conn.execute(text("ALTER TABLE stocks ADD COLUMN per FLOAT;"))
            print("  ✅ per 컬럼 추가")
        else:
            print("  ⏭️  per 컬럼 이미 존재")

        if 'pbr' not in existing_columns:
            conn.execute(text("ALTER TABLE stocks ADD COLUMN pbr FLOAT;"))
            print("  ✅ pbr 컬럼 추가")
        else:
            print("  ⏭️  pbr 컬럼 이미 존재")

        print()

        # 4. news_stock_matches 테이블에 시계열 컬럼 추가
        print("4. news_stock_matches 테이블에 시계열 컬럼 추가 중...")

        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'news_stock_matches'
            AND column_name IN ('price_change_2d', 'price_change_10d', 'price_change_20d');
        """))
        existing_match_columns = [row[0] for row in result]

        if 'price_change_2d' not in existing_match_columns:
            conn.execute(text("ALTER TABLE news_stock_matches ADD COLUMN price_change_2d FLOAT;"))
            print("  ✅ price_change_2d 컬럼 추가")
        else:
            print("  ⏭️  price_change_2d 컬럼 이미 존재")

        if 'price_change_10d' not in existing_match_columns:
            conn.execute(text("ALTER TABLE news_stock_matches ADD COLUMN price_change_10d FLOAT;"))
            print("  ✅ price_change_10d 컬럼 추가")
        else:
            print("  ⏭️  price_change_10d 컬럼 이미 존재")

        if 'price_change_20d' not in existing_match_columns:
            conn.execute(text("ALTER TABLE news_stock_matches ADD COLUMN price_change_20d FLOAT;"))
            print("  ✅ price_change_20d 컬럼 추가")
        else:
            print("  ⏭️  price_change_20d 컬럼 이미 존재")

        conn.commit()
        print("\n✅ Phase 2 마이그레이션 완료!")


if __name__ == "__main__":
    run_migration()
