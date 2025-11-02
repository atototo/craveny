#!/usr/bin/env python
"""
깨진 인코딩의 뉴스 데이터를 복구하는 마이그레이션 스크립트

사용법:
    python -m backend.scripts.fix_encoding
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


def fix_broken_news(db: Session) -> tuple[int, int]:
    """
    데이터베이스의 모든 깨진 뉴스를 복구합니다.

    Args:
        db: 데이터베이스 세션

    Returns:
        (복구된 건수, 삭제된 건수) 튜플
    """
    normalizer = get_encoding_normalizer()

    # 모든 뉴스 조회
    news_list = db.query(NewsArticle).all()
    logger.info(f"검사 대상: {len(news_list)}개 뉴스")

    fixed_count = 0
    deleted_count = 0

    for news in news_list:
        has_broken_title = normalizer.has_broken_text(news.title)
        has_broken_content = normalizer.has_broken_text(news.content)

        if not has_broken_title and not has_broken_content:
            continue

        logger.warning(f"ID {news.id}: 깨진 텍스트 감지")

        # 제목 복구
        if has_broken_title:
            fixed_title = normalizer.try_fix_broken_encoding(news.title)
            if fixed_title and fixed_title.strip():
                news.title = fixed_title
                logger.info(f"ID {news.id}: 제목 복구 -> {fixed_title[:50]}")
                fixed_count += 1
            else:
                # 제목 복구 실패 시 뉴스 삭제
                logger.error(f"ID {news.id}: 제목 복구 실패, 뉴스 삭제")
                db.delete(news)
                deleted_count += 1
                continue

        # 본문 복구
        if has_broken_content:
            fixed_content = normalizer.try_fix_broken_encoding(news.content)
            if fixed_content:
                news.content = fixed_content
                logger.info(f"ID {news.id}: 본문 복구")
                if not has_broken_title:  # 제목이 정상이면 고정 카운트 증가
                    fixed_count += 1

        # 변경 사항 커밋
        db.commit()

    logger.info(f"복구 완료: {fixed_count}건 복구, {deleted_count}건 삭제")
    return (fixed_count, deleted_count)


def main():
    """메인 함수"""
    db = SessionLocal()

    try:
        logger.info("🔧 깨진 인코딩 복구 시작...")
        fixed_count, deleted_count = fix_broken_news(db)

        if fixed_count > 0 or deleted_count > 0:
            logger.info(f"✅ 복구 완료: {fixed_count}건 복구, {deleted_count}건 삭제")
        else:
            logger.info("ℹ️  깨진 뉴스가 없습니다")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    main()
