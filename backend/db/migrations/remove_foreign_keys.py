"""
Foreign Key 제약조건 제거 마이그레이션

- predictions.model_id FK 제거
- ab_test_config.model_a_id FK 제거
- ab_test_config.model_b_id FK 제거

실행 방법:
    python backend/db/migrations/remove_foreign_keys.py
"""
import logging
from sqlalchemy import text
from backend.db.session import engine

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def remove_foreign_keys():
    """Foreign Key 제약조건 제거"""

    with engine.connect() as conn:
        try:
            logger.info("=" * 80)
            logger.info("🔧 Foreign Key 제약조건 제거 시작")
            logger.info("=" * 80)

            # PostgreSQL: FK 이름 확인
            logger.info("\n📋 현재 Foreign Key 확인 중...")

            check_fks_query = text("""
                SELECT
                    tc.constraint_name,
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND (
                    (tc.table_name = 'predictions' AND kcu.column_name = 'model_id')
                    OR (tc.table_name = 'ab_test_config' AND kcu.column_name IN ('model_a_id', 'model_b_id'))
                );
            """)

            result = conn.execute(check_fks_query)
            fks = result.fetchall()

            if not fks:
                logger.warning("⚠️ 제거할 Foreign Key가 없습니다.")
                return

            logger.info(f"\n✅ {len(fks)}개의 Foreign Key 발견:")
            for fk in fks:
                logger.info(f"  - {fk[1]}.{fk[2]} → {fk[3]} (제약조건: {fk[0]})")

            # FK 제거
            logger.info("\n🔄 Foreign Key 제거 중...")

            for fk in fks:
                constraint_name = fk[0]
                table_name = fk[1]

                drop_fk_query = text(f"""
                    ALTER TABLE {table_name}
                    DROP CONSTRAINT IF EXISTS {constraint_name};
                """)

                conn.execute(drop_fk_query)
                logger.info(f"  ✅ {table_name}.{constraint_name} 제거 완료")

            conn.commit()

            # 인덱스는 유지 (성능을 위해)
            logger.info("\n📊 인덱스 확인 중...")

            check_indexes_query = text("""
                SELECT
                    tablename,
                    indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                AND (
                    (tablename = 'predictions' AND indexname LIKE '%model_id%')
                    OR (tablename = 'ab_test_config' AND indexname LIKE '%model_%_id%')
                );
            """)

            result = conn.execute(check_indexes_query)
            indexes = result.fetchall()

            if indexes:
                logger.info("✅ 인덱스 유지됨 (성능 보장):")
                for idx in indexes:
                    logger.info(f"  - {idx[0]}.{idx[1]}")

            logger.info("\n" + "=" * 80)
            logger.info("✅ Foreign Key 제거 완료!")
            logger.info("=" * 80)
            logger.info("\n다음 단계:")
            logger.info("  1. 애플리케이션 레벨 무결성 검증 활성화")
            logger.info("  2. 모델 삭제 시 영향도 로깅")
            logger.info("  3. 정상 작동 확인")

        except Exception as e:
            conn.rollback()
            logger.error(f"\n❌ 마이그레이션 실패: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    remove_foreign_keys()
