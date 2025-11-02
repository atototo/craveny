"""
벡터 검색 테스트 스크립트

유사 뉴스 검색 및 주가 변동률 조회를 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from backend.llm.vector_search import NewsVectorSearch
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_search_similar_news():
    """유사 뉴스 검색 테스트"""
    logger.info("=" * 60)
    logger.info("🔍 유사 뉴스 검색 테스트")
    logger.info("=" * 60)

    vector_search = NewsVectorSearch()

    # 테스트 뉴스 텍스트
    test_text = "삼성전자가 3나노 공정 개발에 성공하여 반도체 산업에 큰 영향을 미칠 것으로 예상됩니다."

    logger.info(f"검색 텍스트: {test_text}")
    logger.info("")

    # 유사 뉴스 검색
    similar_news = vector_search.search_similar_news(
        news_text=test_text,
        stock_code=None,  # 전체 종목
        top_k=5,
        similarity_threshold=0.5,
    )

    if similar_news:
        logger.info(f"✅ 유사 뉴스 {len(similar_news)}건 발견")
        for i, news in enumerate(similar_news, 1):
            logger.info(f"\n{i}. 뉴스 ID: {news['news_id']}")
            logger.info(f"   유사도: {news['similarity']:.4f}")
            logger.info(f"   종목: {news['stock_code']}")
            logger.info(f"   발표일: {news['published_at']}")
    else:
        logger.warning("⚠️  유사 뉴스를 찾지 못했습니다")

    logger.info("")
    return len(similar_news) > 0


def test_search_with_stock_filter():
    """종목 필터링 검색 테스트"""
    logger.info("=" * 60)
    logger.info("🎯 종목 필터링 검색 테스트")
    logger.info("=" * 60)

    vector_search = NewsVectorSearch()

    test_text = "SK하이닉스의 메모리 반도체 실적이 개선되고 있습니다."
    stock_code = "000660"  # SK하이닉스

    logger.info(f"검색 텍스트: {test_text}")
    logger.info(f"종목 코드: {stock_code}")
    logger.info("")

    similar_news = vector_search.search_similar_news(
        news_text=test_text,
        stock_code=stock_code,
        top_k=3,
        similarity_threshold=0.5,
    )

    if similar_news:
        logger.info(f"✅ {stock_code} 관련 유사 뉴스 {len(similar_news)}건 발견")
        for i, news in enumerate(similar_news, 1):
            logger.info(f"\n{i}. 뉴스 ID: {news['news_id']}")
            logger.info(f"   유사도: {news['similarity']:.4f}")
    else:
        logger.info(f"⚠️  {stock_code} 관련 유사 뉴스를 찾지 못했습니다")

    logger.info("")
    return True


def test_get_news_with_price_changes():
    """유사 뉴스 + 주가 변동률 조회 테스트"""
    logger.info("=" * 60)
    logger.info("📈 유사 뉴스 + 주가 변동률 조회 테스트")
    logger.info("=" * 60)

    db = SessionLocal()
    vector_search = NewsVectorSearch()

    try:
        # DB에서 실제 뉴스 가져오기
        sample_news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .first()
        )

        if not sample_news:
            logger.warning("⚠️  테스트할 뉴스가 없습니다")
            return False

        logger.info(f"테스트 뉴스: {sample_news.title[:50]}...")
        logger.info(f"종목: {sample_news.stock_code}")
        logger.info("")

        # 유사 뉴스 + 주가 변동률 조회
        test_text = f"{sample_news.title}\n{sample_news.content}"
        enriched_news = vector_search.get_news_with_price_changes(
            news_text=test_text,
            stock_code=sample_news.stock_code,
            db=db,
            top_k=3,
            similarity_threshold=0.5,
        )

        if enriched_news:
            logger.info(f"✅ 유사 뉴스 + 주가 변동률 {len(enriched_news)}건 조회 완료")
            for i, news in enumerate(enriched_news, 1):
                logger.info(f"\n{i}. [{news['stock_code']}] {news['news_title'][:40]}...")
                logger.info(f"   유사도: {news['similarity']:.4f}")
                logger.info(f"   발표일: {news['published_at'].strftime('%Y-%m-%d')}")
                logger.info(f"   주가 변동률:")
                logger.info(f"      T+1일: {news['price_changes']['1d']}%")
                logger.info(f"      T+3일: {news['price_changes']['3d']}%")
                logger.info(f"      T+5일: {news['price_changes']['5d']}%")
        else:
            logger.warning("⚠️  유사 뉴스를 찾지 못했습니다")

        logger.info("")
        return len(enriched_news) > 0

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 벡터 검색 시스템 테스트 시작")
    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. 기본 유사 뉴스 검색
    tests_total += 1
    if test_search_similar_news():
        tests_passed += 1

    # 2. 종목 필터링 검색
    tests_total += 1
    if test_search_with_stock_filter():
        tests_passed += 1

    # 3. 유사 뉴스 + 주가 변동률
    tests_total += 1
    if test_get_news_with_price_changes():
        tests_passed += 1

    # 결과 출력
    logger.info("=" * 60)
    logger.info(f"✅ 테스트 결과: {tests_passed}/{tests_total}개 통과")
    logger.info("=" * 60)

    if tests_passed == tests_total:
        logger.info("🎉 모든 테스트 통과!")
        sys.exit(0)
    else:
        logger.error(f"❌ {tests_total - tests_passed}개 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
