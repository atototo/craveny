"""
A/B 테스트 검증 스크립트

GPT-4o vs DeepSeek 모델 비교 테스트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.llm.predictor import StockPredictor
from backend.config import settings


def test_ab_comparison():
    """A/B 비교 테스트"""

    print("=" * 80)
    print("A/B 테스트: GPT-4o vs DeepSeek")
    print("=" * 80)

    # 1. A/B 테스트 활성화 확인
    print(f"\n[1] A/B 테스트 설정 확인")
    print(f"  - AB_TEST_ENABLED: {settings.AB_TEST_ENABLED}")
    print(f"  - Model A: {settings.MODEL_A_NAME} ({settings.MODEL_A_PROVIDER})")
    print(f"  - Model B: {settings.MODEL_B_NAME} ({settings.MODEL_B_PROVIDER})")

    if not settings.AB_TEST_ENABLED:
        print("\n❌ A/B 테스트가 비활성화되어 있습니다!")
        print("   .env 파일에서 AB_TEST_ENABLED=true로 설정하세요")
        return False

    print("  ✅ A/B 테스트 활성화됨")

    # 2. Predictor 초기화
    print(f"\n[2] StockPredictor 초기화")
    try:
        predictor = StockPredictor()
        print(f"  ✅ 초기화 성공")
    except Exception as e:
        print(f"  ❌ 초기화 실패: {e}")
        return False

    # 3. 테스트 뉴스로 A/B 예측 수행
    print(f"\n[3] A/B 예측 테스트")

    test_news = {
        "title": "삼성전자, AI 반도체 수주 확대...글로벌 점유율 1위 전망",
        "content": "삼성전자가 인공지능(AI) 반도체 분야에서 대규모 수주에 성공하며 글로벌 시장 점유율 1위를 달성할 것으로 전망된다.",
        "stock_code": "005930"
    }

    similar_news = [
        {
            "news_title": "삼성전자, 신규 반도체 공장 착공",
            "news_content": "삼성전자가 경기도 평택에 신규 반도체 공장 착공식을 가졌다.",
            "similarity": 0.85,
            "published_at": "2024-01-15",
            "price_changes": {"1d": 2.5, "2d": 3.8, "3d": 5.2, "5d": 7.8, "10d": 12.5, "20d": 18.3}
        },
        {
            "news_title": "삼성전자 HBM3 반도체, 엔비디아 공급 승인",
            "news_content": "삼성전자의 고대역폭메모리(HBM3) 반도체가 엔비디아의 품질 검증을 통과했다.",
            "similarity": 0.78,
            "published_at": "2024-02-10",
            "price_changes": {"1d": 3.2, "2d": 4.5, "3d": 6.1, "5d": 8.9, "10d": 11.2, "20d": 15.7}
        }
    ]

    try:
        print("  - A/B 예측 요청 중...")
        result = predictor.dual_predict(
            current_news=test_news,
            similar_news=similar_news,
        )

        print(f"\n  ✅ A/B 예측 성공!")

        # Model A 결과
        model_a = result.get("model_a", {})
        print(f"\n  📊 Model A ({model_a.get('model')})")
        print(f"    - 예측: {model_a.get('prediction')}")
        print(f"    - 신뢰도: {model_a.get('confidence')}%")
        print(f"    - 단기: {model_a.get('short_term')}")
        print(f"    - 중기: {model_a.get('medium_term')}")

        # Model B 결과
        model_b = result.get("model_b", {})
        print(f"\n  📊 Model B ({model_b.get('model')})")
        print(f"    - 예측: {model_b.get('prediction')}")
        print(f"    - 신뢰도: {model_b.get('confidence')}%")
        print(f"    - 단기: {model_b.get('short_term')}")
        print(f"    - 중기: {model_b.get('medium_term')}")

        # 비교 분석
        comparison = result.get("comparison", {})
        print(f"\n  🔍 비교 분석")
        print(f"    - 예측 일치: {'✅ 일치' if comparison.get('agreement') else '⚠️ 불일치'}")
        print(f"    - 신뢰도 차이: {comparison.get('confidence_diff')}%")
        print(f"    - 더 강한 모델: {comparison.get('stronger_model')}")

        # 비용 계산
        print(f"\n  💰 비용 분석")
        print(f"    - GPT-4o 비용: ~$0.015 (1회)")
        print(f"    - DeepSeek 비용: ~$0.001 (1회)")
        print(f"    - 합계: ~$0.016 (A/B 1회)")
        print(f"    - $20 예산: ~1,250회 A/B 테스트 가능")

        return True

    except Exception as e:
        print(f"\n  ❌ A/B 예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_ab_comparison()

    print("\n" + "=" * 80)
    if success:
        print("✅ A/B 테스트 검증 성공!")
        print("\n다음 단계:")
        print("  1. 백엔드 재시작하여 A/B 테스트 활성화")
        print("  2. 실제 뉴스 수집 후 텔레그램 알림 확인")
        print("  3. GPT-4o vs DeepSeek 품질 비교")
    else:
        print("❌ A/B 테스트 검증 실패")
    print("=" * 80)

    sys.exit(0 if success else 1)
