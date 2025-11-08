"""
Daily model performance aggregation service.

매일 17:00에 모델별 일일 성능을 집계합니다.
"""
import logging
from datetime import datetime, date
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.daily_performance import DailyModelPerformance


logger = logging.getLogger(__name__)


class AggregationService:
    """일일 성능 집계 서비스."""

    def __init__(self, db: Session):
        self.db = db

    def aggregate_daily_performance(
        self,
        target_date: date,
        model_id: Optional[int] = None
    ) -> int:
        """
        특정 날짜의 모델 성능 집계.

        Args:
            target_date: 집계 대상 날짜
            model_id: 특정 모델만 집계 (None이면 전체)

        Returns:
            집계된 모델 수
        """
        # 집계 대상 모델 목록
        if model_id:
            model_ids = [model_id]
        else:
            model_ids_query = self.db.query(ModelEvaluation.model_id).filter(
                func.date(ModelEvaluation.predicted_at) == target_date
            ).distinct().all()
            model_ids = [m[0] for m in model_ids_query]

        if not model_ids:
            logger.info(f"📊 집계 대상 모델 없음: {target_date}")
            return 0

        logger.info(f"📊 집계 대상 모델: {len(model_ids)}개")

        success_count = 0
        for mid in model_ids:
            try:
                self._aggregate_model(target_date, mid)
                success_count += 1
            except Exception as e:
                logger.error(f"❌ 모델 집계 실패: model_id={mid}, {e}", exc_info=True)

        logger.info(f"✅ 집계 완료: {success_count}/{len(model_ids)} 모델")
        return success_count

    def _aggregate_model(self, target_date: date, model_id: int):
        """
        단일 모델 집계.

        Args:
            target_date: 집계 대상 날짜
            model_id: 모델 ID
        """
        # 해당 날짜 평가 데이터 조회
        evaluations = self.db.query(ModelEvaluation).filter(
            func.date(ModelEvaluation.predicted_at) == target_date,
            ModelEvaluation.model_id == model_id
        ).all()

        if not evaluations:
            logger.warning(f"⚠️ 평가 데이터 없음: model_id={model_id}, date={target_date}")
            return

        # 통계 계산
        total = len(evaluations)
        evaluated = len([e for e in evaluations if e.evaluated_at])
        human_evaluated = len([e for e in evaluations if e.human_evaluated_at])

        # 평균 점수
        # 최종 점수: final_score가 있는 평가들의 평균
        final_scores = [e.final_score for e in evaluations if e.final_score is not None]
        avg_final = sum(final_scores) / len(final_scores) if final_scores else None

        # 자동 점수: 가중 평균 (40:30:30)
        auto_scores = []
        for e in evaluations:
            if e.target_accuracy_score is not None and e.timing_score is not None and e.risk_management_score is not None:
                auto_score = (
                    (e.target_accuracy_score * 0.4) +
                    (e.timing_score * 0.3) +
                    (e.risk_management_score * 0.3)
                )
                auto_scores.append(auto_score)
        avg_auto = sum(auto_scores) / len(auto_scores) if auto_scores else None

        # 사람 평가 점수: 1-5점을 20배하여 0-100점으로 변환
        human_scores = []
        for e in evaluations:
            if e.human_evaluated_at and e.human_rating_quality and e.human_rating_usefulness and e.human_rating_overall:
                # 3개 점수 평균을 내고 20배
                avg_rating = (e.human_rating_quality + e.human_rating_usefulness + e.human_rating_overall) / 3
                human_scores.append(avg_rating * 20)
        avg_human = sum(human_scores) / len(human_scores) if human_scores else None

        # 세부 메트릭
        target_acc_scores = [e.target_accuracy_score for e in evaluations if e.target_accuracy_score is not None]
        avg_target_acc = sum(target_acc_scores) / len(target_acc_scores) if target_acc_scores else None

        timing_scores = [e.timing_score for e in evaluations if e.timing_score is not None]
        avg_timing = sum(timing_scores) / len(timing_scores) if timing_scores else None

        risk_scores = [e.risk_management_score for e in evaluations if e.risk_management_score is not None]
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else None

        # 성과 지표 (%)
        target_achieved_count = len([e for e in evaluations if e.target_achieved])
        target_achieved_rate = (target_achieved_count / total * 100) if total > 0 else 0.0

        support_breach_count = len([e for e in evaluations if e.support_breached])
        support_breach_rate = (support_breach_count / total * 100) if total > 0 else 0.0

        # UPSERT 로직
        existing = self.db.query(DailyModelPerformance).filter(
            DailyModelPerformance.model_id == model_id,
            DailyModelPerformance.date == target_date
        ).first()

        if existing:
            # UPDATE
            existing.total_predictions = total
            existing.evaluated_count = evaluated
            existing.human_evaluated_count = human_evaluated
            existing.avg_final_score = avg_final
            existing.avg_auto_score = avg_auto
            existing.avg_human_score = avg_human
            existing.avg_target_accuracy = avg_target_acc
            existing.avg_timing_score = avg_timing
            existing.avg_risk_management = avg_risk
            existing.target_achieved_rate = target_achieved_rate
            existing.support_breach_rate = support_breach_rate
            existing.updated_at = datetime.now()
            logger.info(f"📝 기존 레코드 업데이트: model_id={model_id}")
        else:
            # INSERT
            new_record = DailyModelPerformance(
                model_id=model_id,
                date=target_date,
                total_predictions=total,
                evaluated_count=evaluated,
                human_evaluated_count=human_evaluated,
                avg_final_score=avg_final,
                avg_auto_score=avg_auto,
                avg_human_score=avg_human,
                avg_target_accuracy=avg_target_acc,
                avg_timing_score=avg_timing,
                avg_risk_management=avg_risk,
                target_achieved_rate=target_achieved_rate,
                support_breach_rate=support_breach_rate
            )
            self.db.add(new_record)
            logger.info(f"➕ 신규 레코드 추가: model_id={model_id}")

        self.db.commit()

        avg_score_str = f"{avg_final:.1f}" if avg_final is not None else "0.0"
        logger.info(
            f"✅ 집계 완료: model_id={model_id}, "
            f"total={total}, avg_score={avg_score_str}, "
            f"target_rate={target_achieved_rate:.1f}%"
        )
