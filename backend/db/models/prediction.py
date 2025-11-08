"""
Prediction model for storing stock prediction results.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db.base import Base


class Prediction(Base):
    """
    뉴스 영향도 분석 결과 모델.

    Attributes:
        id: Primary key
        news_id: 뉴스 ID (외래키)
        model_id: 모델 ID (외래키, 멀티모델 지원)
        stock_code: 종목 코드

        # 영향도 분석 필드 (v2.0)
        sentiment_direction: 감성 방향 (positive, negative, neutral)
        sentiment_score: 감성 점수 (-1.0 ~ 1.0, 매우 부정 ~ 매우 긍정)
        impact_level: 영향도 등급 (low, medium, high, critical)
        relevance_score: 관련성 점수 (0.0 ~ 1.0, 무관 ~ 직접 관련)
        urgency_level: 긴급도 (routine, notable, urgent, breaking)
        impact_analysis: 상세 영향도 분석 (JSON)

        # 기존 필드 (유지)
        reasoning: 영향도 분석 근거
        current_price: 분석 시점 현재가
        target_period: 분석 기간 (예: "1일~1주")
        created_at: 분석 생성일시
        pattern_analysis: 패턴 분석 통계 (JSON, 읽기 전용)

        # DEPRECATED 필드 (v2.0에서 제거 예정)
        direction: [DEPRECATED] 예측 방향 (→ sentiment_direction 사용)
        confidence: [DEPRECATED] 예측 신뢰도 (→ sentiment_score, impact_level 사용)
        short_term: [DEPRECATED] 단기 예측 (→ Investment Report에서 처리)
        medium_term: [DEPRECATED] 중기 예측 (→ Investment Report에서 처리)
        long_term: [DEPRECATED] 장기 예측 (→ Investment Report에서 처리)
        confidence_breakdown: [DEPRECATED] 신뢰도 구성 요소 (→ impact_analysis 사용)
    """

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    model_id = Column(Integer, nullable=False, index=True)  # FK 제거, 인덱스 유지
    stock_code = Column(String(10), nullable=False, index=True)

    # 영향도 분석 필드 (v2.0)
    sentiment_direction = Column(String(10), nullable=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # -1.0 ~ 1.0
    impact_level = Column(String(20), nullable=True)  # low, medium, high, critical
    relevance_score = Column(Float, nullable=True)  # 0.0 ~ 1.0
    urgency_level = Column(String(20), nullable=True)  # routine, notable, urgent, breaking
    impact_analysis = Column(JSON, nullable=True)  # 상세 영향도 분석

    # 기존 필드 (유지)
    reasoning = Column(Text, nullable=True)
    current_price = Column(Float, nullable=True)
    target_period = Column(String(20), default="1일~1주", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    pattern_analysis = Column(JSON, nullable=True)  # 패턴 분석 통계 (읽기 전용)

    # DEPRECATED: Will be removed in v2.0
    # Use sentiment_direction instead
    direction = Column(String(10), nullable=True)  # up, down, hold

    # DEPRECATED: Will be removed in v2.0
    # Use sentiment_score and impact_level instead
    confidence = Column(Float, nullable=True)  # 0.0 ~ 1.0

    # DEPRECATED: Will be removed in v2.0
    # Price prediction moved to Investment Report
    short_term = Column(Text, nullable=True)  # T+1일 예측
    medium_term = Column(Text, nullable=True)  # T+3일 예측
    long_term = Column(Text, nullable=True)  # T+5일 예측

    # DEPRECATED: Will be removed in v2.0
    # Use impact_analysis instead
    confidence_breakdown = Column(JSON, nullable=True)

    # 관계 (lazy import로 Model 클래스 참조)
    # model = relationship("Model", backref="predictions")

    # 인덱스
    __table_args__ = (
        Index("idx_predictions_stock_code_created", "stock_code", "created_at"),
        Index("idx_predictions_news_id", "news_id"),
        Index("idx_predictions_model_id", "model_id"),
        Index("idx_predictions_news_model", "news_id", "model_id"),
    )

    def __repr__(self) -> str:
        # Use new fields if available, fallback to deprecated fields
        direction = self.sentiment_direction or self.direction
        score = self.sentiment_score if self.sentiment_score is not None else self.confidence
        return (
            f"<Prediction(id={self.id}, stock_code='{self.stock_code}', "
            f"sentiment_direction='{direction}', sentiment_score={score}, "
            f"impact_level='{self.impact_level}')>"
        )
