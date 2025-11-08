"""
평가 테이블 데이터 정리
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.db.session import SessionLocal
from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.evaluation_history import EvaluationHistory
from backend.db.models.daily_performance import DailyModelPerformance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clear_evaluation_tables():
    """평가 테이블 전체 데이터 삭제"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info("🗑️  평가 테이블 데이터 정리")
        logger.info("=" * 80)

        # 기존 데이터 확인
        model_eval_count = db.query(ModelEvaluation).count()
        eval_history_count = db.query(EvaluationHistory).count()
        daily_perf_count = db.query(DailyModelPerformance).count()

        logger.info(f"\n📊 현재 데이터:")
        logger.info(f"  - ModelEvaluation: {model_eval_count}건")
        logger.info(f"  - EvaluationHistory: {eval_history_count}건")
        logger.info(f"  - DailyModelPerformance: {daily_perf_count}건")

        # 삭제 시작
        logger.info(f"\n🗑️  데이터 삭제 중...")

        # 1. ModelEvaluation 삭제
        deleted_model_eval = db.query(ModelEvaluation).delete()
        logger.info(f"  ✅ ModelEvaluation: {deleted_model_eval}건 삭제")

        # 2. EvaluationHistory 삭제
        deleted_eval_history = db.query(EvaluationHistory).delete()
        logger.info(f"  ✅ EvaluationHistory: {deleted_eval_history}건 삭제")

        # 3. DailyModelPerformance 삭제
        deleted_daily_perf = db.query(DailyModelPerformance).delete()
        logger.info(f"  ✅ DailyModelPerformance: {deleted_daily_perf}건 삭제")

        db.commit()

        # 확인
        model_eval_count = db.query(ModelEvaluation).count()
        eval_history_count = db.query(EvaluationHistory).count()
        daily_perf_count = db.query(DailyModelPerformance).count()

        logger.info(f"\n📊 정리 후 데이터:")
        logger.info(f"  - ModelEvaluation: {model_eval_count}건")
        logger.info(f"  - EvaluationHistory: {eval_history_count}건")
        logger.info(f"  - DailyModelPerformance: {daily_perf_count}건")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 평가 테이블 정리 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 정리 실패: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()

    return True


if __name__ == "__main__":
    success = clear_evaluation_tables()
    sys.exit(0 if success else 1)
