"""
11월 1-5일 자동 평가 배치 실행 스크립트
실제 시스템 로직 사용
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService
from backend.services.aggregation_service import AggregationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_evaluation_for_date(target_date: date):
    """특정 날짜의 평가 실행 (Investment Report)"""
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 {target_date} 평가 시작")
    logger.info(f"{'='*80}")

    db = SessionLocal()
    try:
        # A/B 테스트 설정에서 실제 모델 ID 가져오기
        from backend.db.models.ab_test_config import ABTestConfig
        ab_config = db.query(ABTestConfig).filter(
            ABTestConfig.is_active == True
        ).first()

        if ab_config:
            model_a_id = ab_config.model_a_id
            model_b_id = ab_config.model_b_id
            logger.info(f"✅ A/B 테스트 설정: Model A={model_a_id}, Model B={model_b_id}")
        else:
            # fallback
            model_a_id = 1
            model_b_id = 2
            logger.warning(f"⚠️ A/B 테스트 설정 없음, fallback: Model A={model_a_id}, Model B={model_b_id}")

        service = EvaluationService(db)

        # 평가 대상 조회 (해당 날짜에 생성된 Investment Report)
        target_datetime = datetime.combine(target_date, datetime.min.time())
        reports = service.get_evaluable_reports(target_datetime)

        if not reports:
            logger.warning(f"⚠️ {target_date}: 평가 대상 없음")
            return 0

        success_count = 0
        error_count = 0

        for report in reports:
            # A/B 테스트 리포트인 경우 두 모델 모두 평가
            if report.custom_data and report.custom_data.get('ab_test_enabled'):
                # Model A 평가
                try:
                    evaluation_a = service.evaluate_report(report, model_id=model_a_id)
                    if evaluation_a:
                        success_count += 1
                        logger.info(f"  ✅ Model A (ID={model_a_id}) 평가 완료: {report.stock_code}, score={evaluation_a.final_score:.1f}")
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"  ❌ Model A (ID={model_a_id}) 평가 실패: {report.stock_code}, {e}")

                # Model B 평가
                try:
                    evaluation_b = service.evaluate_report(report, model_id=model_b_id)
                    if evaluation_b:
                        success_count += 1
                        logger.info(f"  ✅ Model B (ID={model_b_id}) 평가 완료: {report.stock_code}, score={evaluation_b.final_score:.1f}")
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"  ❌ Model B (ID={model_b_id}) 평가 실패: {report.stock_code}, {e}")
            else:
                # 일반 리포트는 Model A ID로 평가
                try:
                    evaluation = service.evaluate_report(report, model_id=model_a_id)
                    if evaluation:
                        success_count += 1
                        logger.info(f"  ✅ 평가 완료: {report.stock_code}, score={evaluation.final_score:.1f}")
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(f"  ❌ 평가 실패: {report.stock_code}, {e}")

        logger.info(f"✅ {target_date} 평가 완료: 성공 {success_count}건, 실패 {error_count}건")
        return success_count

    except Exception as e:
        logger.error(f"❌ {target_date} 평가 오류: {e}", exc_info=True)
        return 0
    finally:
        db.close()


def run_aggregation_for_date(target_date: date):
    """특정 날짜의 집계 실행"""
    logger.info(f"\n{'='*80}")
    logger.info(f"📈 {target_date} 집계 시작")
    logger.info(f"{'='*80}")

    db = SessionLocal()
    try:
        service = AggregationService(db)
        result = service.aggregate_daily_performance(target_date=target_date)

        logger.info(f"✅ {target_date} 집계 완료: {len(result)}개 모델")
        return len(result)

    except Exception as e:
        logger.error(f"❌ {target_date} 집계 오류: {e}", exc_info=True)
        return 0
    finally:
        db.close()


def main():
    logger.info("\n" + "="*80)
    logger.info("🚀 과거 Investment Report 평가 배치 실행")
    logger.info("="*80)

    total_evaluations = 0
    total_aggregations = 0

    # 11월 1일, 4일, 5일, 6일 (영업일)
    target_dates = [
        date(2025, 11, 1),   # 금요일
        date(2025, 11, 4),   # 월요일
        date(2025, 11, 5),   # 화요일
        date(2025, 11, 6),   # 수요일
    ]

    for target_date in target_dates:
        # 1. 평가 실행
        eval_count = run_evaluation_for_date(target_date)
        total_evaluations += eval_count

        # 2. 집계 실행
        agg_count = run_aggregation_for_date(target_date)
        total_aggregations += agg_count

    # 최종 결과
    logger.info("\n" + "="*80)
    logger.info("🎉 배치 실행 완료")
    logger.info(f"  - 총 평가: {total_evaluations}건")
    logger.info(f"  - 총 집계: {total_aggregations}개 모델")
    logger.info("="*80)


if __name__ == "__main__":
    main()
