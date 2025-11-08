"""
기술적 지표 계산 및 프롬프트 통합 테스트

Phase 1: 이동평균 & 거래량 분석 테스트
"""
import logging
from backend.db.session import SessionLocal
from backend.llm.predictor import StockPredictor

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_technical_indicators():
    """기술적 지표 계산 테스트"""
    print("=" * 80)
    print("📊 기술적 지표 계산 테스트")
    print("=" * 80)

    db = SessionLocal()
    predictor = StockPredictor()

    try:
        # 삼성전자 (005930) 테스트
        stock_code = "005930"
        logger.info(f"\n🔍 종목 코드: {stock_code} (삼성전자)")

        # 기술적 지표 계산
        technical = predictor._get_technical_indicators(stock_code)

        if not technical:
            logger.warning("⚠️ 기술적 지표 데이터 없음")
            return

        # 결과 출력
        print("\n✅ 기술적 지표 계산 성공!")
        print("\n" + "=" * 80)
        print("📈 이동평균선 분석")
        print("=" * 80)

        ma = technical["moving_averages"]
        print(f"MA5 (5일):   {ma['ma5']:>10,.0f}원  (현재가 대비 {ma['current_vs_ma5']:>+7.2f}%)")
        print(f"MA20 (20일): {ma['ma20']:>10,.0f}원  (현재가 대비 {ma['current_vs_ma20']:>+7.2f}%)")
        print(f"MA60 (60일): {ma['ma60']:>10,.0f}원  (현재가 대비 {ma['current_vs_ma60']:>+7.2f}%)")
        print(f"추세 판단: {ma['trend']}")

        print("\n" + "=" * 80)
        print("🔥 거래량 분석")
        print("=" * 80)

        vol = technical["volume_analysis"]
        print(f"오늘 거래량:     {vol['current_volume']:>15,}주")
        print(f"20일 평균 거래량: {vol['avg_volume_20d']:>15,.0f}주")
        print(f"거래량 비율:     {vol['volume_ratio']:>+14.2f}%")
        print(f"추세 판단: {vol['trend']}")

        print("\n" + "=" * 80)
        print("🚀 가격 모멘텀")
        print("=" * 80)

        mom = technical["price_momentum"]
        print(f"1일 수익률:  {mom['change_1d']:>+7.2f}%")
        print(f"5일 수익률:  {mom['change_5d']:>+7.2f}%")
        print(f"20일 수익률: {mom['change_20d']:>+7.2f}%")
        print(f"추세 판단: {mom['trend']}")

        print("\n" + "=" * 80)
        print("✅ 기술적 지표 계산 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
    finally:
        db.close()


def test_prompt_integration():
    """프롬프트 통합 테스트"""
    print("\n\n" + "=" * 80)
    print("📝 프롬프트 통합 테스트")
    print("=" * 80)

    predictor = StockPredictor()

    try:
        # 테스트용 현재 뉴스
        current_news = {
            "title": "삼성전자, 3분기 실적 깜짝 발표",
            "content": "삼성전자가 3분기 영업이익이 전년 대비 25% 증가했다고 발표했습니다...",
            "stock_code": "005930"
        }

        # 테스트용 유사 뉴스 (빈 리스트)
        similar_news = []

        # 프롬프트 생성
        logger.info("\n🔄 프롬프트 생성 중...")
        prompt = predictor._build_prompt(current_news, similar_news)

        # 기술적 지표 섹션이 포함되었는지 확인
        if "기술적 지표 분석" in prompt:
            print("\n✅ 기술적 지표 섹션이 프롬프트에 포함됨!")

            # 주요 키워드 확인 (Phase 1 + Phase 2)
            keywords = [
                "이동평균선", "거래량", "모멘텀", "MA5", "MA20", "MA60",
                "RSI", "볼린저 밴드", "MACD"
            ]
            found_keywords = [kw for kw in keywords if kw in prompt]

            print(f"\n✅ 발견된 키워드: {', '.join(found_keywords)}")
            print(f"   총 {len(found_keywords)}/{len(keywords)}개 키워드 발견")

            # 프롬프트 일부 출력 (기술적 지표 섹션만)
            start_idx = prompt.find("## 📈 기술적 지표 분석")
            if start_idx != -1:
                end_idx = prompt.find("---", start_idx)
                technical_section = prompt[start_idx:end_idx] if end_idx != -1 else prompt[start_idx:start_idx+1000]

                print("\n" + "=" * 80)
                print("📄 프롬프트 미리보기 (기술적 지표 섹션)")
                print("=" * 80)
                print(technical_section[:1500])  # 첫 1500자로 확장 (고급 지표 포함)
                if len(technical_section) > 1500:
                    print("...")
                print("=" * 80)
        else:
            print("\n⚠️ 기술적 지표 섹션이 프롬프트에 없음")
            print(f"   프롬프트 길이: {len(prompt)}자")

        print("\n✅ 프롬프트 통합 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ 프롬프트 통합 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    # 1. 기술적 지표 계산 테스트
    test_technical_indicators()

    # 2. 프롬프트 통합 테스트
    test_prompt_integration()

    print("\n\n" + "=" * 80)
    print("🎉 모든 테스트 완료!")
    print("=" * 80)
    print("\n다음 단계:")
    print("  1. 실제 뉴스로 예측 테스트")
    print("  2. 여러 종목으로 테스트")
    print("  3. LLM 응답 품질 확인")
