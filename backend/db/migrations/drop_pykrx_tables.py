"""
pykrx 기반 테이블 삭제 Migration

sector_indices와 market_indices 테이블을 삭제합니다.
이 테이블들은 KIS API 기반 index_daily_price 테이블로 대체되었습니다.

Usage:
    uv run python backend/db/migrations/drop_pykrx_tables.py
"""
import logging
from sqlalchemy import text

from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def upgrade():
    """Migration 실행"""
    logger.info("=" * 80)
    logger.info("🗑️  Migration: pykrx 기반 테이블 삭제")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 1. sector_indices 테이블 삭제
        logger.info("\n1. sector_indices 테이블 삭제 중...")
        db.execute(text("DROP TABLE IF EXISTS sector_indices CASCADE;"))
        logger.info("   ✅ sector_indices 테이블 삭제 완료")

        # 2. market_indices 테이블 삭제
        logger.info("\n2. market_indices 테이블 삭제 중...")
        db.execute(text("DROP TABLE IF EXISTS market_indices CASCADE;"))
        logger.info("   ✅ market_indices 테이블 삭제 완료")

        db.commit()

        logger.info("\n" + "=" * 80)
        logger.info("✅ Migration 완료!")
        logger.info("=" * 80)

        # 남아있는 테이블 확인
        logger.info("\n📊 남아있는 지수 관련 테이블:")
        result = db.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename LIKE '%index%'
            ORDER BY tablename;
        """))

        for row in result:
            logger.info(f"   - {row[0]}")

    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ Migration 실패: {e}", exc_info=True)
        raise

    finally:
        db.close()


def downgrade():
    """Migration 롤백 (복구는 불가능 - 데이터 손실)"""
    logger.warning("=" * 80)
    logger.warning("⚠️  경고: 삭제된 테이블 복구 불가")
    logger.warning("=" * 80)
    logger.warning("sector_indices와 market_indices 테이블은 이미 삭제되었습니다.")
    logger.warning("복구가 필요한 경우 백업에서 복원해야 합니다.")


if __name__ == "__main__":
    upgrade()
