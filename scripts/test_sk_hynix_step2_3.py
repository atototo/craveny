"""
SK하이닉스(000660) Step 2-3 실행

Step 2: StockAnalysisSummary 생성
Step 3: ModelEvaluation 생성
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from backend.db.session import SessionLocal
from backend.db.models.model import Model
from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.model_evaluation import ModelEvaluation
from backend.services.stock_analysis_service import update_stock_analysis_summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_CODE = "000660"  # SK하이닉스
STOCK_NAME = "SK하이닉스"


async def step2_create_summary():
    """Step 2: StockAnalysisSummary 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"2️⃣  {STOCK_NAME} StockAnalysisSummary 생성 시작")
        print("=" * 80)

        # Prediction 개수 확인
        pred_count = db.query(Prediction).filter(
            Prediction.stock_code == STOCK_CODE
        ).count()

        print(f"📊 기존 Prediction: {pred_count}개")

        if pred_count == 0:
            print("⚠️  Prediction이 없어서 Summary를 생성할 수 없습니다.")
            return False

        # 리포트 생성 (모든 활성 모델에 대해 생성됨)
        print(f"\n🔄 리포트 생성 중...")
        report = await update_stock_analysis_summary(
            stock_code=STOCK_CODE,
            db=db,
            force_update=True
        )

        if report:
            print(f"✅ StockAnalysisSummary 생성 성공 (ID: {report.id})")
            print(f"   총 예측 건수: {report.total_predictions}개")
            print(f"   상승: {report.up_count}, 하락: {report.down_count}, 보합: {report.hold_count}")
            if report.base_price and report.short_term_target_price:
                print(f"   기준가: {report.base_price:,.0f}원, 목표가: {report.short_term_target_price:,.0f}원")
            return True
        else:
            print("❌ StockAnalysisSummary 생성 실패")
            return False

    finally:
        db.close()


def step3_create_evaluation():
    """Step 3: ModelEvaluation 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"3️⃣  {STOCK_NAME} ModelEvaluation 생성 시작")
        print("=" * 80)

        # StockAnalysisSummary 확인
        summary = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.stock_code == STOCK_CODE
        ).first()

        if not summary:
            print("⚠️  StockAnalysisSummary가 없어서 Evaluation을 생성할 수 없습니다.")
            return False

        print(f"📊 StockAnalysisSummary: ID={summary.id}, 예측건수={summary.based_on_prediction_count}")

        # EvaluationService 사용
        from backend.services.evaluation_service import EvaluationService
        service = EvaluationService(db)

        success_count = 0
        error_count = 0

        # A/B 테스트 리포트인 경우 두 모델 모두 평가
        if summary.custom_data and summary.custom_data.get('ab_test_enabled'):
            print(f"\n🔄 A/B 테스트 리포트 평가 중...")

            # Model A 평가 (GPT-4o, ID=1)
            try:
                evaluation_a = service.evaluate_report(summary, model_id=1)
                if evaluation_a:
                    success_count += 1
                    print(f"  ✅ Model A (GPT-4o, ID=1) 평가 완료: score={evaluation_a.final_score:.1f}")
                else:
                    error_count += 1
                    print(f"  ❌ Model A 평가 실패")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Model A 평가 실패: {e}")

            # Model B 평가 (DeepSeek V3.2, ID=5)
            try:
                evaluation_b = service.evaluate_report(summary, model_id=5)
                if evaluation_b:
                    success_count += 1
                    print(f"  ✅ Model B (DeepSeek V3.2, ID=5) 평가 완료: score={evaluation_b.final_score:.1f}")
                else:
                    error_count += 1
                    print(f"  ❌ Model B 평가 실패")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Model B 평가 실패: {e}")
        else:
            # 일반 리포트는 기본 모델로 평가 (ID=1)
            try:
                evaluation = service.evaluate_report(summary, model_id=1)
                if evaluation:
                    success_count += 1
                    print(f"  ✅ 평가 완료: score={evaluation.final_score:.1f}")
                else:
                    error_count += 1
                    print(f"  ❌ 평가 실패")
            except Exception as e:
                error_count += 1
                print(f"  ❌ 평가 실패: {e}")

        print(f"\n📊 ModelEvaluation 생성 완료:")
        print(f"   성공: {success_count}개")
        print(f"   실패: {error_count}개")

        return success_count > 0

    finally:
        db.close()


async def main():
    """메인 실행 함수"""
    print("\n" + "=" * 80)
    print(f"🚀 {STOCK_NAME} Step 2-3 실행")
    print("=" * 80)
    print("실행 단계:")
    print("  2️⃣  StockAnalysisSummary 생성")
    print("  3️⃣  ModelEvaluation 생성")
    print("=" * 80)

    # 2. Summary 생성
    step2_success = await step2_create_summary()
    if not step2_success:
        print("\n❌ Step 2 실패로 중단합니다.")
        return

    # 3. Evaluation 생성
    step3_success = step3_create_evaluation()

    # 최종 결과
    print("\n" + "=" * 80)
    print("🎉 Step 2-3 실행 완료")
    print("=" * 80)
    print(f"  Step 2 (Summary):             {'✅' if step2_success else '❌'}")
    print(f"  Step 3 (Evaluation):          {'✅' if step3_success else '❌'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
