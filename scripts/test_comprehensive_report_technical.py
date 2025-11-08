"""
종합 리포트에 기술적 지표 반영 여부 테스트

Phase C: 종합 리포트 생성 시 RSI, 볼린저 밴드, MACD가 포함되는지 확인
"""
import logging
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.llm.investment_report import get_report_generator
from backend.db.models.stock import StockPrice

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_comprehensive_report_with_technical_indicators():
    """종합 리포트에 기술적 지표가 포함되는지 테스트"""
    print("=" * 80)
    print("🔬 종합 리포트 기술적 지표 반영 테스트")
    print("=" * 80)

    db = SessionLocal()
    generator = get_report_generator()

    try:
        # SK하이닉스 종목 코드
        stock_code = "000660"

        # 최근 예측 데이터 조회 (최대 20건)
        predictions = (
            db.query(Prediction)
            .filter(Prediction.stock_code == stock_code)
            .order_by(Prediction.created_at.desc())
            .limit(20)
            .all()
        )

        if not predictions:
            logger.error(f"❌ 종목 {stock_code}에 대한 예측 데이터가 없습니다")
            return

        logger.info(f"✅ {len(predictions)}개의 예측 데이터 발견")

        # 현재가 정보 조회
        current_price_obj = (
            db.query(StockPrice)
            .filter(StockPrice.stock_code == stock_code)
            .order_by(StockPrice.date.desc())
            .first()
        )

        current_price = None
        if current_price_obj:
            # 전일 대비 변동률 계산
            previous_price_obj = (
                db.query(StockPrice)
                .filter(
                    StockPrice.stock_code == stock_code,
                    StockPrice.date < current_price_obj.date
                )
                .order_by(StockPrice.date.desc())
                .first()
            )

            change_rate = 0.0
            if previous_price_obj and previous_price_obj.close > 0:
                change_rate = ((current_price_obj.close - previous_price_obj.close) / previous_price_obj.close) * 100

            current_price = {
                "close": current_price_obj.close,
                "change_rate": round(change_rate, 2),
            }

        # 종합 리포트 생성 (단일 모델)
        logger.info(f"\n🔄 종합 리포트 생성 중...")

        # A/B 테스트가 비활성화되어 있다고 가정하고 단일 모델 리포트 생성
        from backend.config import settings
        if settings.AB_TEST_ENABLED:
            logger.info("📊 A/B 테스트 모드 활성화 - 두 모델로 리포트 생성")
            report = generator.dual_generate_report(stock_code, predictions, current_price)

            print("\n" + "=" * 80)
            print("✅ A/B 종합 리포트 생성 완료!")
            print("=" * 80)

            # Model A 리포트
            model_a = report.get("model_a", {})
            print(f"\n📊 Model A ({model_a.get('provider', 'N/A')} / {model_a.get('model', 'N/A')}):")
            print(f"   종합 요약: {model_a.get('overall_summary', 'N/A')[:100]}...")
            print(f"   최종 추천: {model_a.get('recommendation', 'N/A')[:80]}...")

            # Model B 리포트
            model_b = report.get("model_b", {})
            print(f"\n📊 Model B ({model_b.get('provider', 'N/A')} / {model_b.get('model', 'N/A')}):")
            print(f"   종합 요약: {model_b.get('overall_summary', 'N/A')[:100]}...")
            print(f"   최종 추천: {model_b.get('recommendation', 'N/A')[:80]}...")

            # 비교 결과
            comparison = report.get("comparison", {})
            print(f"\n📈 비교 결과:")
            print(f"   추천 일치 여부: {comparison.get('recommendation_match', False)}")

        else:
            logger.info("📊 단일 모델 리포트 생성")
            report = generator.generate_report(stock_code, predictions, current_price)

            print("\n" + "=" * 80)
            print("✅ 종합 리포트 생성 완료!")
            print("=" * 80)
            print(f"📊 종합 요약: {report.get('overall_summary', 'N/A')[:150]}...")
            print(f"📈 단기 시나리오: {report.get('short_term_scenario', 'N/A')[:100]}...")
            print(f"📅 중기 시나리오: {report.get('medium_term_scenario', 'N/A')[:100]}...")
            print(f"🎯 최종 추천: {report.get('recommendation', 'N/A')[:100]}...")

        # 프롬프트 생성하여 기술적 지표 포함 여부 확인
        print("\n" + "=" * 80)
        print("🔍 프롬프트에 기술적 지표 포함 확인")
        print("=" * 80)

        # _prepare_report_data를 직접 호출하여 데이터 확인
        report_data = generator._prepare_report_data(stock_code, predictions, current_price)

        # 기술적 지표가 포함되어 있는지 확인
        if "technical_indicators" in report_data:
            technical = report_data["technical_indicators"]
            print("✅ 기술적 지표가 report_data에 포함되어 있습니다!")

            # 각 지표 확인
            indicators_found = []
            if technical.get("moving_averages"):
                indicators_found.append("이동평균선 (MA5, MA20, MA60)")
            if technical.get("volume_analysis"):
                indicators_found.append("거래량 분석")
            if technical.get("rsi"):
                indicators_found.append(f"RSI ({technical['rsi'].get('value', 'N/A'):.1f})")
            if technical.get("bollinger_bands"):
                indicators_found.append("볼린저 밴드")
            if technical.get("macd"):
                indicators_found.append(f"MACD ({technical['macd'].get('signal_type', 'N/A')})")
            if technical.get("price_momentum"):
                indicators_found.append("가격 모멘텀")

            print(f"\n발견된 지표 ({len(indicators_found)}개):")
            for indicator in indicators_found:
                print(f"  ✓ {indicator}")

            # 프롬프트 생성
            prompt = generator._build_prompt(report_data)

            # 프롬프트에 기술적 지표 섹션이 포함되어 있는지 확인
            keywords = ["RSI", "볼린저 밴드", "MACD", "이동평균선", "거래량", "모멘텀"]
            found_keywords = [kw for kw in keywords if kw in prompt]

            print(f"\n✅ 프롬프트에서 발견된 키워드 ({len(found_keywords)}/{len(keywords)}개):")
            for kw in found_keywords:
                print(f"  ✓ {kw}")

            if len(found_keywords) == len(keywords):
                print("\n🎉 모든 기술적 지표가 종합 리포트 프롬프트에 포함되었습니다!")
            else:
                missing = set(keywords) - set(found_keywords)
                print(f"\n⚠️ 누락된 키워드: {', '.join(missing)}")

        else:
            print("❌ 기술적 지표가 report_data에 포함되지 않았습니다!")

        print("\n" + "=" * 80)
        print("✅ 테스트 완료!")
        print("=" * 80)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_comprehensive_report_with_technical_indicators()
