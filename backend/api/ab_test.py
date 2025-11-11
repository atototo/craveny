"""
A/B 테스트 API

GPT-4o vs DeepSeek 모델 비교 테스트
"""
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.llm.predictor import get_predictor
from backend.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ab-test")


class ABTestRequest(BaseModel):
    """A/B 테스트 요청"""
    current_news: Dict[str, Any] = Field(..., description="현재 뉴스")
    similar_news: List[Dict[str, Any]] = Field(..., description="유사 뉴스 리스트")


@router.post("/predict")
async def ab_test_predict(request: ABTestRequest):
    """
    A/B 테스트 예측 API

    GPT-4o와 DeepSeek 모델을 동시에 호출하여 비교합니다.
    """
    try:
        if not settings.AB_TEST_ENABLED:
            raise HTTPException(
                status_code=400,
                detail="A/B 테스트가 비활성화되어 있습니다. .env에서 AB_TEST_ENABLED=true로 설정하세요."
            )

        logger.info(f"A/B 테스트 요청: {request.current_news.get('title', 'N/A')[:50]}")

        predictor = get_predictor()

        result = predictor.dual_predict(
            current_news=request.current_news,
            similar_news=request.similar_news,
        )

        logger.info(f"A/B 테스트 완료")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A/B 테스트 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"A/B 테스트 실패: {str(e)}")


@router.get("/status")
async def ab_test_status():
    """A/B 테스트 설정 상태 조회 (레거시 - 환경변수 기반)"""
    return {
        "ab_test_enabled": settings.AB_TEST_ENABLED,
        "model_a": {
            "provider": settings.MODEL_A_PROVIDER,
            "name": settings.MODEL_A_NAME,
        },
        "model_b": {
            "provider": settings.MODEL_B_PROVIDER,
            "name": settings.MODEL_B_NAME,
        },
    }


# ==================== 동적 A/B 설정 API (NEW) ====================

from backend.db.models.model import Model
from backend.db.models.ab_test_config import ABTestConfig
from backend.db.session import SessionLocal
from backend.utils.prediction_status import get_tracker
from typing import List


class ABConfigResponse(BaseModel):
    """A/B 설정 응답"""
    id: int
    model_a: Dict[str, Any]
    model_b: Dict[str, Any]
    is_active: bool
    created_at: Any

    class Config:
        from_attributes = True


class ABConfigCreate(BaseModel):
    """A/B 설정 생성 요청"""
    model_a_id: int = Field(..., description="Model A ID")
    model_b_id: int = Field(..., description="Model B ID")


