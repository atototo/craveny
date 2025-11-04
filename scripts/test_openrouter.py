"""
OpenRouter DeepSeek 모델 테스트 스크립트

OpenRouter API가 정상적으로 작동하는지 검증합니다.
- API 키 유효성
- 모델 응답 확인
- JSON 모드 호환성
- 비용 계산
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.llm.predictor import StockPredictor
from backend.config import settings


def test_openrouter_prediction():
    """OpenRouter DeepSeek 모델로 간단한 예측 테스트"""

    print("=" * 80)
    print("OpenRouter DeepSeek 모델 테스트")
    print("=" * 80)

    # 1. 설정 확인
    print(f"\n[1] 설정 확인")
    print(f"  - LLM Provider: {settings.LLM_PROVIDER}")
    print(f"  - Model: {settings.OPENROUTER_MODEL}")
    print(f"  - API Key: {settings.OPENROUTER_API_KEY[:20]}..." if settings.OPENROUTER_API_KEY else "  - API Key: NOT SET")

    if settings.LLM_PROVIDER != "openrouter":
        print("\n❌ LLM_PROVIDER가 'openrouter'가 아닙니다!")
        print(f"   현재 값: {settings.LLM_PROVIDER}")
        return False

    if not settings.OPENROUTER_API_KEY:
        print("\n❌ OPENROUTER_API_KEY가 설정되지 않았습니다!")
        return False

    print("  ✅ 설정 정상")

    # 2. Predictor 초기화
    print(f"\n[2] StockPredictor 초기화")
    try:
        predictor = StockPredictor()
        print(f"  ✅ 초기화 성공")
        print(f"  - 사용 모델: {predictor.model}")
    except Exception as e:
        print(f"  ❌ 초기화 실패: {e}")
        return False

    # 3. 테스트 뉴스로 예측 수행
    print(f"\n[3] 테스트 예측 수행")

    test_news = {
        "title": "삼성전자, AI 반도체 수주 확대...글로벌 점유율 1위 전망",
        "content": "삼성전자가 인공지능(AI) 반도체 분야에서 대규모 수주에 성공하며 글로벌 시장 점유율 1위를 달성할 것으로 전망된다. 업계에 따르면 삼성전자는 최근 주요 글로벌 빅테크 기업들로부터 차세대 AI 가속기 칩 공급 계약을 체결했다.",
        "stock_code": "005930"
    }

    similar_news = [
        {
            "news_title": "삼성전자, 신규 반도체 공장 착공...3나노 양산 본격화",
            "news_content": "삼성전자가 경기도 평택에 신규 반도체 공장 착공식을 가졌다. 3나노 공정 기반의 차세대 반도체를 양산할 예정이다.",
            "similarity": 0.85,
            "published_at": "2024-01-15",
            "price_changes": {
                "1d": 2.5,
                "2d": 3.8,
                "3d": 5.2,
                "5d": 7.8,
                "10d": 12.5,
                "20d": 18.3
            }
        },
        {
            "news_title": "삼성전자 HBM3 반도체, 엔비디아 공급 승인",
            "news_content": "삼성전자의 고대역폭메모리(HBM3) 반도체가 엔비디아의 품질 검증을 통과했다.",
            "similarity": 0.78,
            "published_at": "2024-02-10",
            "price_changes": {
                "1d": 3.2,
                "2d": 4.5,
                "3d": 6.1,
                "5d": 8.9,
                "10d": 11.2,
                "20d": 15.7
            }
        }
    ]

    try:
        print("  - 예측 요청 중...")
        result = predictor.predict(
            current_news=test_news,
            similar_news=similar_news,
            use_cache=False  # 캐시 비활성화하여 실제 API 호출
        )

        print(f"\n  ✅ 예측 성공!")
        print(f"\n  📊 예측 결과:")
        print(f"    - 예측: {result.get('prediction')}")
        print(f"    - 신뢰도: {result.get('confidence')}%")
        print(f"    - 모델: {result.get('model')}")
        print(f"    - 단기 예측: {result.get('short_term')}")
        print(f"    - 중기 예측: {result.get('medium_term')}")
        print(f"    - 장기 예측: {result.get('long_term')}")
        print(f"\n  💡 예측 근거:")
        reasoning = result.get('reasoning', '').replace('\n', '\n      ')
        print(f"    {reasoning[:300]}...")

        # 신뢰도 breakdown 확인
        if 'confidence_breakdown' in result:
            breakdown = result['confidence_breakdown']
            print(f"\n  🔍 신뢰도 상세:")
            print(f"    - 유사뉴스 품질: {breakdown.get('similar_news_quality')}점")
            print(f"    - 패턴 일관성: {breakdown.get('pattern_consistency')}점")
            print(f"    - 공시 영향: {breakdown.get('disclosure_impact')}점")

        # 비용 계산 (대략적)
        print(f"\n  💰 예상 비용:")
        print(f"    - DeepSeek V3.2 Exp: $0.27/M input, $0.40/M output")
        print(f"    - 이 요청: ~$0.001 (약 1,500 input + 500 output tokens)")
        print(f"    - 1,000회 예측: ~$1.21")
        print(f"    - $20 예산: ~16,500회 예측 가능")

        return True

    except Exception as e:
        print(f"\n  ❌ 예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_openrouter_prediction()

    print("\n" + "=" * 80)
    if success:
        print("✅ OpenRouter DeepSeek 모델 테스트 성공!")
        print("\n다음 단계:")
        print("  1. 실제 뉴스로 여러 번 테스트하여 응답 품질 확인")
        print("  2. 비용 모니터링 (OpenRouter 대시보드)")
        print("  3. 필요시 예산 증액 또는 주요 종목 필터링 추가")
    else:
        print("❌ OpenRouter DeepSeek 모델 테스트 실패")
        print("\n문제 해결:")
        print("  1. .env 파일에서 OPENROUTER_API_KEY 확인")
        print("  2. LLM_PROVIDER=openrouter 설정 확인")
        print("  3. 인터넷 연결 확인")
        print("  4. OpenRouter API 키 유효성 확인 (https://openrouter.ai)")
    print("=" * 80)

    sys.exit(0 if success else 1)
