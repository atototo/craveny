"""
데이터베이스 마이그레이션: news_articles 테이블에 notified_at 컬럼 추가

notified_at 필드를 추가하여 중복 알림을 방지합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from sqlalchemy import text
from backend.db.session import engine

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate():
    """notified_at 컬럼 추가 마이그레이션"""
    logger.info("=" * 70)
    logger.info("🔧 데이터베이스 마이그레이션 시작")
    logger.info("=" * 70)

    try:
        with engine.connect() as conn:
            # 1. 컬럼이 이미 존재하는지 확인
            logger.info("1️⃣  기존 컬럼 확인 중...")
            result = conn.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'news_articles'
                    AND column_name = 'notified_at'
                    """
                )
            )
            exists = result.fetchone() is not None

            if exists:
                logger.warning("⚠️  notified_at 컬럼이 이미 존재합니다. 마이그레이션 건너뜀")
                return True

            # 2. 컬럼 추가
            logger.info("2️⃣  notified_at 컬럼 추가 중...")
            conn.execute(
                text(
                    """
                    ALTER TABLE news_articles
                    ADD COLUMN notified_at TIMESTAMP NULL
                    """
                )
            )
            conn.commit()

            logger.info("✅ notified_at 컬럼 추가 완료")

            # 3. 컬럼 추가 확인
            logger.info("3️⃣  마이그레이션 결과 확인 중...")
            result = conn.execute(
                text(
                    """
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'news_articles'
                    AND column_name = 'notified_at'
                    """
                )
            )
            row = result.fetchone()

            if row:
                logger.info(f"✅ 컬럼 정보: {row[0]} ({row[1]}, nullable={row[2]})")
            else:
                logger.error("❌ 컬럼 추가 실패")
                return False

            logger.info("")
            logger.info("=" * 70)
            logger.info("🎉 마이그레이션 완료")
            logger.info("=" * 70)
            return True

    except Exception as e:
        logger.error(f"❌ 마이그레이션 실패: {e}", exc_info=True)
        return False


def main():
    """메인 실행 함수"""
    logger.info("🚀 데이터베이스 마이그레이션 스크립트 시작")
    logger.info("")

    if migrate():
        logger.info("✅ 마이그레이션 성공")
        sys.exit(0)
    else:
        logger.error("❌ 마이그레이션 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
