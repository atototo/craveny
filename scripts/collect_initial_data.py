"""
초기 데이터 수집 스크립트

대상 종목의 최근 30일 뉴스를 수집합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta

from backend.crawlers.naver_search_crawler import NaverNewsSearchCrawler
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 대상 종목 정의
TARGET_STOCKS = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
    {"code": "005380", "name": "현대차"},
    {"code": "035420", "name": "네이버"},
    {"code": "003670", "name": "포스코퓨처엠"},
]

# 수집 기간
DAYS_TO_COLLECT = 30


def collect_news_for_stock(stock_code: str, stock_name: str, days: int = 30) -> int:
    """
    특정 종목의 뉴스를 수집합니다.

    Args:
        stock_code: 종목 코드
        stock_name: 종목명
        days: 수집할 기간 (일)

    Returns:
        수집된 뉴스 개수
    """
    logger.info("=" * 60)
    logger.info(f"📰 {stock_name} ({stock_code}) 뉴스 수집 시작")
    logger.info("=" * 60)

    db = SessionLocal()
    crawler = NaverNewsSearchCrawler()

    try:
        # 기간 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logger.info(f"수집 기간: {start_date.date()} ~ {end_date.date()}")

        # 뉴스 수집
        news_items = crawler.search_news(
            query=stock_name, start_date=start_date, end_date=end_date, limit=100
        )

        if not news_items:
            logger.warning(f"⚠️  {stock_name}: 수집된 뉴스가 없습니다")
            return 0

        logger.info(f"✅ {len(news_items)}건의 뉴스를 수집했습니다")

        # 데이터베이스 저장
        saved_count = 0
        duplicate_count = 0

        for item in news_items:
            # 중복 확인 (제목으로 체크 - url 필드가 없음)
            existing = (
                db.query(NewsArticle).filter(NewsArticle.title == item.title).first()
            )

            if existing:
                duplicate_count += 1
                continue

            # 새 뉴스 저장 (url 필드는 현재 모델에 없음)
            news = NewsArticle(
                title=item.title,
                content=item.content,
                source=item.source,
                published_at=item.published_at,
                stock_code=stock_code,
            )

            db.add(news)
            saved_count += 1

        db.commit()

        logger.info(f"💾 저장 완료: {saved_count}건 (중복 제외: {duplicate_count}건)")
        logger.info("")

        return saved_count

    except Exception as e:
        logger.error(f"❌ {stock_name} 뉴스 수집 실패: {e}", exc_info=True)
        db.rollback()
        return 0

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 초기 데이터 수집 시작")
    logger.info(f"대상 종목: {len(TARGET_STOCKS)}개")
    logger.info(f"수집 기간: 최근 {DAYS_TO_COLLECT}일")
    logger.info("")

    total_collected = 0

    # 각 종목별 뉴스 수집
    for stock in TARGET_STOCKS:
        count = collect_news_for_stock(
            stock_code=stock["code"],
            stock_name=stock["name"],
            days=DAYS_TO_COLLECT,
        )
        total_collected += count

    # 최종 결과
    logger.info("=" * 60)
    logger.info("✅ 초기 데이터 수집 완료")
    logger.info("=" * 60)
    logger.info(f"총 수집 뉴스: {total_collected}건")
    logger.info("")

    # 다음 단계 안내
    logger.info("📋 다음 단계:")
    logger.info("   1. 뉴스 임베딩: uv run python -m backend.llm.embedder")
    logger.info("   2. 주가 매칭: uv run python -m backend.crawlers.news_stock_matcher")
    logger.info("")


if __name__ == "__main__":
    main()
