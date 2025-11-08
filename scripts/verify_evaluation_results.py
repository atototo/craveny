"""
평가 결과 검증
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func
from backend.db.session import SessionLocal
from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.evaluation_history import EvaluationHistory
from backend.db.models.daily_performance import DailyModelPerformance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_evaluation_results():
    """평가 결과 검증"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info("📊 평가 결과 검증")
        logger.info("=" * 80)

        # 1. ModelEvaluation 결과 확인
        logger.info("\n1️⃣ ModelEvaluation 테이블")
        total_evaluations = db.query(ModelEvaluation).count()
        logger.info(f"  총 평가 건수: {total_evaluations}건")

        # 날짜별 평가 건수
        date_counts = db.query(
            func.date(ModelEvaluation.predicted_at).label('date'),
            func.count(ModelEvaluation.id).label('count'),
            func.avg(ModelEvaluation.final_score).label('avg_score')
        ).group_by(
            func.date(ModelEvaluation.predicted_at)
        ).order_by('date').all()

        logger.info("\n  📅 날짜별 평가 결과:")
        for date, count, avg_score in date_counts:
            logger.info(
                f"    {date}: {count}건, "
                f"평균 점수 {avg_score:.1f}"
            )

        # 2. DailyModelPerformance 결과 확인
        logger.info("\n2️⃣ DailyModelPerformance 테이블")
        daily_perfs = db.query(DailyModelPerformance).order_by(
            DailyModelPerformance.date
        ).all()

        logger.info(f"  총 집계 레코드: {len(daily_perfs)}건")

        if daily_perfs:
            logger.info("\n  📈 일별 성과 집계:")
            for perf in daily_perfs:
                logger.info(
                    f"    {perf.date}: "
                    f"평가 {perf.evaluated_count}건, "
                    f"평균 점수 {perf.avg_final_score:.1f}, "
                    f"목표가 달성률 {perf.target_achieved_rate:.1f}%"
                )

        # 3. 샘플 평가 내역
        logger.info("\n3️⃣ 샘플 평가 내역 (각 날짜별 3건)")
        for date, _, _ in date_counts[:3]:
            evals = db.query(ModelEvaluation).filter(
                func.date(ModelEvaluation.predicted_at) == date
            ).limit(3).all()

            logger.info(f"\n  📅 {date}:")
            for eval in evals:
                logger.info(
                    f"    {eval.stock_code}: "
                    f"점수={eval.final_score:.1f}, "
                    f"목표가 {'달성' if eval.target_achieved else '미달성'}, "
                    f"손절 {'이탈' if eval.support_breached else '안전'}"
                )

        logger.info("\n" + "=" * 80)
        logger.info("✅ 평가 결과 검증 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 검증 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    verify_evaluation_results()
