"""
stock_prices 테이블에 source 컬럼 추가

Migration: 003.2 - 일봉 수집기 (FDR + KIS Dual-run)
"""
import logging
from sqlalchemy import text
from backend.db.session import SessionLocal

logger = logging.getLogger(__name__)


def upgrade():
    """
    stock_prices 테이블에 source 컬럼 추가
    """
    db = SessionLocal()

    try:
        logger.info("=== Migration 시작: source 컬럼 추가 ===")

        # 1. source 컬럼 추가 (기본값: 'fdr')
        db.execute(text("""
            ALTER TABLE stock_prices
            ADD COLUMN IF NOT EXISTS source VARCHAR(10) NOT NULL DEFAULT 'fdr';
        """))

        logger.info("✅ source 컬럼 추가 완료")

        # 2. 인덱스 추가
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_stock_prices_date_source
            ON stock_prices (date, source);
        """))

        logger.info("✅ 인덱스 추가 완료")

        # 3. 기존 데이터 source 업데이트 ('fdr'로 설정)
        result = db.execute(text("""
            UPDATE stock_prices
            SET source = 'fdr'
            WHERE source IS NULL;
        """))

        logger.info(f"✅ 기존 데이터 업데이트 완료: {result.rowcount}건")

        db.commit()

        logger.info("=== Migration 완료 ===")

    except Exception as e:
        logger.error(f"❌ Migration 실패: {e}")
        db.rollback()
        raise

    finally:
        db.close()


def downgrade():
    """
    source 컬럼 제거 (롤백)
    """
    db = SessionLocal()

    try:
        logger.info("=== Rollback 시작: source 컬럼 제거 ===")

        # 1. 인덱스 제거
        db.execute(text("""
            DROP INDEX IF EXISTS idx_stock_prices_date_source;
        """))

        logger.info("✅ 인덱스 제거 완료")

        # 2. 컬럼 제거
        db.execute(text("""
            ALTER TABLE stock_prices
            DROP COLUMN IF EXISTS source;
        """))

        logger.info("✅ source 컬럼 제거 완료")

        db.commit()

        logger.info("=== Rollback 완료 ===")

    except Exception as e:
        logger.error(f"❌ Rollback 실패: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Migration 실행
    upgrade()

    print("\n✅ Migration 완료!")
    print("stock_prices 테이블에 source 컬럼이 추가되었습니다.")
