"""
Nov 7 리포트 생성 및 평가 테스트 (SK하이닉스)

Nov 7 과거 리포트를 생성하고, Nov 10 데이터로 ModelEvaluation을 생성합니다.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.services.evaluation_service import EvaluationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_CODE = "000660"  # SK하이닉스
TARGET_DATE = datetime(2025, 11, 7, 15, 30, 0)  # Nov 7, 15:30


async def create_nov7_report():
    """Nov 7 리포트 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"📅 Nov 7 리포트 생성: {STOCK_CODE}")
        print("=" * 80)

        # 리포트 생성
        report = await update_stock_analysis_summary(
            stock_code=STOCK_CODE,
            db=db,
            force_update=True
        )

        if not report:
            print("❌ 리포트 생성 실패")
            return None

        # last_updated를 Nov 7로 변경
        report.last_updated = TARGET_DATE
        db.commit()
        db.refresh(report)

        print(f"✅ 리포트 생성 완료 (ID: {report.id})")
        print(f"   날짜: {report.last_updated}")
        print(f"   기준가: {report.base_price:,.0f}원")
        print(f"   목표가: {report.short_term_target_price:,.0f}원")

        return report

    finally:
        db.close()


def create_evaluations(report_id: int):
    """ModelEvaluation 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"🎯 ModelEvaluation 생성")
        print("=" * 80)

        # 리포트 조회
        report = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.id == report_id
        ).first()

        if not report:
            print(f"❌ 리포트 없음: ID={report_id}")
            return False

        print(f"📊 리포트: {report.stock_code}, {report.last_updated}")

        # EvaluationService
        service = EvaluationService(db)

        success_count = 0
        error_count = 0

        # A/B 테스트 리포트인 경우 두 모델 모두 평가
        if report.custom_data and report.custom_data.get('ab_test_enabled'):
            print(f"\n🔄 A/B 테스트 리포트 평가 중...")

            # DB에서 A/B 설정 가져오기
            from backend.db.models.ab_test_config import ABTestConfig
            from backend.db.models.model import Model

            ab_config = db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first()

            if ab_config:
                model_a = db.query(Model).filter(Model.id == ab_config.model_a_id).first()
                model_b = db.query(Model).filter(Model.id == ab_config.model_b_id).first()

                # Model A
                try:
                    eval_a = service.evaluate_report(report, model_id=ab_config.model_a_id)
                    if eval_a:
                        success_count += 1
                        print(f"  ✅ Model A ({model_a.name}) 평가 완료: score={eval_a.final_score:.1f}")
                        print(f"     목표달성: {eval_a.target_achieved}, 손절이탈: {eval_a.support_breached}")
                    else:
                        error_count += 1
                        print(f"  ❌ Model A 평가 실패")
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Model A 평가 실패: {e}")

                # Model B
                try:
                    eval_b = service.evaluate_report(report, model_id=ab_config.model_b_id)
                    if eval_b:
                        success_count += 1
                        print(f"  ✅ Model B ({model_b.name}) 평가 완료: score={eval_b.final_score:.1f}")
                        print(f"     목표달성: {eval_b.target_achieved}, 손절이탈: {eval_b.support_breached}")
                    else:
                        error_count += 1
                        print(f"  ❌ Model B 평가 실패")
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ Model B 평가 실패: {e}")
            else:
                print("  ⚠️ 활성 A/B 테스트 설정 없음")

        print(f"\n📊 평가 완료: 성공 {success_count}개, 실패 {error_count}개")
        return success_count > 0

    finally:
        db.close()


async def main():
    """메인 실행"""
    print("\n" + "=" * 80)
    print("🚀 Nov 7 리포트 생성 및 평가 테스트")
    print("=" * 80)

    # 1. Nov 7 리포트 생성
    report = await create_nov7_report()
    if not report:
        print("\n❌ 테스트 실패: 리포트 생성 안됨")
        return

    # 2. ModelEvaluation 생성
    success = create_evaluations(report.id)

    # 결과
    print("\n" + "=" * 80)
    print("🎉 테스트 완료")
    print("=" * 80)
    print(f"  리포트 생성:     {'✅' if report else '❌'}")
    print(f"  평가 생성:       {'✅' if success else '❌'}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
