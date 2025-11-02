"""
주가 예측 API

뉴스 기반 주가 예측 엔드포인트를 제공합니다.
"""
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.llm.vector_search import get_vector_search
from backend.llm.predictor import get_predictor


logger = logging.getLogger(__name__)

router = APIRouter()


# === 요청/응답 스키마 ===


class PredictionRequest(BaseModel):
    """예측 요청 스키마"""

    news_id: int = Field(..., description="뉴스 ID", example=1)
    stock_code: Optional[str] = Field(
        None, description="종목 코드 (생략 시 뉴스의 종목 사용)", example="005930"
    )
    top_k: int = Field(
        5, description="참고할 유사 뉴스 개수", ge=1, le=20, example=5
    )
    similarity_threshold: float = Field(
        0.5, description="유사도 임계값 (0.0 ~ 1.0)", ge=0.0, le=1.0, example=0.5
    )
    use_cache: bool = Field(True, description="캐시 사용 여부", example=True)

    class Config:
        schema_extra = {
            "example": {
                "news_id": 1,
                "stock_code": "005930",
                "top_k": 5,
                "similarity_threshold": 0.5,
                "use_cache": True,
            }
        }


class PriceChange(BaseModel):
    """주가 변동률 스키마"""

    day1: Optional[float] = Field(None, description="T+1일 변동률 (%)", example=2.5)
    day2: Optional[float] = Field(None, description="T+2일 변동률 (%)", example=3.8)
    day3: Optional[float] = Field(None, description="T+3일 변동률 (%)", example=5.3)
    day5: Optional[float] = Field(None, description="T+5일 변동률 (%)", example=7.8)
    day10: Optional[float] = Field(None, description="T+10일 변동률 (%)", example=10.2)
    day20: Optional[float] = Field(None, description="T+20일 변동률 (%)", example=12.5)


class ConfidenceBreakdown(BaseModel):
    """신뢰도 구성 요소 스키마 (Phase 2)"""

    similar_news_quality: Optional[int] = Field(
        None, description="유사 뉴스 품질 점수", ge=0, le=100, example=85
    )
    pattern_consistency: Optional[int] = Field(
        None, description="패턴 일관성 점수", ge=0, le=100, example=70
    )
    disclosure_impact: Optional[int] = Field(
        None, description="공시 영향 점수", ge=0, le=100, example=60
    )
    explanation: Optional[str] = Field(
        None, description="신뢰도 계산 근거", example="유사 뉴스 5건, 일관된 상승 패턴"
    )


class PatternAnalysis(BaseModel):
    """패턴 분석 통계 스키마 (Phase 2)"""

    avg_1d: Optional[float] = Field(None, description="T+1일 평균 변동률 (%)", example=2.5)
    avg_2d: Optional[float] = Field(None, description="T+2일 평균 변동률 (%)", example=3.2)
    avg_3d: Optional[float] = Field(None, description="T+3일 평균 변동률 (%)", example=5.3)
    avg_5d: Optional[float] = Field(None, description="T+5일 평균 변동률 (%)", example=7.8)
    avg_10d: Optional[float] = Field(None, description="T+10일 평균 변동률 (%)", example=10.2)
    avg_20d: Optional[float] = Field(None, description="T+20일 평균 변동률 (%)", example=12.5)
    max_1d: Optional[float] = Field(None, description="T+1일 최대 변동률 (%)", example=8.5)
    min_1d: Optional[float] = Field(None, description="T+1일 최소 변동률 (%)", example=-2.1)
    count: Optional[int] = Field(None, description="분석된 유사 뉴스 개수", example=5)


class SimilarNews(BaseModel):
    """유사 뉴스 스키마"""

    news_id: int = Field(..., description="뉴스 ID", example=2)
    title: str = Field(..., description="뉴스 제목", example="삼성전자, 3나노 공정...")
    similarity: float = Field(..., description="유사도 (0.0 ~ 1.0)", example=0.95)
    price_changes: PriceChange = Field(..., description="주가 변동률")


