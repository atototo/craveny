"""
주가 예측 테스트 스크립트

유사 뉴스 검색 → LLM 예측 → 결과 출력
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from backend.llm.vector_search import NewsVectorSearch
from backend.llm.predictor import StockPredictor
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_prediction_with_similar_news():
    """유사 뉴스 기반 예측 테스트"""
    logger.info("=" * 70)
    logger.info("📊 유사 뉴스 기반 주가 예측 테스트")
    logger.info("=" * 70)

    db = SessionLocal()
    vector_search = NewsVectorSearch()
    predictor = StockPredictor()

    try:
        # 1. 테스트용 뉴스 가져오기
        sample_news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .first()
        )

        if not sample_news:
            logger.warning("⚠️  테스트할 뉴스가 없습니다")
            return False

        logger.info(f"\n📰 현재 뉴스:")
        logger.info(f"   제목: {sample_news.title[:60]}...")
        logger.info(f"   종목: {sample_news.stock_code}")
        logger.info(f"   발표일: {sample_news.published_at}")
        logger.info("")

        # 2. 유사 뉴스 검색
        logger.info("🔍 유사 뉴스 검색 중...")
        test_text = f"{sample_news.title}\n{sample_news.content}"
        similar_news = vector_search.get_news_with_price_changes(
            news_text=test_text,
            stock_code=sample_news.stock_code,
            db=db,
            top_k=5,
            similarity_threshold=0.5,
        )

        logger.info(f"✅ 유사 뉴스 {len(similar_news)}건 발견")
        for i, news in enumerate(similar_news[:3], 1):  # 상위 3건만 출력
            logger.info(f"\n   {i}. {news['news_title'][:50]}...")
            logger.info(f"      유사도: {news['similarity']:.2%}")
            logger.info(
                f"      주가 변동: T+1일 {news['price_changes']['1d']}%, "
                f"T+3일 {news['price_changes']['3d']}%, "
                f"T+5일 {news['price_changes']['5d']}%"
            )

        logger.info("")

        # 3. 주가 예측
        logger.info("🤖 LLM 주가 예측 중...")
        current_news_data = {
            "title": sample_news.title,
            "content": sample_news.content,
            "stock_code": sample_news.stock_code,
        }

        prediction = predictor.predict(
            current_news=current_news_data,
            similar_news=similar_news,
        )

        # 4. 결과 출력
        logger.info("")
        logger.info("=" * 70)
        logger.info("📈 예측 결과")
        logger.info("=" * 70)
        logger.info(f"예측 방향: {prediction['prediction']}")
        logger.info(f"신뢰도: {prediction['confidence']}%")
        logger.info(f"\n근거:")
        logger.info(f"{prediction['reasoning']}")
        logger.info(f"\n기간별 예측:")
        logger.info(f"  - 단기 (T+1일): {prediction['short_term']}")
        logger.info(f"  - 중기 (T+3일): {prediction['medium_term']}")
        logger.info(f"  - 장기 (T+5일): {prediction['long_term']}")
        logger.info(f"\n메타 정보:")
        logger.info(f"  - 참고 뉴스: {prediction['similar_count']}건")
        logger.info(f"  - 사용 모델: {prediction['model']}")
        logger.info(f"  - 예측 시각: {prediction['timestamp']}")
        logger.info("")

        # JSON 저장 (선택)
        output_file = project_root / "test_prediction_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "news": {
                        "title": sample_news.title,
                        "stock_code": sample_news.stock_code,
                        "published_at": sample_news.published_at.isoformat()
                        if sample_news.published_at
                        else None,
                    },
                    "similar_news_count": len(similar_news),
                    "prediction": prediction,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.info(f"💾 결과 저장: {output_file}")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ 예측 테스트 실패: {e}", exc_info=True)
        return False

    finally:
        db.close()


def test_prediction_without_similar_news():
    """유사 뉴스 없이 예측 테스트 (뉴스 내용만으로 예측)"""
    logger.info("=" * 70)
    logger.info("📊 뉴스 내용만으로 주가 예측 테스트")
    logger.info("=" * 70)

    predictor = StockPredictor()

    try:
        # 새로운 가상 뉴스 (유사 뉴스 없음)
        test_news = {
            "title": "삼성전자, 차세대 AI 칩 개발 성공",
            "content": "삼성전자가 차세대 인공지능(AI) 반도체 개발에 성공했다. "
            "새로운 칩은 기존 대비 성능이 3배 향상되었으며, "
            "전력 소비는 40% 감소했다. 업계에서는 이번 개발로 "
            "삼성전자가 AI 반도체 시장에서 경쟁력을 크게 높일 것으로 전망하고 있다.",
            "stock_code": "005930",
        }

        logger.info(f"\n📰 테스트 뉴스:")
        logger.info(f"   제목: {test_news['title']}")
        logger.info(f"   종목: {test_news['stock_code']}")
        logger.info("")

        # 유사 뉴스 없이 예측
        logger.info("🤖 LLM 주가 예측 중 (유사 뉴스 없음)...")
        prediction = predictor.predict(
            current_news=test_news,
            similar_news=[],  # 빈 리스트
        )

        # 결과 출력
        logger.info("")
        logger.info("=" * 70)
        logger.info("📈 예측 결과")
        logger.info("=" * 70)
        logger.info(f"예측 방향: {prediction['prediction']}")
        logger.info(f"신뢰도: {prediction['confidence']}%")
        logger.info(f"\n근거:")
        logger.info(f"{prediction['reasoning']}")
        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ 예측 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """메인 실행 함수"""
    logger.info("🚀 주가 예측 시스템 테스트 시작")
    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. 유사 뉴스 기반 예측
    tests_total += 1
    if test_prediction_with_similar_news():
        tests_passed += 1

    # 2. 뉴스 내용만으로 예측
    tests_total += 1
    if test_prediction_without_similar_news():
        tests_passed += 1

    # 결과 출력
    logger.info("=" * 70)
    logger.info(f"✅ 테스트 결과: {tests_passed}/{tests_total}개 통과")
    logger.info("=" * 70)

    if tests_passed == tests_total:
        logger.info("🎉 모든 테스트 통과!")
        sys.exit(0)
    else:
        logger.error(f"❌ {tests_total - tests_passed}개 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
