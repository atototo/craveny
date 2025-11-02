"""
시스템 상태 확인 스크립트

현재 시스템이 정상적으로 동작하고 있는지 확인합니다.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta
from sqlalchemy import func
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_status():
    """시스템 상태 확인"""
    logger.info("=" * 70)
    logger.info("📊 시스템 상태 확인")
    logger.info("=" * 70)

    db = SessionLocal()

    try:
        # 1. 전체 뉴스 개수
        total_news = db.query(func.count(NewsArticle.id)).scalar()
        logger.info(f"전체 뉴스: {total_news}건")

        # 2. 최근 1시간 이내 저장된 뉴스
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_news_count = (
            db.query(func.count(NewsArticle.id))
            .filter(NewsArticle.created_at >= one_hour_ago)
            .scalar()
        )
        logger.info(f"최근 1시간: {recent_news_count}건")

        # 3. 최근 24시간 이내 저장된 뉴스
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        daily_news_count = (
            db.query(func.count(NewsArticle.id))
            .filter(NewsArticle.created_at >= one_day_ago)
            .scalar()
        )
        logger.info(f"최근 24시간: {daily_news_count}건")

        # 4. 가장 최근 뉴스
        latest_news = (
            db.query(NewsArticle)
            .order_by(NewsArticle.created_at.desc())
            .first()
        )

        if latest_news:
            logger.info("")
            logger.info("📰 가장 최근 뉴스:")
            logger.info(f"   ID: {latest_news.id}")
            logger.info(f"   제목: {latest_news.title[:50]}...")
            logger.info(f"   출처: {latest_news.source}")
            logger.info(f"   종목: {latest_news.stock_code or 'N/A'}")
            logger.info(f"   저장 시각: {latest_news.created_at}")

            time_diff = datetime.utcnow() - latest_news.created_at
            hours_ago = time_diff.total_seconds() / 3600
            logger.info(f"   경과 시간: {hours_ago:.1f}시간 전")

        # 5. 종목 코드가 있는 뉴스
        news_with_stock = (
            db.query(func.count(NewsArticle.id))
            .filter(NewsArticle.stock_code.isnot(None))
            .scalar()
        )
        logger.info("")
        logger.info(f"종목 코드 매칭된 뉴스: {news_with_stock}건 / {total_news}건")

        # 6. 알림 전송된 뉴스
        notified_news = (
            db.query(func.count(NewsArticle.id))
            .filter(NewsArticle.notified_at.isnot(None))
            .scalar()
        )
        logger.info(f"알림 전송된 뉴스: {notified_news}건")

        # 7. 상태 판단
        logger.info("")
        logger.info("=" * 70)
        logger.info("💡 시스템 상태")
        logger.info("=" * 70)

        if recent_news_count > 0:
            logger.info("✅ 크롤러 정상 작동 중 (최근 1시간 이내 뉴스 수집)")
        else:
            logger.warning("⚠️  최근 1시간 동안 새 뉴스 없음")
            logger.warning("   - 크롤러가 실행되지 않았거나")
            logger.warning("   - 새로운 뉴스가 없는 상태일 수 있습니다")

        if latest_news and hours_ago < 0.5:
            logger.info("✅ 실시간 수집 중 (30분 이내 뉴스)")
        elif latest_news and hours_ago < 3:
            logger.info("🟡 정상 작동 중 (3시간 이내 뉴스)")
        else:
            logger.warning("🔴 크롤러 점검 필요 (뉴스가 오래됨)")

    finally:
        db.close()


if __name__ == "__main__":
    check_status()
