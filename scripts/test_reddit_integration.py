"""
Reddit 통합 테스트 스크립트

Reddit 크롤링 → DB 저장 → 예측 생성까지 전체 플로우를 테스트합니다.
"""
import logging
from datetime import datetime

from backend.db.session import SessionLocal
from backend.crawlers.reddit_crawler import RedditCrawler
from backend.crawlers.news_saver import NewsSaver


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_reddit_integration():
    """Reddit 통합 테스트 실행"""

    logger.info("=" * 60)
    logger.info("Reddit 통합 테스트 시작")
    logger.info("=" * 60)

    # 1. Reddit 크롤링
    logger.info("\n1️⃣ Reddit 크롤링 시작...")
    crawler = RedditCrawler(
        subreddits=['investing'],  # 테스트용으로 1개만
        min_upvotes=10,
        min_comments=2,
        lookback_hours=24,
    )

    news_list = crawler.fetch_news(limit=20)
    logger.info(f"✅ 크롤링 완료: {len(news_list)}개 게시글 수집")

    if not news_list:
        logger.warning("⚠️ 수집된 게시글이 없습니다. 테스트 종료.")
        return

    # 2. DB 저장
    logger.info("\n2️⃣ DB 저장 시작...")
    db = SessionLocal()

    try:
        saver = NewsSaver(db, auto_predict=True)  # 자동 예측 활성화

        saved_count, skipped_count = saver.save_news_batch(news_list)

        logger.info(f"✅ DB 저장 완료: 저장 {saved_count}건, 중복 스킵 {skipped_count}건")

        # 3. 결과 확인
        logger.info("\n3️⃣ 결과 확인...")

        from sqlalchemy import text

        # Reddit 게시글 수 확인
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM news_articles
            WHERE content_type = 'reddit'
        """))
        reddit_count = result.scalar()
        logger.info(f"📊 DB에 저장된 Reddit 게시글: {reddit_count}건")

        # 최근 Reddit 게시글 확인
        result = db.execute(text("""
            SELECT
                id,
                title,
                author,
                subreddit,
                upvotes,
                num_comments,
                stock_code,
                created_at
            FROM news_articles
            WHERE content_type = 'reddit'
            ORDER BY created_at DESC
            LIMIT 5
        """))

        logger.info("\n최근 Reddit 게시글 5개:")
        for row in result:
            logger.info(
                f"  - ID={row.id}, 제목='{row.title[:50]}...', "
                f"작성자={row.author}, subreddit={row.subreddit}, "
                f"upvotes={row.upvotes}, comments={row.num_comments}, "
                f"종목={row.stock_code or 'N/A'}"
            )

        # 예측 생성 확인
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM predictions p
            JOIN news_articles n ON p.news_id = n.id
            WHERE n.content_type = 'reddit'
        """))
        prediction_count = result.scalar()
        logger.info(f"\n📈 Reddit 게시글에 대한 예측: {prediction_count}건")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Reddit 통합 테스트 완료!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    test_reddit_integration()
