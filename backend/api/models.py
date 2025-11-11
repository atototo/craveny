"""
모델 관리 API

LLM 모델 CRUD 및 관리 기능을 제공합니다.
"""
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.db.models.model import Model
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ==================== Pydantic Models ====================

class ModelCreate(BaseModel):
    """모델 생성 요청"""
    name: str = Field(..., description="모델 표시 이름 (예: GPT-4o)")
    provider: str = Field(..., description="모델 제공자 (openai, openrouter)")
    model_identifier: str = Field(..., description="실제 모델 식별자 (예: gpt-4o, deepseek/deepseek-v3.2-exp)")
    description: Optional[str] = Field(None, description="모델 설명")


class ModelUpdate(BaseModel):
    """모델 수정 요청"""
    name: Optional[str] = None
    provider: Optional[str] = None
    model_identifier: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ModelResponse(BaseModel):
    """모델 응답"""
    id: int
    name: str
    provider: str
    model_identifier: str
    is_active: bool
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== API Endpoints ====================

@router.get("/models", response_model=List[ModelResponse])
async def list_models(active_only: bool = False):
    """
    모델 목록 조회

    Args:
        active_only: True면 활성 모델만 반환

    Returns:
        모델 리스트
    """
    db = SessionLocal()
    try:
        query = db.query(Model)
        if active_only:
            query = query.filter(Model.is_active == True)

        models = query.all()
        logger.info(f"모델 목록 조회: {len(models)}개")

        return models

    except Exception as e:
        logger.error(f"모델 목록 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")
    finally:
        db.close()


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int):
    """
    특정 모델 조회

    Args:
        model_id: 모델 ID

    Returns:
        모델 정보
    """
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail=f"모델 ID {model_id} 없음")

        logger.info(f"모델 조회: {model.name}")
        return model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모델 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 조회 실패: {str(e)}")
    finally:
        db.close()


@router.post("/models", response_model=ModelResponse, status_code=201)
async def create_model(model: ModelCreate):
    """
    새 모델 추가 + 최근 뉴스에 대해 자동으로 예측 생성

    Args:
        model: 모델 생성 정보

    Returns:
        생성된 모델
    """
    db = SessionLocal()
    try:
        # 중복 이름 체크
        existing = db.query(Model).filter(Model.name == model.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"모델 이름 '{model.name}'이 이미 존재합니다")

        # 새 모델 생성
        new_model = Model(
            name=model.name,
            provider=model.provider,
            model_identifier=model.model_identifier,
            description=model.description,
            is_active=True,  # 기본값: 활성화
        )

        db.add(new_model)
        db.commit()
        db.refresh(new_model)

        logger.info(f"✅ 모델 추가 완료: {new_model.name} (ID: {new_model.id})")

        # 백그라운드에서 최근 뉴스에 대해 예측 생성
        try:
            from backend.utils.background_prediction import generate_predictions_for_recent_news

            stats = generate_predictions_for_recent_news(
                model_ids=[new_model.id],
                limit=20,  # 최근 20개 뉴스
                days=7,    # 최근 7일
                in_background=True
            )
            logger.info(
                f"🔄 백그라운드 예측 생성 시작: "
                f"model={new_model.name}, "
                f"total={stats['total']}, scheduled={stats['scheduled']}"
            )
        except Exception as e:
            logger.warning(f"백그라운드 예측 생성 스케줄 실패: {e}")

        return new_model

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"모델 추가 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 추가 실패: {str(e)}")
    finally:
        db.close()


@router.put("/models/{model_id}", response_model=ModelResponse)
async def update_model(model_id: int, model_update: ModelUpdate):
    """
    모델 정보 수정

    Args:
        model_id: 모델 ID
        model_update: 수정할 정보

    Returns:
        수정된 모델
    """
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail=f"모델 ID {model_id} 없음")

        # 수정할 필드만 업데이트
        update_data = model_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(model, field, value)

        db.commit()
        db.refresh(model)

        logger.info(f"✅ 모델 수정 완료: {model.name}")
        return model

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"모델 수정 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 수정 실패: {str(e)}")
    finally:
        db.close()


