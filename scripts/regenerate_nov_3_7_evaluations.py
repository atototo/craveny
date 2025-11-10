"""
11월 3-7일 ModelEvaluation 재생성 스크립트

새로 생성된 StockAnalysisSummary를 기준으로 모든 모델의 평가 데이터를 재생성합니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, date
from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_evaluation_for_date(target_date: date):
    """특정 날짜의 평가 실행"""
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 {target_date} 평가 시작")
    logger.info(f"{'='*80}")

    db = SessionLocal()
    try:
        service = EvaluationService(db)

        # 평가 대상 조회 (해당 날짜에 생성된 Investment Report)
        target_datetime = datetime.combine(target_date, datetime.min.time())
        reports = service.get_evaluable_reports(target_datetime)

        if not reports:
            logger.warning(f"⚠️ {target_date}: 평가 대상 없음")
            return 0, 0

        logger.info(f"📊 평가 대상: {len(reports)}개 리포트")

        success_count = 0
        error_count = 0

        for report in reports:
            try:
                # A/B 테스트 리포트인 경우 두 모델 모두 평가
                if report.custom_data and report.custom_data.get('ab_test_enabled'):
                    # Model A 평가
                    model_a_data = report.custom_data.get('model_a', {})
                    model_a_id = None

                    # OpenRouter 모델에서 ID 추출
                    if model_a_data.get('provider') == 'openrouter':
                        # Model A는 ID 2 (Qwen3 Max)
                        model_a_id = 2

                    if model_a_id:
                        try:
                            evaluation_a = service.evaluate_report(report, model_id=model_a_id)
                            if evaluation_a:
                                success_count += 1
                                logger.info(
                                    f"  ✅ Model A (ID={model_a_id}) 평가 완료: {report.stock_code}, "
                                    f"score={evaluation_a.final_score:.1f}"
                                )
                        except Exception as e:
                            error_count += 1
                            logger.error(f"  ❌ Model A 평가 실패: {report.stock_code}, {e}")

                    # Model B 평가
                    model_b_data = report.custom_data.get('model_b', {})
                    model_b_id = None

                    if model_b_data.get('provider') == 'openrouter':
                        # Model B는 ID 5 (DeepSeek V3.2)
                        model_b_id = 5

                    if model_b_id:
                        try:
                            evaluation_b = service.evaluate_report(report, model_id=model_b_id)
                            if evaluation_b:
                                success_count += 1
                                logger.info(
                                    f"  ✅ Model B (ID={model_b_id}) 평가 완료: {report.stock_code}, "
                                    f"score={evaluation_b.final_score:.1f}"
                                )
                        except Exception as e:
                            error_count += 1
                            logger.error(f"  ❌ Model B 평가 실패: {report.stock_code}, {e}")
                else:
                    # 일반 리포트는 기본 모델로 평가 (ID 1)
                    evaluation = service.evaluate_report(report, model_id=1)
                    if evaluation:
                        success_count += 1
                        logger.info(
                            f"  ✅ 평가 완료: {report.stock_code}, "
                            f"score={evaluation.final_score:.1f}"
                        )
                    else:
                        error_count += 1

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 평가 실패: {report.stock_code}, {e}")

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 {target_date} 평가 완료")
        logger.info(f"  성공: {success_count}개, 실패: {error_count}개")
        logger.info(f"{'='*80}\n")

        return success_count, error_count

    except Exception as e:
        logger.error(f"\n❌ 날짜 처리 실패: {target_date}, {e}")
        import traceback
        traceback.print_exc()
        return 0, 0
    finally:
        db.close()


def regenerate_all_evaluations():
    """11월 3-7일 모든 평가 재생성"""
    logger.info("=" * 80)
    logger.info("🔄 11월 3-7일 ModelEvaluation 재생성 시작")
    logger.info("=" * 80)

    # 11월 3-7일
    dates = [
        date(2025, 11, 3),
        date(2025, 11, 4),
        date(2025, 11, 5),
        date(2025, 11, 6),
        date(2025, 11, 7),
    ]

    total_success = 0
    total_error = 0

    for target_date in dates:
        success, error = run_evaluation_for_date(target_date)
        total_success += success
        total_error += error

    logger.info("\n" + "=" * 80)
    logger.info("🎯 전체 재생성 완료 요약")
    logger.info("=" * 80)
    logger.info(f"  총 성공: {total_success}개")
    logger.info(f"  총 실패: {total_error}개")
    if total_success + total_error > 0:
        logger.info(f"  성공률: {total_success / (total_success + total_error) * 100:.1f}%")
    logger.info("=" * 80)
    logger.info("\n✅ 11월 3-7일 ModelEvaluation 재생성 완료!")


if __name__ == "__main__":
    print("\n📢 11월 3-7일 모든 ModelEvaluation을 재생성합니다.")
    print("   (StockAnalysisSummary 기반)")
    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        regenerate_all_evaluations()
    else:
        print("❌ 취소되었습니다.")
