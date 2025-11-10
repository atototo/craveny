"""
시간외 거래 가격 테이블 추가 Migration

Usage:
    uv run python backend/db/migrations/add_overtime_price_table.py
"""
import logging
from sqlalchemy import text

from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def upgrade():
    """Migration 실행"""
    logger.info("=" * 80)
    logger.info("🚀 Migration: stock_overtime_price 테이블 생성")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 테이블 생성
        logger.info("\n1. 테이블 생성 중...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_overtime_price (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                date DATE NOT NULL,

                -- 시간외 거래 가격
                ovtm_untp_prpr FLOAT,
                ovtm_untp_prdy_vrss FLOAT,
                prdy_vrss_sign VARCHAR(1),
                ovtm_untp_prdy_ctrt FLOAT,

                -- 거래량/거래대금
                acml_vol BIGINT,
                acml_tr_pbmn BIGINT,

                -- 예상 체결 정보
                ovtm_untp_antc_cnpr FLOAT,
                ovtm_untp_antc_cntg_vrss FLOAT,
                ovtm_untp_antc_cntg_vrss_sign VARCHAR(1),
                ovtm_untp_antc_cntg_ctrt FLOAT,
                ovtm_untp_antc_vol BIGINT,

                -- 메타데이터
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT uk_overtime_price_stock_date UNIQUE (stock_code, date)
            );
        """))
        logger.info("   ✅ stock_overtime_price 테이블 생성 완료")

        # 인덱스 생성
        logger.info("\n2. 인덱스 생성 중...")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_overtime_price_stock_date
            ON stock_overtime_price(stock_code, date DESC);
        """))
        logger.info("   ✅ idx_overtime_price_stock_date 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_overtime_price_date
            ON stock_overtime_price(date DESC);
        """))
        logger.info("   ✅ idx_overtime_price_date 인덱스 생성")

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_overtime_price_stock_code
            ON stock_overtime_price(stock_code);
        """))
        logger.info("   ✅ idx_overtime_price_stock_code 인덱스 생성")

        # 외래키 제약 추가 (선택적)
        logger.info("\n3. 외래키 제약 추가 중...")
        db.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_stock_overtime_price_stock_code'
                ) THEN
                    ALTER TABLE stock_overtime_price
                    ADD CONSTRAINT fk_stock_overtime_price_stock_code
                    FOREIGN KEY (stock_code) REFERENCES stocks(code);
                END IF;
            END $$;
        """))
        logger.info("   ✅ fk_stock_overtime_price_stock_code 외래키 생성")

        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ Migration 완료!")
        logger.info("=" * 80)

        # 테이블 정보 출력
        logger.info("\n📊 테이블 정보:")
        result = db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'stock_overtime_price'
            ORDER BY ordinal_position;
        """))

        for row in result:
            logger.info(f"   {row[0]}: {row[1]} (NULL: {row[2]})")

        # 인덱스 정보 출력
        logger.info("\n📊 인덱스 정보:")
        result = db.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'stock_overtime_price';
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
    logger.info("🔙 Rollback: stock_overtime_price 테이블 삭제")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        db.execute(text("DROP TABLE IF EXISTS stock_overtime_price CASCADE;"))
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
