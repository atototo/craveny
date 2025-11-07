"""
Model evaluation API endpoints.

평가 조회, 사람 평가 저장, 대시보드 데이터 제공 API.
"""
import logging
from typing import List, Optional
from datetime import datetime, date, timedelta

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func

from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.daily_performance import DailyModelPerformance
from backend.db.models.evaluation_history import EvaluationHistory
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Pydantic Models ====================

class HumanRatingRequest(BaseModel):
    """사람 평가 요청."""
    quality: int = Field(..., ge=1, le=5, description="분석 품질 (1-5)")
    usefulness: int = Field(..., ge=1, le=5, description="실용성 (1-5)")
    overall: int = Field(..., ge=1, le=5, description="종합 만족도 (1-5)")
    evaluator: str = Field(..., description="평가자 이름")
    reason: Optional[str] = Field(None, description="수정 사유 (수정 시)")


class EvaluationResponse(BaseModel):
    """평가 응답."""
    id: int
    prediction_id: int
    model_id: int
    stock_code: str
    stock_name: Optional[str] = None
    model_name: Optional[str] = None
    predicted_at: datetime

    # 예측 정보
    predicted_target_price: Optional[float]
    predicted_support_price: Optional[float]
    predicted_base_price: float
    predicted_confidence: Optional[float]
    ai_reasoning: Optional[str] = None  # AI 분석 코멘트

    # AI 리포트 상세 내용
    overall_summary: Optional[str] = None  # 종합 의견
    recommendation: Optional[str] = None  # 최종 추천
    short_term_scenario: Optional[str] = None  # 단기 시나리오
    risk_factors: Optional[list] = None  # 리스크 요인
    opportunity_factors: Optional[list] = None  # 기회 요인

    # 실제 결과
    actual_high_1d: Optional[float]
    actual_low_1d: Optional[float]
    actual_close_1d: Optional[float]
    actual_high_5d: Optional[float]
    actual_low_5d: Optional[float]
    actual_close_5d: Optional[float]
    target_achieved: Optional[bool]
    target_achieved_days: Optional[int]
    support_breached: Optional[bool]

    # 점수
    target_accuracy_score: Optional[float]
    timing_score: Optional[float]
    risk_management_score: Optional[float]
    final_score: Optional[float]

    # 사람 평가
    human_rating_quality: Optional[int]
    human_rating_usefulness: Optional[int]
    human_rating_overall: Optional[int]
    human_evaluated_by: Optional[str]
    human_evaluated_at: Optional[datetime]

    class Config:
        from_attributes = True


class DailyPerformanceResponse(BaseModel):
    """일일 성능 응답."""
    model_id: int
    date: date
    total_predictions: int
    evaluated_count: int
    human_evaluated_count: int
    avg_final_score: Optional[float]
    avg_auto_score: Optional[float]
    avg_human_score: Optional[float]
    target_achieved_rate: Optional[float]
    support_breach_rate: Optional[float]

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    """대시보드 응답."""
    today_queue_count: int
    today_evaluated_count: int
    models: List[dict]
    recent_trend: List[dict]


# ==================== API Endpoints ====================