@router.get("/config")
async def get_ab_config():
    """
    현재 활성 A/B 설정 조회

    Returns:
        활성 A/B 설정 정보
    """
    db = SessionLocal()
    try:
        config = db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first()

        if not config:
            logger.warning("활성 A/B 설정 없음")
            return {
                "message": "활성 A/B 설정이 없습니다",
                "config": None
            }

        return {
            "id": config.id,
            "model_a": {
                "id": config.model_a.id,
                "name": config.model_a.name,
                "provider": config.model_a.provider,
                "model_identifier": config.model_a.model_identifier,
            },
            "model_b": {
                "id": config.model_b.id,
                "name": config.model_b.name,
                "provider": config.model_b.provider,
                "model_identifier": config.model_b.model_identifier,
            },
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(f"A/B 설정 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"A/B 설정 조회 실패: {str(e)}")
    finally:
        db.close()


@router.post("/config")
async def update_ab_config(config: ABConfigCreate):
    """
    A/B 설정 변경

    Args:
        config: 새 A/B 설정 (model_a_id, model_b_id)

    Returns:
        생성된 A/B 설정
    """
    db = SessionLocal()
    try:
        # 검증: 같은 모델을 선택하면 안 됨
        if config.model_a_id == config.model_b_id:
            raise HTTPException(
                status_code=400,
                detail="Model A와 Model B는 서로 다른 모델이어야 합니다"
            )

        # 검증: 두 모델이 모두 존재하는지 확인
        model_a = db.query(Model).filter(Model.id == config.model_a_id).first()
        model_b = db.query(Model).filter(Model.id == config.model_b_id).first()

        if not model_a:
            raise HTTPException(status_code=404, detail=f"Model A (ID: {config.model_a_id}) 없음")
        if not model_b:
            raise HTTPException(status_code=404, detail=f"Model B (ID: {config.model_b_id}) 없음")

        # 기존 활성 설정 비활성화
        db.query(ABTestConfig).filter(ABTestConfig.is_active == True).update(
            {"is_active": False}
        )

        # 새 설정 생성
        new_config = ABTestConfig(
            model_a_id=config.model_a_id,
            model_b_id=config.model_b_id,
            is_active=True,
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)

        logger.info(
            f"✅ A/B 설정 변경 완료: {model_a.name} vs {model_b.name}"
        )

        # 백그라운드에서 최근 뉴스에 대해 예측 생성 (예측이 없는 경우만)
        prediction_task_id = None
        try:
            from backend.utils.background_prediction import generate_predictions_for_recent_news

            stats = generate_predictions_for_recent_news(
                model_ids=[new_config.model_a_id, new_config.model_b_id],
                limit=20,  # 최근 20개 뉴스
                days=7,    # 최근 7일
                in_background=True
            )
            prediction_task_id = stats.get('task_id')
            logger.info(
                f"🔄 A/B 모델 예측 생성 시작: "
                f"{model_a.name} vs {model_b.name}, "
                f"total={stats['total']}, scheduled={stats['scheduled']}, skipped={stats['skipped']}, "
                f"task_id={prediction_task_id}"
            )
        except Exception as e:
            logger.warning(f"백그라운드 예측 생성 스케줄 실패: {e}")

        return {
            "id": new_config.id,
            "model_a": {
                "id": model_a.id,
                "name": model_a.name,
                "provider": model_a.provider,
            },
            "model_b": {
                "id": model_b.id,
                "name": model_b.name,
                "provider": model_b.provider,
            },
            "is_active": True,
            "message": f"A/B 설정이 '{model_a.name} vs {model_b.name}'으로 변경되었습니다",
            "prediction_task_id": prediction_task_id,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"A/B 설정 변경 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"A/B 설정 변경 실패: {str(e)}")
    finally:
        db.close()


@router.get("/prediction-status")
async def get_prediction_status():
    """
    예측 생성 진행 상태 조회

    Returns:
        진행 중인 예측 생성 작업 목록
    """
    try:
        tracker = get_tracker()
        active_tasks = tracker.get_all_active_tasks()

        return {
            "has_active_tasks": len(active_tasks) > 0,
            "active_tasks": active_tasks,
        }

    except Exception as e:
        logger.error(f"진행 상태 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"진행 상태 조회 실패: {str(e)}")


@router.get("/history")
async def get_ab_config_history(limit: int = 10):
    """
    A/B 설정 변경 이력 조회

    Args:
        limit: 조회할 이력 개수 (기본값: 10)

    Returns:
        A/B 설정 이력 리스트
    """
    db = SessionLocal()
    try:
        configs = (
            db.query(ABTestConfig)
            .order_by(ABTestConfig.created_at.desc())
            .limit(limit)
            .all()
        )

        history = []
        for config in configs:
            history.append({
                "id": config.id,
                "model_a": {
                    "id": config.model_a.id,
                    "name": config.model_a.name,
                },
                "model_b": {
                    "id": config.model_b.id,
                    "name": config.model_b.name,
                },
                "is_active": config.is_active,
                "created_at": config.created_at.isoformat(),
            })

        return {"history": history, "count": len(history)}

    except Exception as e:
        logger.error(f"A/B 이력 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"A/B 이력 조회 실패: {str(e)}")
    finally:
        db.close()
