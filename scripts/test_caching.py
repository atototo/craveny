"""
예측 결과 캐싱 테스트 스크립트

Redis 캐싱 기능을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import time
from backend.llm.vector_search import NewsVectorSearch
from backend.llm.predictor import StockPredictor
from backend.llm.prediction_cache import get_prediction_cache
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_cache_hit_miss():
    """캐시 히트/미스 테스트"""
    logger.info("=" * 70)
    logger.info("🔄 캐시 히트/미스 테스트")
    logger.info("=" * 70)

    db = SessionLocal()
    vector_search = NewsVectorSearch()
    predictor = StockPredictor()
    cache = get_prediction_cache()

    try:
        # 캐시 초기화
        cache.clear_all()
        cache.reset_stats()
        logger.info("✅ 캐시 초기화 완료")
        logger.info("")

        # 테스트용 뉴스 가져오기
        sample_news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .first()
        )

        if not sample_news:
            logger.warning("⚠️  테스트할 뉴스가 없습니다")
            return False

        news_id = sample_news.id
        stock_code = sample_news.stock_code

        logger.info(f"📰 테스트 뉴스: ID={news_id}, 종목={stock_code}")
        logger.info(f"   제목: {sample_news.title[:50]}...")
        logger.info("")

        # 유사 뉴스 검색
        test_text = f"{sample_news.title}\n{sample_news.content}"
        similar_news = vector_search.get_news_with_price_changes(
            news_text=test_text,
            stock_code=stock_code,
            db=db,
            top_k=3,
            similarity_threshold=0.5,
        )

        current_news_data = {
            "title": sample_news.title,
            "content": sample_news.content,
            "stock_code": stock_code,
        }

        # --- 1차 예측: 캐시 미스 (LLM 호출) ---
        logger.info("🤖 [1차 예측] 캐시 미스 → LLM 호출")
        start_time = time.time()

        prediction1 = predictor.predict(
            current_news=current_news_data,
            similar_news=similar_news,
            news_id=news_id,
            use_cache=True,
        )

        elapsed1 = time.time() - start_time

        logger.info(f"✅ 예측 완료: {prediction1['prediction']} (신뢰도: {prediction1['confidence']}%)")
        logger.info(f"   캐시 여부: {prediction1.get('cached', False)}")
        logger.info(f"   소요 시간: {elapsed1:.2f}초")
        logger.info("")

        # --- 2차 예측: 캐시 히트 (LLM 호출 없음) ---
        logger.info("🚀 [2차 예측] 캐시 히트 → 즉시 반환")
        start_time = time.time()

        prediction2 = predictor.predict(
            current_news=current_news_data,
            similar_news=similar_news,
            news_id=news_id,
            use_cache=True,
        )

        elapsed2 = time.time() - start_time

        logger.info(f"✅ 예측 완료: {prediction2['prediction']} (신뢰도: {prediction2['confidence']}%)")
        logger.info(f"   캐시 여부: {prediction2.get('cached', False)}")
        logger.info(f"   소요 시간: {elapsed2:.2f}초")
        logger.info(f"   속도 향상: {elapsed1 / elapsed2:.1f}배 빠름")
        logger.info("")

        # 결과 일치 확인
        if (
            prediction1["prediction"] == prediction2["prediction"]
            and prediction1["confidence"] == prediction2["confidence"]
        ):
            logger.info("✅ 1차/2차 예측 결과 일치")
        else:
            logger.warning("⚠️  1차/2차 예측 결과 불일치")

        logger.info("")

        # 캐시 통계
        stats = cache.get_stats()
        hit_rate = cache.get_hit_rate()

        logger.info("=" * 70)
        logger.info("📊 캐시 통계")
        logger.info("=" * 70)
        logger.info(f"캐시 히트: {stats['hits']}건")
        logger.info(f"캐시 미스: {stats['misses']}건")
        logger.info(f"캐시 저장: {stats['sets']}건")
        logger.info(f"캐시 삭제: {stats['deletes']}건")
        logger.info(f"오류: {stats['errors']}건")
        logger.info(f"히트율: {hit_rate:.1%}")
        logger.info("")

        # TTL 확인
        ttl = cache.get_ttl(news_id, stock_code)
        if ttl:
            logger.info(f"⏱️  남은 TTL: {ttl}초 (약 {ttl / 3600:.1f}시간)")
        else:
            logger.warning("⚠️  TTL 조회 실패")

        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ 캐시 테스트 실패: {e}", exc_info=True)
        return False

    finally:
        db.close()


def test_cache_bypass():
    """캐시 우회 테스트 (use_cache=False)"""
    logger.info("=" * 70)
    logger.info("⏭️  캐시 우회 테스트")
    logger.info("=" * 70)

    predictor = StockPredictor()

    try:
        # 가상 뉴스
        test_news = {
            "title": "현대차, 전기차 판매 급증",
            "content": "현대차의 전기차 판매가 전년 대비 50% 증가했다.",
            "stock_code": "005380",
        }

        logger.info("🤖 캐시 우회 모드 (use_cache=False)")

        prediction = predictor.predict(
            current_news=test_news,
            similar_news=[],
            news_id=999,  # 가상 ID
            use_cache=False,  # 캐시 우회
        )

        logger.info(f"✅ 예측 완료: {prediction['prediction']}")
        logger.info(f"   캐시 여부: {prediction.get('cached', False)}")
        logger.info("")

        # 캐시에 저장되지 않았는지 확인
        cache = get_prediction_cache()
        cached = cache.get(999, "005380")

        if cached is None:
            logger.info("✅ 캐시 우회 확인: 결과가 캐시에 저장되지 않음")
        else:
            logger.warning("⚠️  캐시 우회 실패: 결과가 캐시에 저장됨")

        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ 캐시 우회 테스트 실패: {e}", exc_info=True)
        return False


def test_cache_ttl():
    """캐시 TTL 테스트"""
    logger.info("=" * 70)
    logger.info("⏱️  캐시 TTL 테스트")
    logger.info("=" * 70)

    cache = get_prediction_cache()

    try:
        # 짧은 TTL로 캐시 저장
        test_data = {
            "prediction": "상승",
            "confidence": 80,
            "reasoning": "테스트 데이터",
        }

        news_id = 9999
        stock_code = "TEST01"
        ttl = 5  # 5초

        logger.info(f"📝 테스트 데이터 저장 (TTL={ttl}초)")
        cache.set(news_id, stock_code, test_data, ttl=ttl)

        # 즉시 조회
        result1 = cache.get(news_id, stock_code)
        if result1:
            logger.info("✅ 저장 직후 조회 성공")
        else:
            logger.error("❌ 저장 직후 조회 실패")
            return False

        # TTL 경과 전 조회
        time.sleep(2)
        remaining_ttl = cache.get_ttl(news_id, stock_code)
        logger.info(f"⏳ 2초 후 남은 TTL: {remaining_ttl}초")

        # TTL 경과 후 조회
        logger.info(f"⏳ {ttl}초 대기 중...")
        time.sleep(ttl + 1)

        result2 = cache.get(news_id, stock_code)
        if result2 is None:
            logger.info("✅ TTL 만료 후 캐시 자동 삭제 확인")
        else:
            logger.warning("⚠️  TTL 만료 후에도 캐시 존재")

        logger.info("")

        return True

    except Exception as e:
        logger.error(f"❌ TTL 테스트 실패: {e}", exc_info=True)
        return False


def main():
    """메인 실행 함수"""
    logger.info("🚀 예측 캐싱 시스템 테스트 시작")
    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. 캐시 히트/미스
    tests_total += 1
    if test_cache_hit_miss():
        tests_passed += 1

    # 2. 캐시 우회
    tests_total += 1
    if test_cache_bypass():
        tests_passed += 1

    # 3. 캐시 TTL
    tests_total += 1
    if test_cache_ttl():
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
