"""
Prediction model for storing stock prediction results.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, JSON
from datetime import datetime
from backend.db.base import Base


class Prediction(Base):
    """
    주가 예측 결과 모델.

    Attributes:
        id: Primary key
        news_id: 뉴스 ID (외래키)
        stock_code: 종목 코드
        direction: 예측 방향 (up, down, hold)
        confidence: 예측 신뢰도 (0.0~1.0)
        reasoning: 예측 근거
        current_price: 예측 시점 현재가
        target_period: 예측 기간 (예: "1일", "1주일")
        created_at: 예측 생성일시

        # Phase 2 필드
        short_term: 단기 예측 (T+1일)
        medium_term: 중기 예측 (T+3일)
        long_term: 장기 예측 (T+5일)
        confidence_breakdown: 신뢰도 구성 요소 (JSON)
        pattern_analysis: 패턴 분석 통계 (JSON)
    """

    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    stock_code = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # up, down, hold
    confidence = Column(Float, nullable=False)  # 0.0 ~ 1.0
    reasoning = Column(Text, nullable=True)
    current_price = Column(Float, nullable=True)
    target_period = Column(String(20), default="1일", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Phase 2: 기간별 예측
    short_term = Column(Text, nullable=True)  # T+1일 예측
    medium_term = Column(Text, nullable=True)  # T+3일 예측
    long_term = Column(Text, nullable=True)  # T+5일 예측

    # Phase 2: 신뢰도 구성 요소 (JSON)
    confidence_breakdown = Column(JSON, nullable=True)

    # Phase 2: 패턴 분석 통계 (JSON)
    pattern_analysis = Column(JSON, nullable=True)

    # 인덱스
    __table_args__ = (
        Index("idx_predictions_stock_code_created", "stock_code", "created_at"),
        Index("idx_predictions_news_id", "news_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, stock_code='{self.stock_code}', "
            f"direction='{self.direction}', confidence={self.confidence})>"
        )