@router.patch("/models/{model_id}/toggle")
async def toggle_model_status(model_id: int):
    """
    모델 활성화/비활성화 토글

    Args:
        model_id: 모델 ID

    Returns:
        {"is_active": bool, "message": str}
    """
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail=f"모델 ID {model_id} 없음")

        # 상태 토글
        model.is_active = not model.is_active
        db.commit()

        status = "활성화" if model.is_active else "비활성화"
        logger.info(f"✅ 모델 {status}: {model.name}")

        return {
            "is_active": model.is_active,
            "message": f"모델 '{model.name}' {status} 완료"
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"모델 상태 변경 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 상태 변경 실패: {str(e)}")
    finally:
        db.close()


@router.delete("/models/{model_id}", status_code=204)
async def delete_model(model_id: int):
    """
    모델 삭제 (애플리케이션 레벨 무결성 검증)

    FK 제약조건 없이 애플리케이션에서 데이터 무결성을 관리합니다.
    삭제 전 영향도를 분석하고 명시적으로 로깅합니다.

    Args:
        model_id: 모델 ID

    Returns:
        204 No Content
    """
    db = SessionLocal()
    try:
        model = db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise HTTPException(status_code=404, detail=f"모델 ID {model_id} 없음")

        logger.info("=" * 80)
        logger.info(f"🗑️ 모델 삭제 요청: {model.name} (ID: {model_id})")
        logger.info("=" * 80)

        # ==================== 무결성 검증 ====================
        from backend.db.models.ab_test_config import ABTestConfig
        from backend.db.models.prediction import Prediction

        # 1. 활성화된 A/B 설정 확인 (삭제 차단)
        active_ab_configs = db.query(ABTestConfig).filter(
            ABTestConfig.is_active == True,
            (ABTestConfig.model_a_id == model_id) | (ABTestConfig.model_b_id == model_id)
        ).all()

        if active_ab_configs:
            logger.warning(f"⚠️ 활성 A/B 테스트에서 사용 중: {len(active_ab_configs)}개 설정")
            raise HTTPException(
                status_code=400,
                detail=f"이 모델은 현재 활성화된 A/B 테스트에서 사용 중입니다. 먼저 A/B 설정을 변경하세요."
            )

        # 2. 영향도 분석
        inactive_ab_configs = db.query(ABTestConfig).filter(
            ABTestConfig.is_active == False,
            (ABTestConfig.model_a_id == model_id) | (ABTestConfig.model_b_id == model_id)
        ).all()

        predictions = db.query(Prediction).filter(Prediction.model_id == model_id).all()

        logger.info(f"\n📊 삭제 영향도 분석:")
        logger.info(f"  - 비활성 A/B 설정: {len(inactive_ab_configs)}개")
        logger.info(f"  - 예측 데이터: {len(predictions)}개")
        logger.info(f"  - 총 삭제 대상: {len(inactive_ab_configs) + len(predictions) + 1}개 레코드")

        # ==================== 연쇄 삭제 ====================

        # 3. 비활성화된 A/B 설정 삭제
        if inactive_ab_configs:
            logger.info(f"\n🔄 비활성 A/B 설정 {len(inactive_ab_configs)}개 삭제 중...")
            for config in inactive_ab_configs:
                db.delete(config)
                logger.info(f"  ✅ A/B 설정 삭제: ID {config.id}")

        # 4. 예측 데이터 삭제
        if predictions:
            logger.info(f"\n🔄 예측 데이터 {len(predictions)}개 삭제 중...")
            # 효율성을 위해 bulk delete 사용
            db.query(Prediction).filter(Prediction.model_id == model_id).delete()
            logger.info(f"  ✅ 예측 데이터 {len(predictions)}개 삭제 완료")

        # 5. 모델 삭제
        logger.info(f"\n🗑️ 모델 '{model.name}' 삭제 중...")
        db.delete(model)
        db.commit()

        logger.info(f"\n✅ 모델 삭제 완료: {model.name}")
        logger.info("=" * 80)
        return None

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"\n❌ 모델 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"모델 삭제 실패: {str(e)}")
    finally:
        db.close()
