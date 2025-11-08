"""
DB 마이그레이션 적용: stock_code UNIQUE 제약조건 제거
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.session import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def apply_migration():
    """UNIQUE 제약조건 제거 및 인덱스 재구성"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info("🔧 DB 마이그레이션 시작")
        logger.info("=" * 80)

        # Step 1: Drop UNIQUE constraint
        logger.info("\n1️⃣ UNIQUE 제약조건 제거 중...")
        db.execute(text("""
            DROP INDEX IF EXISTS ix_stock_analysis_summaries_stock_code;
        """))
        logger.info("✅ UNIQUE 인덱스 제거 완료")

        # Step 2: Create regular index
        logger.info("\n2️⃣ 일반 인덱스 생성 중...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_stock_analysis_stock_code
            ON stock_analysis_summaries(stock_code);
        """))
        logger.info("✅ stock_code 인덱스 생성 완료")

        # Step 3: Create composite index
        logger.info("\n3️⃣ 복합 인덱스 생성 중...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_stock_analysis_stock_code_date
            ON stock_analysis_summaries(stock_code, last_updated DESC);
        """))
        logger.info("✅ (stock_code, last_updated) 복합 인덱스 생성 완료")

        db.commit()

        # Verification
        logger.info("\n4️⃣ 인덱스 확인 중...")
        result = db.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'stock_analysis_summaries';
        """))

        logger.info("\n📊 현재 인덱스 목록:")
        for row in result:
            logger.info(f"  - {row.indexname}")
            logger.info(f"    {row.indexdef}")

        logger.info("\n" + "=" * 80)
        logger.info("🎉 마이그레이션 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()

    return True


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
