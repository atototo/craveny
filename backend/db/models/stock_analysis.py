"""
Stock Analysis Summary model for caching AI-generated investment reports.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from datetime import datetime
from backend.db.base import Base


class StockAnalysisSummary(Base):
    """
    종목별 AI 투자 분석 요약 (캐시)

    Attributes:
        id: Primary key
        stock_code: 종목 코드

        # LLM 생성 콘텐츠
        overall_summary: 종합 의견
        short_term_scenario: 단기 투자 시나리오
        medium_term_scenario: 중기 투자 시나리오
        long_term_scenario: 장기 투자 시나리오
        risk_factors: 리스크 요인 리스트
        opportunity_factors: 기회 요인 리스트
        recommendation: 최종 추천

        # 통계 (규칙 기반)
        total_predictions: 총 예측 건수
        up_count: 상승 예측 건수
        down_count: 하락 예측 건수
        hold_count: 보합 예측 건수
        avg_confidence: 평균 신뢰도

        # 메타 정보
        last_updated: 마지막 업데이트 시각
        based_on_prediction_count: 분석에 사용된 예측 건수
    """

    __tablename__ = "stock_analysis_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), unique=True, nullable=False, index=True)

    # LLM 생성 콘텐츠
    overall_summary = Column(Text, nullable=True)
    short_term_scenario = Column(Text, nullable=True)
    medium_term_scenario = Column(Text, nullable=True)
    long_term_scenario = Column(Text, nullable=True)
    risk_factors = Column(JSON, nullable=True)  # ["리스크1", "리스크2", ...]
    opportunity_factors = Column(JSON, nullable=True)  # ["기회1", "기회2", ...]
    recommendation = Column(Text, nullable=True)

    # 통계 데이터
    total_predictions = Column(Integer, default=0)
    up_count = Column(Integer, default=0)
    down_count = Column(Integer, default=0)
    hold_count = Column(Integer, default=0)
    avg_confidence = Column(Float, nullable=True)

    # A/B 테스트용 전체 리포트 JSON 저장
    custom_data = Column(JSON, nullable=True)

    # 메타 정보
    last_updated = Column(DateTime, default=datetime.now, nullable=False)
    based_on_prediction_count = Column(Integer, default=0)

    def __repr__(self) -> str:
        return (
            f"<StockAnalysisSummary(stock_code='{self.stock_code}', "
            f"total_predictions={self.total_predictions}, "
            f"last_updated='{self.last_updated}')>"
        )
