"""
Automated evaluation scheduler.

매일 16:00에 D-1일 Investment Report를 자동 평가합니다.
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService


logger = logging.getLogger(__name__)


class EvaluationScheduler:
    """
    평가 스케줄러.

    매일 16:00에 D-1일 Investment Report를 자동 평가합니다.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        """스케줄러 시작."""
        # 매일 16:00 - 자동 평가
        self.scheduler.add_job(
            self._run_daily_evaluation,
            trigger="cron",
            hour=16,
            minute=0,
            id="daily_evaluation",
            name="일일 모델 평가"
        )

        # 매일 17:00 - 집계 배치
        self.scheduler.add_job(
            self._run_daily_aggregation,
            trigger="cron",
            hour=17,
            minute=0,
            id="daily_aggregation",
            name="일일 성능 집계"
        )

        self.scheduler.start()
        logger.info("✅ 평가 스케줄러 시작: 매일 16:00 평가, 17:00 집계")

    def stop(self):
        """스케줄러 중지."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️  평가 스케줄러 중지")

    def _run_daily_evaluation(self):
        """
        일일 평가 배치 작업.

        D-1일 생성된 Investment Report를 평가합니다.
        """
        logger.info("=" * 80)
        logger.info("🔄 일일 평가 배치 작업 시작")
        logger.info("=" * 80)

        db = SessionLocal()
        try:
            service = EvaluationService(db)

            # 어제 날짜
            yesterday = datetime.now() - timedelta(days=1)

            # 평가 대상 조회
            predictions = service.get_evaluable_predictions(yesterday)

            if not predictions:
                logger.info("📊 평가 대상 없음")
                return

            success_count = 0
            error_count = 0

            for prediction in predictions:
                try:
                    # 평가 실행
                    evaluation = service.evaluate_prediction(prediction)

                    if evaluation:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 평가 실패: {prediction.id}, {e}", exc_info=True)

            logger.info("=" * 80)
            logger.info(f"✅ 일일 평가 완료: 성공 {success_count}건, 실패 {error_count}건")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ 일일 평가 배치 작업 실패: {e}", exc_info=True)
        finally:
            db.close()

    def run_manual(self, target_date: datetime = None):
        """
        수동 실행 (테스트용).

        Args:
            target_date: 평가 대상 날짜 (기본값: 어제)
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)

        logger.info(f"🔧 수동 평가 실행: {target_date.date()}")

        db = SessionLocal()
        try:
            service = EvaluationService(db)

            # 평가 대상 조회
            predictions = service.get_evaluable_predictions(target_date)

            if not predictions:
                logger.info("📊 평가 대상 없음")
                return

            success_count = 0
            error_count = 0

            for prediction in predictions:
                try:
                    evaluation = service.evaluate_prediction(prediction)

                    if evaluation:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 평가 실패: {prediction.id}, {e}", exc_info=True)

            logger.info(f"✅ 수동 평가 완료: 성공 {success_count}건, 실패 {error_count}건")

        except Exception as e:
            logger.error(f"❌ 수동 평가 실패: {e}", exc_info=True)
        finally:
            db.close()

    def _run_daily_aggregation(self):
        """
        일일 집계 배치 작업.

        D-1일 평가 데이터를 집계합니다.
        """
        logger.info("=" * 80)
        logger.info("🔄 일일 집계 배치 작업 시작")
        logger.info("=" * 80)

        db = SessionLocal()
        try:
            from backend.services.aggregation_service import AggregationService

            service = AggregationService(db)

            # 어제 날짜
            yesterday = (datetime.now() - timedelta(days=1)).date()

            # 집계 실행
            aggregated_count = service.aggregate_daily_performance(yesterday)

            logger.info("=" * 80)
            logger.info(f"✅ 일일 집계 완료: {aggregated_count}개 모델")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ 일일 집계 배치 작업 실패: {e}", exc_info=True)
        finally:
            db.close()

    def run_manual_aggregation(self, target_date: datetime = None):
        """
        수동 집계 실행 (테스트용).

        Args:
            target_date: 집계 대상 날짜 (기본값: 어제)
        """
        if target_date is None:
            target_date = (datetime.now() - timedelta(days=1)).date()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()

        logger.info(f"🔧 수동 집계 실행: {target_date}")

        db = SessionLocal()
        try:
            from backend.services.aggregation_service import AggregationService

            service = AggregationService(db)
            aggregated_count = service.aggregate_daily_performance(target_date)

            logger.info(f"✅ 수동 집계 완료: {aggregated_count}개 모델")

        except Exception as e:
            logger.error(f"❌ 수동 집계 실패: {e}", exc_info=True)
        finally:
            db.close()
