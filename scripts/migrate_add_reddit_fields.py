"""
데이터베이스 마이그레이션: Reddit 통합을 위한 필드 추가

NewsArticle 테이블에 다음 필드들을 추가:
- content_type: 콘텐츠 타입 (news, reddit, twitter 등)
- url: 원본 URL
- author: 작성자
- upvotes: Reddit upvote 수
- num_comments: Reddit 댓글 수
- subreddit: Subreddit 이름
- metadata: JSON 메타데이터
"""
import logging
from sqlalchemy import text
from backend.db.session import SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def upgrade():
    """Reddit 지원 필드 추가"""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("Reddit 통합 마이그레이션 시작")
        logger.info("=" * 60)

        # 1. content_type enum 타입 생성
        logger.info("1. ContentType enum 생성 중...")
        db.execute(text("""
            DO $$ BEGIN
                CREATE TYPE contenttype AS ENUM ('news', 'reddit', 'twitter', 'telegram');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        logger.info("✅ ContentType enum 생성 완료")

        # 2. content_type 컬럼 추가
        logger.info("2. content_type 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS content_type contenttype NOT NULL DEFAULT 'news';
        """))
        logger.info("✅ content_type 컬럼 추가 완료")

        # 3. url 컬럼 추가
        logger.info("3. url 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS url VARCHAR(1000);
        """))
        logger.info("✅ url 컬럼 추가 완료")

        # 4. author 컬럼 추가
        logger.info("4. author 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS author VARCHAR(200);
        """))
        logger.info("✅ author 컬럼 추가 완료")

        # 5. upvotes 컬럼 추가
        logger.info("5. upvotes 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS upvotes INTEGER;
        """))
        logger.info("✅ upvotes 컬럼 추가 완료")

        # 6. num_comments 컬럼 추가
        logger.info("6. num_comments 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS num_comments INTEGER;
        """))
        logger.info("✅ num_comments 컬럼 추가 완료")

        # 7. subreddit 컬럼 추가
        logger.info("7. subreddit 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS subreddit VARCHAR(100);
        """))
        logger.info("✅ subreddit 컬럼 추가 완료")

        # 8. metadata 컬럼 추가 (JSONB)
        logger.info("8. metadata 컬럼 추가 중...")
        db.execute(text("""
            ALTER TABLE news_articles
            ADD COLUMN IF NOT EXISTS metadata JSONB;
        """))
        logger.info("✅ metadata 컬럼 추가 완료")

        # 9. 인덱스 생성
        logger.info("9. 인덱스 생성 중...")

        # content_type 인덱스
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_content_type
            ON news_articles(content_type);
        """))
        logger.info("✅ idx_news_articles_content_type 생성 완료")

        # subreddit 인덱스
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_subreddit
            ON news_articles(subreddit);
        """))
        logger.info("✅ idx_news_articles_subreddit 생성 완료")

        # source + content_type 복합 인덱스
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_news_articles_source_type
            ON news_articles(source, content_type);
        """))
        logger.info("✅ idx_news_articles_source_type 생성 완료")

        # 10. 기존 데이터 backfill (content_type을 'news'로 설정)
        logger.info("10. 기존 데이터 backfill 중...")
        result = db.execute(text("""
            UPDATE news_articles
            SET content_type = 'news'
            WHERE content_type IS NULL;
        """))
        logger.info(f"✅ {result.rowcount}건의 기존 데이터를 'news'로 설정 완료")

        db.commit()

        logger.info("=" * 60)
        logger.info("✅ Reddit 통합 마이그레이션 완료!")
        logger.info("=" * 60)

        # 결과 확인
        logger.info("\n📊 마이그레이션 결과 확인:")
        result = db.execute(text("""
            SELECT
                content_type,
                COUNT(*) as count
            FROM news_articles
            GROUP BY content_type;
        """))

        for row in result:
            logger.info(f"  - {row.content_type}: {row.count}건")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 마이그레이션 실패: {e}", exc_info=True)
        raise
    finally:
        db.close()


def downgrade():
    """마이그레이션 롤백 (Reddit 필드 제거)"""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("Reddit 통합 마이그레이션 롤백 시작")
        logger.info("=" * 60)

        # 인덱스 삭제
        logger.info("1. 인덱스 삭제 중...")
        db.execute(text("DROP INDEX IF EXISTS idx_news_articles_source_type;"))
        db.execute(text("DROP INDEX IF EXISTS idx_news_articles_subreddit;"))
        db.execute(text("DROP INDEX IF EXISTS idx_news_articles_content_type;"))
        logger.info("✅ 인덱스 삭제 완료")

        # 컬럼 삭제
        logger.info("2. 컬럼 삭제 중...")
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS metadata;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS subreddit;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS num_comments;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS upvotes;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS author;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS url;"))
        db.execute(text("ALTER TABLE news_articles DROP COLUMN IF EXISTS content_type;"))
        logger.info("✅ 컬럼 삭제 완료")

        # enum 타입 삭제
        logger.info("3. ContentType enum 삭제 중...")
        db.execute(text("DROP TYPE IF EXISTS contenttype;"))
        logger.info("✅ ContentType enum 삭제 완료")

        db.commit()

        logger.info("=" * 60)
        logger.info("✅ Reddit 통합 마이그레이션 롤백 완료!")
        logger.info("=" * 60)

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 롤백 실패: {e}", exc_info=True)
        raise
    finally:
        db.close()


def check_migration_status():
    """마이그레이션 상태 확인"""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("마이그레이션 상태 확인")
        logger.info("=" * 60)

        # 컬럼 존재 여부 확인
        result = db.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'news_articles'
            AND column_name IN (
                'content_type', 'url', 'author', 'upvotes',
                'num_comments', 'subreddit', 'metadata'
            )
            ORDER BY column_name;
        """))

        columns = list(result)

        if columns:
            logger.info("\n✅ Reddit 통합 필드가 존재합니다:")
            for col in columns:
                logger.info(f"  - {col.column_name}: {col.data_type}")
        else:
            logger.info("\n⚠️ Reddit 통합 필드가 없습니다. 마이그레이션을 실행하세요.")

        # 인덱스 존재 여부 확인
        result = db.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'news_articles'
            AND indexname LIKE '%content_type%' OR indexname LIKE '%subreddit%';
        """))

        indexes = list(result)

        if indexes:
            logger.info("\n✅ Reddit 관련 인덱스:")
            for idx in indexes:
                logger.info(f"  - {idx.indexname}")

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 상태 확인 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("사용법:")
        print("  python scripts/migrate_add_reddit_fields.py upgrade   # 마이그레이션 실행")
        print("  python scripts/migrate_add_reddit_fields.py downgrade # 마이그레이션 롤백")
        print("  python scripts/migrate_add_reddit_fields.py status    # 상태 확인")
        sys.exit(1)

    command = sys.argv[1]

    if command == "upgrade":
        upgrade()
    elif command == "downgrade":
        # 롤백 확인
        response = input("⚠️ 정말로 마이그레이션을 롤백하시겠습니까? (yes/no): ")
        if response.lower() == "yes":
            downgrade()
        else:
            print("롤백이 취소되었습니다.")
    elif command == "status":
        check_migration_status()
    else:
        print(f"❌ 알 수 없는 명령어: {command}")
        sys.exit(1)