@router.get("/evaluations/all", response_model=List[EvaluationResponse])
async def get_all_evaluations(
    limit: int = Query(20, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    모든 평가 목록 조회 (사람 평가 여부 무관).

    페이징 지원.
    """
    from backend.db.models.stock import Stock
    from backend.db.models.prediction import Prediction

    db = SessionLocal()
    try:
        # 모든 평가 조회 (종목코드 → 모델ID → 날짜 역순)
        evaluations = db.query(ModelEvaluation).order_by(
            ModelEvaluation.stock_code.asc(),
            ModelEvaluation.model_id.asc(),
            ModelEvaluation.predicted_at.desc()
        ).limit(limit).offset(offset).all()

        # 종목명과 모델명 추가 (DB에서 조회)
        from backend.db.models.model import Model
        stock_map = {s.code: s.name for s in db.query(Stock).all()}
        model_map = {m.id: m.name for m in db.query(Model).all()}

        # AI reasoning 조회를 위한 prediction 맵 (prediction_id가 -1이 아닌 경우만)
        prediction_ids = [e.prediction_id for e in evaluations if e.prediction_id > 0]
        predictions = {}
        if prediction_ids:
            pred_list = db.query(Prediction).filter(Prediction.id.in_(prediction_ids)).all()
            predictions = {p.id: p.reasoning for p in pred_list}

        # StockAnalysisSummary 조회 (AI 리포트 상세 내용)
        from backend.db.models.stock_analysis import StockAnalysisSummary
        reports = {}
        if prediction_ids:
            report_list = db.query(StockAnalysisSummary).filter(
                StockAnalysisSummary.id.in_(prediction_ids)
            ).all()
            reports = {r.id: r for r in report_list}

        result = []
        for e in evaluations:
            report = reports.get(e.prediction_id) if e.prediction_id > 0 else None
            result.append(EvaluationResponse(
                id=e.id,
                prediction_id=e.prediction_id,
                model_id=e.model_id,
                stock_code=e.stock_code,
                stock_name=stock_map.get(e.stock_code),
                model_name=model_map.get(e.model_id),
                predicted_at=e.predicted_at,
                predicted_target_price=e.predicted_target_price,
                predicted_support_price=e.predicted_support_price,
                predicted_base_price=e.predicted_base_price,
                predicted_confidence=e.predicted_confidence,
                ai_reasoning=predictions.get(e.prediction_id) if e.prediction_id > 0 else None,
                # AI 리포트 상세 내용
                overall_summary=report.overall_summary if report else None,
                recommendation=report.recommendation if report else None,
                short_term_scenario=report.short_term_scenario if report else None,
                risk_factors=report.risk_factors if report else None,
                opportunity_factors=report.opportunity_factors if report else None,
                actual_high_1d=e.actual_high_1d,
                actual_low_1d=e.actual_low_1d,
                actual_close_1d=e.actual_close_1d,
                actual_high_5d=e.actual_high_5d,
                actual_low_5d=e.actual_low_5d,
                actual_close_5d=e.actual_close_5d,
                target_achieved=e.target_achieved,
                target_achieved_days=e.target_achieved_days,
                support_breached=e.support_breached,
                target_accuracy_score=e.target_accuracy_score,
                timing_score=e.timing_score,
                risk_management_score=e.risk_management_score,
                final_score=e.final_score,
                human_rating_quality=e.human_rating_quality,
                human_rating_usefulness=e.human_rating_usefulness,
                human_rating_overall=e.human_rating_overall,
                human_evaluated_by=e.human_evaluated_by,
                human_evaluated_at=e.human_evaluated_at
            ))

        return result

    except Exception as e:
        logger.error(f"모든 평가 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/queue", response_model=List[EvaluationResponse])
async def get_evaluation_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    평가 대기 목록 조회 (Priority 1-2 종목만).

    사람 평가가 없고 Priority 높은 종목 우선 반환.
    """
    from backend.db.models.stock import Stock
    from backend.db.models.prediction import Prediction

    db = SessionLocal()
    try:
        # Priority 1-2 종목 코드 조회
        # TODO: stocks 테이블과 JOIN하여 priority 조회
        # 현재는 임시로 하드코딩
        priority_stocks = ["005930", "000660", "035720", "051910", "035420"]

        # 사람 평가 미완료 + Priority 종목
        evaluations = db.query(ModelEvaluation).filter(
            ModelEvaluation.human_evaluated_at.is_(None),
            ModelEvaluation.stock_code.in_(priority_stocks)
        ).order_by(
            ModelEvaluation.predicted_at.desc()
        ).limit(limit).offset(offset).all()

        # 종목명과 모델명 추가 (DB에서 조회)
        from backend.db.models.model import Model
        stock_map = {s.code: s.name for s in db.query(Stock).all()}
        model_map = {m.id: m.name for m in db.query(Model).all()}

        # AI reasoning 조회를 위한 prediction 맵
        prediction_ids = [e.prediction_id for e in evaluations]
        predictions = db.query(Prediction).filter(
            Prediction.id.in_(prediction_ids)
        ).all()
        prediction_map = {p.id: p.reasoning for p in predictions}

        results = []
        for evaluation in evaluations:
            eval_dict = {
                **evaluation.__dict__,
                "stock_name": stock_map.get(evaluation.stock_code),
                "model_name": model_map.get(evaluation.model_id, f"Model {evaluation.model_id}"),
                "ai_reasoning": prediction_map.get(evaluation.prediction_id)
            }
            results.append(EvaluationResponse(**eval_dict))

        logger.info(f"📋 평가 대기 목록: {len(results)}건")
        return results

    except Exception as e:
        logger.error(f"평가 대기 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/daily", response_model=List[EvaluationResponse])
async def get_daily_evaluations(
    target_date: date = Query(..., description="조회 날짜 (YYYY-MM-DD)"),
    model_id: Optional[int] = Query(None, description="특정 모델만 조회")
):
    """
    특정 날짜의 평가 내역 조회.

    수정 가능한 평가 목록 반환.
    """
    db = SessionLocal()
    try:
        query = db.query(ModelEvaluation).filter(
            func.date(ModelEvaluation.predicted_at) == target_date
        )

        if model_id:
            query = query.filter(ModelEvaluation.model_id == model_id)

        evaluations = query.order_by(
            ModelEvaluation.final_score.desc()
        ).all()

        logger.info(f"📅 Daily 평가 내역: {target_date}, {len(evaluations)}건")
        return evaluations

    except Exception as e:
        logger.error(f"Daily 평가 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/evaluations/{evaluation_id}/rate")
async def rate_evaluation(
    evaluation_id: int,
    rating: HumanRatingRequest
):
    """
    사람 평가 저장 (신규 또는 수정).

    수정 시 evaluation_history 테이블에 이력 기록.
    사람 평가 저장 후 해당 날짜의 daily_model_performance를 즉시 업데이트.
    """
    from backend.services.aggregation_service import AggregationService

    db = SessionLocal()
    try:
        evaluation = db.query(ModelEvaluation).filter(
            ModelEvaluation.id == evaluation_id
        ).first()

        if not evaluation:
            raise HTTPException(status_code=404, detail=f"평가 ID {evaluation_id} 없음")

        # 기존 평가 존재 시 이력 기록
        is_modification = evaluation.human_evaluated_at is not None
        if is_modification:
            history = EvaluationHistory(
                evaluation_id=evaluation_id,
                old_human_rating_quality=evaluation.human_rating_quality,
                old_human_rating_usefulness=evaluation.human_rating_usefulness,
                old_human_rating_overall=evaluation.human_rating_overall,
                old_final_score=evaluation.final_score,
                new_human_rating_quality=rating.quality,
                new_human_rating_usefulness=rating.usefulness,
                new_human_rating_overall=rating.overall,
                modified_by=rating.evaluator,
                reason=rating.reason
            )

        # 사람 평가 업데이트
        evaluation.human_rating_quality = rating.quality
        evaluation.human_rating_usefulness = rating.usefulness
        evaluation.human_rating_overall = rating.overall
        evaluation.human_evaluated_by = rating.evaluator
        evaluation.human_evaluated_at = datetime.now()

        # 최종 점수 재계산 (자동 70% + 사람 30%)
        auto_score = (
            (evaluation.target_accuracy_score or 0) * 0.4 +
            (evaluation.timing_score or 0) * 0.3 +
            (evaluation.risk_management_score or 0) * 0.3
        )
        human_score = (
            (rating.quality + rating.usefulness + rating.overall) / 3
        ) * 20  # 1-5 → 0-100

        evaluation.final_score = auto_score * 0.7 + human_score * 0.3

        # 이력 업데이트 (수정인 경우)
        if is_modification:
            history.new_final_score = evaluation.final_score
            db.add(history)

        db.commit()
        db.refresh(evaluation)

        logger.info(
            f"✅ 사람 평가 저장: ID {evaluation_id}, "
            f"품질={rating.quality}, 실용성={rating.usefulness}, "
            f"종합={rating.overall}, 최종점수={evaluation.final_score:.1f}"
        )

        # 🔄 즉시 집계 업데이트 (17:00 배치와 별개로 실행)
        try:
            aggregation_service = AggregationService(db)
            evaluation_date = evaluation.predicted_at.date()
            aggregation_service.aggregate_daily_performance(
                target_date=evaluation_date,
                model_id=evaluation.model_id
            )
            logger.info(
                f"📊 집계 즉시 업데이트 완료: model_id={evaluation.model_id}, "
                f"date={evaluation_date}"
            )
        except Exception as agg_error:
            # 집계 실패해도 사람 평가는 저장됨 (17:00 배치에서 재시도)
            logger.warning(
                f"⚠️ 집계 즉시 업데이트 실패 (17:00 배치에서 재시도): {agg_error}"
            )

        return {
            "id": evaluation.id,
            "final_score": evaluation.final_score,
            "message": "평가 저장 완료"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"사람 평가 저장 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """
    대시보드 데이터 조회.

    - 오늘의 평가 현황
    - 모델별 리더보드
    - 최근 30일 트렌드
    """
    db = SessionLocal()
    try:
        today = date.today()

        # 오늘의 평가 현황
        today_queue = db.query(func.count(ModelEvaluation.id)).filter(
            func.date(ModelEvaluation.predicted_at) == today,
            ModelEvaluation.human_evaluated_at.is_(None)
        ).scalar() or 0

        today_evaluated = db.query(func.count(ModelEvaluation.id)).filter(
            func.date(ModelEvaluation.predicted_at) == today,
            ModelEvaluation.human_evaluated_at.isnot(None)
        ).scalar() or 0

        # 모델별 리더보드 (최근 30일 평균)
        thirty_days_ago = today - timedelta(days=30)

        models = db.query(
            DailyModelPerformance.model_id,
            func.avg(DailyModelPerformance.avg_final_score).label("avg_score"),
            func.avg(DailyModelPerformance.target_achieved_rate).label("avg_achieved_rate"),
            func.sum(DailyModelPerformance.total_predictions).label("total_predictions")
        ).filter(
            DailyModelPerformance.date >= thirty_days_ago
        ).group_by(
            DailyModelPerformance.model_id
        ).order_by(
            func.avg(DailyModelPerformance.avg_final_score).desc()
        ).all()

        # 최근 30일 트렌드
        recent_trend = db.query(
            DailyModelPerformance.date,
            DailyModelPerformance.model_id,
            DailyModelPerformance.avg_final_score
        ).filter(
            DailyModelPerformance.date >= thirty_days_ago
        ).order_by(
            DailyModelPerformance.date.desc()
        ).all()

        # 모델명 DB에서 조회
        from backend.db.models.model import Model
        model_map = {m.id: m.name for m in db.query(Model).all()}

        return {
            "today_queue_count": today_queue,
            "today_evaluated_count": today_evaluated,
            "models": [
                {
                    "model_id": m.model_id,
                    "model_name": model_map.get(m.model_id, f"Model {m.model_id}"),
                    "avg_score": round(m.avg_score, 1) if m.avg_score else 0,
                    "avg_achieved_rate": round(m.avg_achieved_rate, 1) if m.avg_achieved_rate else 0,
                    "total_predictions": m.total_predictions
                }
                for m in models
            ],
            "recent_trend": [
                {
                    "date": t.date.isoformat(),
                    "model_id": t.model_id,
                    "model_name": model_map.get(t.model_id, f"Model {t.model_id}"),
                    "avg_score": round(t.avg_final_score, 1) if t.avg_final_score else 0
                }
                for t in recent_trend
            ]
        }

    except Exception as e:
        logger.error(f"대시보드 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/model/{model_id}")
async def get_model_detail(
    model_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """모델 상세 분석 데이터."""
    db = SessionLocal()
    try:
        import statistics

        cutoff_date = date.today() - timedelta(days=days)

        # 평가 데이터 조회
        evaluations = db.query(ModelEvaluation).filter(
            ModelEvaluation.model_id == model_id,
            func.date(ModelEvaluation.predicted_at) >= cutoff_date
        ).all()

        if not evaluations:
            return {
                "model_id": model_id,
                "total_predictions": 0,
                "message": "데이터 없음"
            }

        # 통계 계산
        final_scores = [e.final_score for e in evaluations if e.final_score]
        target_scores = [e.target_accuracy_score for e in evaluations if e.target_accuracy_score]
        timing_scores = [e.timing_score for e in evaluations if e.timing_score]
        risk_scores = [e.risk_management_score for e in evaluations if e.risk_management_score]

        return {
            "model_id": model_id,
            "total_predictions": len(evaluations),
            "human_evaluated_count": len([e for e in evaluations if e.human_evaluated_at]),
            "target_achieved_count": len([e for e in evaluations if e.target_achieved]),
            "support_breach_count": len([e for e in evaluations if e.support_breached]),

            "avg_final_score": statistics.mean(final_scores) if final_scores else 0,
            "avg_target_accuracy": statistics.mean(target_scores) if target_scores else 0,
            "avg_timing_score": statistics.mean(timing_scores) if timing_scores else 0,
            "avg_risk_management": statistics.mean(risk_scores) if risk_scores else 0,

            "median_target_accuracy": statistics.median(target_scores) if target_scores else 0,
            "median_timing_score": statistics.median(timing_scores) if timing_scores else 0,
            "median_risk_management": statistics.median(risk_scores) if risk_scores else 0,

            "std_target_accuracy": statistics.stdev(target_scores) if len(target_scores) > 1 else 0,
            "std_timing_score": statistics.stdev(timing_scores) if len(timing_scores) > 1 else 0,
            "std_risk_management": statistics.stdev(risk_scores) if len(risk_scores) > 1 else 0,

            "target_achieved_rate": len([e for e in evaluations if e.target_achieved]) / len(evaluations) * 100,
            "support_breach_rate": len([e for e in evaluations if e.support_breached]) / len(evaluations) * 100
        }

    except Exception as e:
        logger.error(f"모델 상세 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/evaluations/model/{model_id}/stocks")
async def get_model_stock_performance(
    model_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """종목별 성능 분석."""
    db = SessionLocal()
    try:
        from sqlalchemy import Integer

        cutoff_date = date.today() - timedelta(days=days)

        # 종목별 집계
        stock_stats = db.query(
            ModelEvaluation.stock_code,
            func.count(ModelEvaluation.id).label("prediction_count"),
            func.avg(ModelEvaluation.final_score).label("avg_score"),
            func.sum(func.cast(ModelEvaluation.target_achieved, Integer)).label("target_achieved_count"),
            func.sum(func.cast(ModelEvaluation.support_breached, Integer)).label("support_breached_count")
        ).filter(
            ModelEvaluation.model_id == model_id,
            func.date(ModelEvaluation.predicted_at) >= cutoff_date
        ).group_by(
            ModelEvaluation.stock_code
        ).all()

        return [
            {
                "stock_code": s.stock_code,
                "prediction_count": s.prediction_count,
                "avg_score": s.avg_score,
                "target_achieved_rate": (s.target_achieved_count / s.prediction_count * 100) if s.prediction_count > 0 else 0,
                "support_breach_rate": (s.support_breached_count / s.prediction_count * 100) if s.prediction_count > 0 else 0,
                "trend": "up" if s.avg_score and s.avg_score > 70 else "down"
            }
            for s in stock_stats
        ]

    except Exception as e:
        logger.error(f"종목별 성능 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
