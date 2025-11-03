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

router = APIRouter()


class ABTestRequest(BaseModel):
    """A/B 테스트 요청"""
    current_news: Dict[str, Any] = Field(..., description="현재 뉴스")
    similar_news: List[Dict[str, Any]] = Field(..., description="유사 뉴스 리스트")


@router.post("/ab-test/predict")
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


@router.get("/ab-test/status")
async def ab_test_status():
    """A/B 테스트 설정 상태 조회"""
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