class PredictionResponse(BaseModel):
    """예측 응답 스키마"""

    # 예측 결과
    prediction: str = Field(
        ..., description="예측 방향 (상승/하락/유지)", example="상승"
    )
    confidence: int = Field(..., description="신뢰도 (0 ~ 100)", ge=0, le=100, example=85)
    reasoning: str = Field(
        ...,
        description="예측 근거",
        example="과거 유사 뉴스에서 T+5일 7.8% 상승 패턴 확인",
    )

    # 기간별 예측
    short_term: str = Field(..., description="단기 (T+1일) 예측", example="2.5% 상승 예상")
    medium_term: str = Field(..., description="중기 (T+3일) 예측", example="5.3% 상승 예상")
    long_term: str = Field(..., description="장기 (T+5일) 예측", example="7.8% 상승 예상")

    # Phase 2: 신뢰도 구성 요소
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(
        None, description="신뢰도 구성 요소 분석"
    )

    # Phase 2: 패턴 분석 통계
    pattern_analysis: Optional[PatternAnalysis] = Field(
        None, description="유사 뉴스 패턴 분석 통계"
    )

    # 메타 정보
    similar_news: list[SimilarNews] = Field(..., description="참고한 유사 뉴스 목록")
    cached: bool = Field(..., description="캐시 사용 여부", example=False)
    model: str = Field(..., description="사용 모델", example="gpt-4o")
    timestamp: str = Field(
        ..., description="예측 시각 (ISO 8601)", example="2025-11-01T14:00:00"
    )

    class Config:
        schema_extra = {
            "example": {
                "prediction": "상승",
                "confidence": 85,
                "reasoning": "과거 유사 뉴스에서 T+5일 7.8% 상승 패턴 확인",
                "short_term": "2.5% 상승 예상",
                "medium_term": "5.3% 상승 예상",
                "long_term": "7.8% 상승 예상",
                "confidence_breakdown": {
                    "similar_news_quality": 85,
                    "pattern_consistency": 70,
                    "disclosure_impact": 60,
                    "explanation": "유사 뉴스 5건, 일관된 상승 패턴",
                },
                "pattern_analysis": {
                    "avg_1d": 2.5,
                    "avg_2d": 3.2,
                    "avg_3d": 5.3,
                    "avg_5d": 7.8,
                    "avg_10d": 10.2,
                    "avg_20d": 12.5,
                    "max_1d": 8.5,
                    "min_1d": -2.1,
                    "count": 5,
                },
                "similar_news": [
                    {
                        "news_id": 2,
                        "title": "삼성전자, 3나노 공정...",
                        "similarity": 0.95,
                        "price_changes": {
                            "day1": 2.5,
                            "day2": 3.8,
                            "day3": 5.3,
                            "day5": 7.8,
                            "day10": 10.2,
                            "day20": 12.5,
                        },
                    }
                ],
                "cached": False,
                "model": "gpt-4o",
                "timestamp": "2025-11-01T14:00:00",
            }
        }


# === 의존성 ===


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === API 엔드포인트 ===


