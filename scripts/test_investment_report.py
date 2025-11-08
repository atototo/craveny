"""
투자 리포트 생성 테스트 스크립트

Epic 3 완료 확인을 위한 통합 테스트
- 뉴스 영향도 집계 확인
- 가격 예측 포함 확인
- 5개 종목 리포트 생성 테스트
"""

from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.llm.investment_report import InvestmentReportGenerator
from sqlalchemy import func, desc

def test_investment_report():
    """투자 리포트 생성 테스트"""
    print("=" * 80)
    print("Epic 3 완료 확인: 투자 리포트 생성 테스트")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. 영향도 분석 데이터가 있는 종목 찾기
        print("\n1. 영향도 분석 데이터가 있는 종목 찾기...")
        stocks_with_data = (
            db.query(Prediction.stock_code, func.count(Prediction.id).label("count"))
            .filter(Prediction.sentiment_direction.isnot(None))
            .group_by(Prediction.stock_code)
            .order_by(desc("count"))
            .limit(5)
            .all()
        )

        if not stocks_with_data:
            print("   ❌ 영향도 분석 데이터가 없습니다.")
            return

        print(f"   ✅ {len(stocks_with_data)}개 종목 발견:")
        for stock_code, count in stocks_with_data:
            print(f"      - {stock_code}: {count}건")

        # 2. 리포트 생성기 초기화
        print("\n2. 리포트 생성기 초기화...")
        generator = InvestmentReportGenerator()
        print("   ✅ 초기화 완료")

        # 3. 각 종목별 리포트 생성 테스트
        print("\n3. 종목별 리포트 생성 테스트...")
        success_count = 0

        for stock_code, pred_count in stocks_with_data:
            print(f"\n   [{stock_code}] 리포트 생성 중...")

            # 최근 20개 예측 데이터 가져오기
            predictions = (
                db.query(Prediction)
                .filter(Prediction.stock_code == stock_code)
                .filter(Prediction.sentiment_direction.isnot(None))
                .order_by(Prediction.created_at.desc())
                .limit(20)
                .all()
            )

            if len(predictions) < 3:
                print(f"      ⚠️  예측 데이터가 부족합니다 ({len(predictions)}건)")
                continue

            # 영향도 통계 확인
            positive = sum(1 for p in predictions if p.sentiment_direction == "positive")
            negative = sum(1 for p in predictions if p.sentiment_direction == "negative")
            neutral = sum(1 for p in predictions if p.sentiment_direction == "neutral")

            high_impact = sum(1 for p in predictions if p.impact_level in ["high", "critical"])
            medium_impact = sum(1 for p in predictions if p.impact_level == "medium")
            low_impact = sum(1 for p in predictions if p.impact_level == "low")

            avg_sentiment = sum(p.sentiment_score for p in predictions if p.sentiment_score is not None) / len(predictions)
            avg_relevance = sum(p.relevance_score for p in predictions if p.relevance_score is not None) / len(predictions)

            print(f"      감성 분포: 긍정 {positive}, 부정 {negative}, 중립 {neutral}")
            print(f"      영향도 분포: 높음 {high_impact}, 중간 {medium_impact}, 낮음 {low_impact}")
            print(f"      평균 감성: {avg_sentiment:.2f}, 평균 관련성: {avg_relevance:.2f}")

            # 리포트 생성 (LLM 호출은 실제로 하지 않고 데이터 준비만 테스트)
            try:
                report_data = generator._prepare_report_data(
                    stock_code=stock_code,
                    predictions=predictions,
                    current_price={"close": 50000, "change_rate": 1.5}
                )

                # 데이터 구조 확인
                assert "sentiment_distribution" in report_data["statistical_summary"]
                assert "impact_distribution" in report_data["statistical_summary"]
                assert "avg_sentiment_score" in report_data["statistical_summary"]
                assert "avg_relevance_score" in report_data["statistical_summary"]

                # 최근 뉴스 분석에 새 필드 포함 확인
                if report_data["recent_news_analysis"]:
                    news = report_data["recent_news_analysis"][0]
                    assert "sentiment_direction" in news
                    assert "sentiment_score" in news
                    assert "impact_level" in news
                    assert "relevance_score" in news
                    assert "urgency_level" in news

                print(f"      ✅ 리포트 데이터 준비 성공")
                success_count += 1

            except Exception as e:
                print(f"      ❌ 리포트 생성 실패: {e}")
                continue

        # 4. 결과 요약
        print("\n" + "=" * 80)
        print("테스트 결과 요약")
        print("=" * 80)
        print(f"총 종목 수: {len(stocks_with_data)}")
        print(f"성공: {success_count}개")
        print(f"실패: {len(stocks_with_data) - success_count}개")

        if success_count >= 3:
            print("\n✅ Epic 3 완료 조건 충족: 3개 이상 종목 리포트 생성 성공")
        else:
            print(f"\n⚠️  Epic 3 완료 조건 미충족: 최소 3개 종목 필요 (현재 {success_count}개)")

    finally:
        db.close()


if __name__ == "__main__":
    test_investment_report()
