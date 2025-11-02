"""
예측 API 테스트 스크립트

FastAPI 예측 엔드포인트를 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import httpx
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# API 베이스 URL
BASE_URL = "http://localhost:8000"


def test_predict_api():
    """예측 API 테스트"""
    logger.info("=" * 70)
    logger.info("📡 /api/predict POST 테스트")
    logger.info("=" * 70)

    try:
        # 요청 데이터
        request_data = {
            "news_id": 1,
            "stock_code": "005930",
            "top_k": 5,
            "similarity_threshold": 0.5,
            "use_cache": True,
        }

        logger.info(f"📤 요청 데이터:")
        logger.info(json.dumps(request_data, indent=2, ensure_ascii=False))
        logger.info("")

        # API 호출
        logger.info("🚀 API 호출 중...")
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{BASE_URL}/api/predict",
                json=request_data,
            )

        logger.info(f"📥 응답 상태: {response.status_code}")
        logger.info("")

        if response.status_code == 200:
            result = response.json()

            logger.info("=" * 70)
            logger.info("✅ 예측 결과")
            logger.info("=" * 70)
            logger.info(f"예측 방향: {result['prediction']}")
            logger.info(f"신뢰도: {result['confidence']}%")
            logger.info(f"\n근거:")
            logger.info(f"{result['reasoning']}")
            logger.info(f"\n기간별 예측:")
            logger.info(f"  - 단기 (T+1일): {result['short_term']}")
            logger.info(f"  - 중기 (T+3일): {result['medium_term']}")
            logger.info(f"  - 장기 (T+5일): {result['long_term']}")
            logger.info(f"\n유사 뉴스: {len(result['similar_news'])}건")

            for i, news in enumerate(result["similar_news"][:3], 1):
                logger.info(f"  {i}. {news['title'][:40]}...")
                logger.info(f"     유사도: {news['similarity']:.2%}")
                logger.info(
                    f"     주가: T+1일 {news['price_changes']['day1']}%, "
                    f"T+3일 {news['price_changes']['day3']}%, "
                    f"T+5일 {news['price_changes']['day5']}%"
                )

            logger.info(f"\n메타 정보:")
            logger.info(f"  - 캐시 사용: {result['cached']}")
            logger.info(f"  - 사용 모델: {result['model']}")
            logger.info(f"  - 예측 시각: {result['timestamp']}")
            logger.info("")

            return True
        else:
            logger.error(f"❌ API 실패: {response.status_code}")
            logger.error(f"응답: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ API 테스트 실패: {e}", exc_info=True)
        return False


def test_predict_api_cached():
    """캐시 히트 테스트 (동일 요청 재전송)"""
    logger.info("=" * 70)
    logger.info("🔄 캐시 히트 테스트")
    logger.info("=" * 70)

    try:
        request_data = {
            "news_id": 1,
            "stock_code": "005930",
            "top_k": 5,
            "similarity_threshold": 0.5,
            "use_cache": True,
        }

        logger.info("🚀 2차 API 호출 (캐시 히트 예상)...")

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{BASE_URL}/api/predict",
                json=request_data,
            )

        if response.status_code == 200:
            result = response.json()

            if result["cached"]:
                logger.info("✅ 캐시 히트: 결과가 캐시에서 반환됨")
            else:
                logger.warning("⚠️  캐시 미스: LLM이 다시 호출됨")

            logger.info(f"예측: {result['prediction']} (신뢰도: {result['confidence']}%)")
            logger.info("")

            return True
        else:
            logger.error(f"❌ API 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ 캐시 테스트 실패: {e}", exc_info=True)
        return False


def test_cache_stats_api():
    """캐시 통계 API 테스트"""
    logger.info("=" * 70)
    logger.info("📊 /api/predict/cache/stats GET 테스트")
    logger.info("=" * 70)

    try:
        logger.info("🚀 API 호출 중...")

        with httpx.Client() as client:
            response = client.get(f"{BASE_URL}/api/predict/cache/stats")

        logger.info(f"📥 응답 상태: {response.status_code}")
        logger.info("")

        if response.status_code == 200:
            result = response.json()

            logger.info("=" * 70)
            logger.info("📊 캐시 통계")
            logger.info("=" * 70)
            logger.info(f"캐시 히트: {result['stats']['hits']}건")
            logger.info(f"캐시 미스: {result['stats']['misses']}건")
            logger.info(f"캐시 저장: {result['stats']['sets']}건")
            logger.info(f"캐시 삭제: {result['stats']['deletes']}건")
            logger.info(f"오류: {result['stats']['errors']}건")
            logger.info(f"히트율: {result['hit_rate_percent']}")
            logger.info("")

            return True
        else:
            logger.error(f"❌ API 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ 통계 API 테스트 실패: {e}", exc_info=True)
        return False


def test_health_api():
    """헬스 체크 API 테스트 (서버 준비 확인)"""
    logger.info("🏥 서버 상태 확인 중...")

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{BASE_URL}/health/liveness")

        if response.status_code == 200:
            logger.info("✅ 서버 준비 완료")
            return True
        else:
            logger.error(f"❌ 서버 미준비: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ 서버 연결 실패: {e}")
        return False


def main():
    """메인 실행 함수"""
    logger.info("🚀 예측 API 테스트 시작")
    logger.info("")

    # 서버 준비 확인
    if not test_health_api():
        logger.error("❌ 서버가 준비되지 않았습니다. 서버를 먼저 시작하세요.")
        sys.exit(1)

    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. 예측 API (캐시 미스)
    tests_total += 1
    if test_predict_api():
        tests_passed += 1

    # 2. 예측 API (캐시 히트)
    tests_total += 1
    if test_predict_api_cached():
        tests_passed += 1

    # 3. 캐시 통계 API
    tests_total += 1
    if test_cache_stats_api():
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
