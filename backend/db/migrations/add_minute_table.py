"""
1분봉 테이블 추가 Migration

Usage:
    uv run python backend/db/migrations/add_minute_table.py
"""
import logging
from sqlalchemy import text

from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def upgrade():
    """Migration 실행"""
    logger.info("=" * 80)
    logger.info("🚀 Migration: stock_prices_minute 테이블 생성")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 테이블 생성
        logger.info("\n1. 테이블 생성 중...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_prices_minute (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT,
                source VARCHAR(20) DEFAULT 'kis',
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT uk_stock_datetime UNIQUE (stock_code, datetime)
            );
        """))
        logger.info("   ✅ stock_prices_minute 테이블 생성 완료")

        # 인덱스 생성
        logger.info("\n2. 인덱스 생성 중...")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_stock_datetime
            ON stock_prices_minute(stock_code, datetime DESC);
        """))
        logger.info("   ✅ idx_minute_stock_datetime 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_datetime
            ON stock_prices_minute(datetime DESC);
        """))
        logger.info("   ✅ idx_minute_datetime 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_source
            ON stock_prices_minute(source);
        """))
        logger.info("   ✅ idx_minute_source 인덱스 생성")

        # 외래키 제약 추가 (선택적)
        logger.info("\n3. 외래키 제약 추가 중...")
        db.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_stock_prices_minute_stock_code'
                ) THEN
                    ALTER TABLE stock_prices_minute
                    ADD CONSTRAINT fk_stock_prices_minute_stock_code
                    FOREIGN KEY (stock_code) REFERENCES stocks(code);
                END IF;
            END $$;
        """))
        logger.info("   ✅ fk_stock_prices_minute_stock_code 외래키 생성")

        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ Migration 완료!")
        logger.info("=" * 80)

        # 테이블 정보 출력
        logger.info("\n📊 테이블 정보:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'stock_prices_minute'
            ORDER BY ordinal_position;
        """))

        for row in result:
            logger.info(f"   {row[0]}: {row[1]} (NULL: {row[2]})")

        # 인덱스 정보 출력
        logger.info("\n📊 인덱스 정보:")
        result = db.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'stock_prices_minute';
        """))

        for row in result:
            logger.info(f"   {row[0]}")

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ Migration 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


def downgrade():
    """Migration 롤백"""
    logger.info("=" * 80)
    logger.info("🔙 Rollback: stock_prices_minute 테이블 삭제")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        db.execute(text("DROP TABLE IF EXISTS stock_prices_minute CASCADE;"))
        db.commit()
        logger.info("\n✅ Rollback 완료!")

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ Rollback 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    upgrade()
