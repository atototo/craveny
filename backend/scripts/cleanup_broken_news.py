#!/usr/bin/env python
"""
깨진 뉴스 데이터를 삭제하는 스크립트

사용법:
    uv run python -m backend.scripts.cleanup_broken_news
"""
import logging
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.utils.encoding_normalizer import get_encoding_normalizer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def delete_broken_news(db: Session) -> int:
    """
    깨진 뉴스를 모두 삭제합니다.

    Args:
        db: 데이터베이스 세션

    Returns:
        삭제된 건수
    """
    normalizer = get_encoding_normalizer()

    # 모든 뉴스 조회
    news_list = db.query(NewsArticle).all()
    logger.info(f"검사 대상: {len(news_list)}개 뉴스")

    deleted_count = 0

    for news in news_list:
        # 깨진 문자가 있는지 확인
        if normalizer.has_broken_text(news.title) or normalizer.has_broken_text(news.content):
            logger.warning(f"ID {news.id}: 깨진 뉴스 삭제 -> {news.title[:50]}")
            db.delete(news)
            deleted_count += 1

    # 변경 사항 커밋
    db.commit()
    logger.info(f"삭제 완료: {deleted_count}건 삭제")

    return deleted_count


def main():
    """메인 함수"""
    db = SessionLocal()

    try:
        logger.info("🧹 깨진 뉴스 정리 시작...")
        deleted_count = delete_broken_news(db)
        logger.info(f"✅ 정리 완료: {deleted_count}건 삭제")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()
