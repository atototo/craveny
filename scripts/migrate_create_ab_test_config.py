"""
A/B Test Config 테이블 생성 및 초기 데이터 마이그레이션

ab_test_config 테이블을 생성하고 GPT-4o vs DeepSeek 기본 설정을 추가합니다.
"""
import logging
from sqlalchemy import text
from backend.db.session import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(db) -> bool:
    """ab_test_config 테이블 존재 여부 확인"""
    result = db.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'ab_test_config'
        );
    """))
    return result.scalar()


def create_ab_test_config_table(db):
    """ab_test_config 테이블 생성"""
    logger.info("ab_test_config 테이블 생성 중...")

    db.execute(text("""
        CREATE TABLE ab_test_config (
            id SERIAL PRIMARY KEY,
            model_a_id INTEGER NOT NULL REFERENCES models(id),
            model_b_id INTEGER NOT NULL REFERENCES models(id),
            is_active BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """))

    # 인덱스 생성
    db.execute(text("""
        CREATE INDEX idx_ab_test_config_is_active ON ab_test_config(is_active);
    """))

    db.commit()
    logger.info("✅ ab_test_config 테이블 생성 완료")


def insert_default_config(db):
    """기본 A/B 테스트 설정 추가 (GPT-4o vs DeepSeek)"""
    logger.info("기본 A/B 테스트 설정 추가 중...")

    # 기존 활성 설정 비활성화
    db.execute(text("""
        UPDATE ab_test_config SET is_active = false WHERE is_active = true;
    """))

    # GPT-4o (ID=1) vs DeepSeek V3.2 (ID=2) 설정 추가
    db.execute(text("""
        INSERT INTO ab_test_config (model_a_id, model_b_id, is_active)
        VALUES (1, 2, true);
    """))

    db.commit()
    logger.info("✅ 기본 A/B 테스트 설정 추가 완료 (GPT-4o vs DeepSeek V3.2)")


def verify_migration(db):
    """마이그레이션 결과 확인"""
    logger.info("\n=== 마이그레이션 결과 확인 ===")

    # 테이블 존재 확인
    exists = check_table_exists(db)
    logger.info(f"ab_test_config 테이블 존재: {exists}")

    if exists:
        # 활성 설정 확인
        result = db.execute(text("""
            SELECT
                ac.id,
                m1.name as model_a_name,
                m2.name as model_b_name,
                ac.is_active,
                ac.created_at
            FROM ab_test_config ac
            JOIN models m1 ON ac.model_a_id = m1.id
            JOIN models m2 ON ac.model_b_id = m2.id
            WHERE ac.is_active = true;
        """))

        row = result.fetchone()
        if row:
            logger.info(f"활성 A/B 설정: Model A={row.model_a_name}, Model B={row.model_b_name}")
        else:
            logger.warning("활성 A/B 설정 없음")


def upgrade():
    """마이그레이션 실행"""
    db = SessionLocal()

    try:
        # 1. 테이블 존재 여부 확인
        if check_table_exists(db):
            logger.info("ab_test_config 테이블이 이미 존재합니다. 스킵합니다.")
            verify_migration(db)
            return

        # 2. 테이블 생성
        create_ab_test_config_table(db)

        # 3. 기본 설정 추가
        insert_default_config(db)

        # 4. 결과 확인
        verify_migration(db)

        logger.info("\n✅ A/B Test Config 마이그레이션 완료!")

    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def downgrade():
    """마이그레이션 롤백"""
    db = SessionLocal()

    try:
        logger.info("ab_test_config 테이블 삭제 중...")

        db.execute(text("DROP TABLE IF EXISTS ab_test_config CASCADE;"))
        db.commit()

        logger.info("✅ ab_test_config 테이블 삭제 완료")

    except Exception as e:
        logger.error(f"❌ 롤백 실패: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