@router.post("/predict", response_model=PredictionResponse)
async def predict_stock_price(
    request: PredictionRequest,
    db: Session = Depends(get_db),
):
    """
    뉴스 기반 주가 예측

    유사한 과거 뉴스의 주가 변동 패턴을 분석하여 현재 뉴스가 주가에 미칠 영향을 예측합니다.

    **처리 흐름:**
    1. 뉴스 ID로 뉴스 조회
    2. 뉴스 임베딩 → Milvus 유사 뉴스 검색
    3. 유사 뉴스의 주가 변동률 조회 (PostgreSQL)
    4. GPT-4 기반 주가 예측 (캐시 활용)

    **예측 방향:**
    - `상승`: 주가 상승 예상
    - `하락`: 주가 하락 예상
    - `유지`: 주가 횡보 예상

    **신뢰도:**
    - 0 ~ 100: 예측 신뢰도 (유사 뉴스 개수, 패턴 일관성 등 고려)
    """
    try:
        # 1. 뉴스 조회
        news = db.query(NewsArticle).filter(NewsArticle.id == request.news_id).first()

        if not news:
            raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

        # 종목 코드 결정 (요청 > 뉴스 > 오류)
        stock_code = request.stock_code or news.stock_code
        if not stock_code:
            raise HTTPException(
                status_code=400, detail="종목 코드가 지정되지 않았습니다"
            )

        logger.info(
            f"예측 요청: news_id={request.news_id}, stock_code={stock_code}"
        )

        # 2. 유사 뉴스 검색
        vector_search = get_vector_search()
        news_text = f"{news.title}\n{news.content}"

        similar_news = vector_search.get_news_with_price_changes(
            news_text=news_text,
            stock_code=stock_code,
            db=db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        logger.info(f"유사 뉴스 {len(similar_news)}건 발견")

        # 3. LLM 예측
        predictor = get_predictor()
        current_news_data = {
            "title": news.title,
            "content": news.content,
            "stock_code": stock_code,
        }

        prediction = predictor.predict(
            current_news=current_news_data,
            similar_news=similar_news,
            news_id=request.news_id,
            use_cache=request.use_cache,
        )

        logger.info(
            f"예측 완료: {prediction['prediction']} (신뢰도: {prediction['confidence']}%)"
        )

        # 4. 응답 생성
        similar_news_response = [
            SimilarNews(
                news_id=sn["news_id"],
                title=sn["news_title"],
                similarity=sn["similarity"],
                price_changes=PriceChange(
                    day1=sn["price_changes"].get("1d"),
                    day2=sn["price_changes"].get("2d"),
                    day3=sn["price_changes"].get("3d"),
                    day5=sn["price_changes"].get("5d"),
                    day10=sn["price_changes"].get("10d"),
                    day20=sn["price_changes"].get("20d"),
                ),
            )
            for sn in similar_news
        ]

        # Phase 2: 신뢰도 breakdown
        confidence_breakdown_data = prediction.get("confidence_breakdown")
        confidence_breakdown_response = None
        if confidence_breakdown_data:
            confidence_breakdown_response = ConfidenceBreakdown(
                similar_news_quality=confidence_breakdown_data.get("similar_news_quality"),
                pattern_consistency=confidence_breakdown_data.get("pattern_consistency"),
                disclosure_impact=confidence_breakdown_data.get("disclosure_impact"),
                explanation=confidence_breakdown_data.get("explanation"),
            )

        # Phase 2: 패턴 분석
        pattern_analysis_data = prediction.get("pattern_analysis")
        pattern_analysis_response = None
        if pattern_analysis_data:
            pattern_analysis_response = PatternAnalysis(
                avg_1d=pattern_analysis_data.get("avg_1d"),
                avg_2d=pattern_analysis_data.get("avg_2d"),
                avg_3d=pattern_analysis_data.get("avg_3d"),
                avg_5d=pattern_analysis_data.get("avg_5d"),
                avg_10d=pattern_analysis_data.get("avg_10d"),
                avg_20d=pattern_analysis_data.get("avg_20d"),
                max_1d=pattern_analysis_data.get("max_1d"),
                min_1d=pattern_analysis_data.get("min_1d"),
                count=pattern_analysis_data.get("count"),
            )

        return PredictionResponse(
            prediction=prediction["prediction"],
            confidence=prediction["confidence"],
            reasoning=prediction["reasoning"],
            short_term=prediction["short_term"],
            medium_term=prediction["medium_term"],
            long_term=prediction["long_term"],
            confidence_breakdown=confidence_breakdown_response,
            pattern_analysis=pattern_analysis_response,
            similar_news=similar_news_response,
            cached=prediction.get("cached", False),
            model=prediction["model"],
            timestamp=prediction["timestamp"],
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"예측 API 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")


@router.get("/predict/cache/stats")
async def get_cache_stats():
    """
    예측 캐시 통계 조회

    캐시 히트율, 사용량 등의 통계 정보를 반환합니다.
    """
    try:
        from backend.llm.prediction_cache import get_prediction_cache

        cache = get_prediction_cache()
        stats = cache.get_stats()
        hit_rate = cache.get_hit_rate()

        return {
            "stats": stats,
            "hit_rate": hit_rate,
            "hit_rate_percent": f"{hit_rate:.1%}",
        }

    except Exception as e:
        logger.error(f"캐시 통계 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"통계 조회 실패: {str(e)}")


@router.get("/predict/{news_id}", response_model=PredictionResponse)
async def get_prediction_by_news_id(
    news_id: int,
    db: Session = Depends(get_db),
):
    """
    뉴스 ID로 예측 결과 조회

    특정 뉴스의 저장된 예측 결과를 반환합니다. 예측이 없으면 새로 수행합니다.
    """
    try:
        # 1. 뉴스 조회
        news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()

        if not news:
            raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

        if not news.stock_code:
            raise HTTPException(status_code=400, detail="종목 코드가 없는 뉴스입니다")

        logger.info(f"예측 조회 요청: news_id={news_id}, stock_code={news.stock_code}")

        # 2. 유사 뉴스 검색
        vector_search = get_vector_search()
        news_text = f"{news.title}\n{news.content}"

        similar_news = vector_search.get_news_with_price_changes(
            news_text=news_text,
            stock_code=news.stock_code,
            db=db,
            top_k=5,
            similarity_threshold=0.5,
        )

        logger.info(f"유사 뉴스 {len(similar_news)}건 발견")

        # 3. LLM 예측 (캐시 사용)
        predictor = get_predictor()
        current_news_data = {
            "title": news.title,
            "content": news.content,
            "stock_code": news.stock_code,
        }

        prediction = predictor.predict(
            current_news=current_news_data,
            similar_news=similar_news,
            news_id=news_id,
            use_cache=True,  # 캐시 사용
        )

        logger.info(
            f"예측 조회 완료: {prediction['prediction']} (신뢰도: {prediction['confidence']}%)"
        )

        # 4. 응답 생성
        similar_news_response = [
            SimilarNews(
                news_id=sn["news_id"],
                title=sn["news_title"],
                similarity=sn["similarity"],
                price_changes=PriceChange(
                    day1=sn["price_changes"].get("1d"),
                    day2=sn["price_changes"].get("2d"),
                    day3=sn["price_changes"].get("3d"),
                    day5=sn["price_changes"].get("5d"),
                    day10=sn["price_changes"].get("10d"),
                    day20=sn["price_changes"].get("20d"),
                ),
            )
            for sn in similar_news
        ]

        # Phase 2: 신뢰도 breakdown
        confidence_breakdown_data = prediction.get("confidence_breakdown")
        confidence_breakdown_response = None
        if confidence_breakdown_data:
            confidence_breakdown_response = ConfidenceBreakdown(
                similar_news_quality=confidence_breakdown_data.get("similar_news_quality"),
                pattern_consistency=confidence_breakdown_data.get("pattern_consistency"),
                disclosure_impact=confidence_breakdown_data.get("disclosure_impact"),
                explanation=confidence_breakdown_data.get("explanation"),
            )

        # Phase 2: 패턴 분석
        pattern_analysis_data = prediction.get("pattern_analysis")
        pattern_analysis_response = None
        if pattern_analysis_data:
            pattern_analysis_response = PatternAnalysis(
                avg_1d=pattern_analysis_data.get("avg_1d"),
                avg_2d=pattern_analysis_data.get("avg_2d"),
                avg_3d=pattern_analysis_data.get("avg_3d"),
                avg_5d=pattern_analysis_data.get("avg_5d"),
                avg_10d=pattern_analysis_data.get("avg_10d"),
                avg_20d=pattern_analysis_data.get("avg_20d"),
                max_1d=pattern_analysis_data.get("max_1d"),
                min_1d=pattern_analysis_data.get("min_1d"),
                count=pattern_analysis_data.get("count"),
            )

        return PredictionResponse(
            prediction=prediction["prediction"],
            confidence=prediction["confidence"],
            reasoning=prediction["reasoning"],
            short_term=prediction["short_term"],
            medium_term=prediction["medium_term"],
            long_term=prediction["long_term"],
            confidence_breakdown=confidence_breakdown_response,
            pattern_analysis=pattern_analysis_response,
            similar_news=similar_news_response,
            cached=prediction.get("cached", False),
            model=prediction["model"],
            timestamp=prediction["timestamp"],
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"예측 조회 API 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"예측 조회 실패: {str(e)}")


@router.delete("/predict/cache")
async def clear_cache():
    """
    예측 캐시 전체 삭제

    모든 캐시된 예측 결과를 삭제합니다. (관리용 엔드포인트)
    """
    try:
        from backend.llm.prediction_cache import get_prediction_cache

        cache = get_prediction_cache()
        deleted_count = cache.clear_all()

        return {
            "message": "캐시 전체 삭제 완료",
            "deleted_count": deleted_count,
        }

    except Exception as e:
        logger.error(f"캐시 삭제 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"캐시 삭제 실패: {str(e)}")
