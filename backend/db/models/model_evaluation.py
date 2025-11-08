"""
Model evaluation tracking for daily performance assessment.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from datetime import datetime
from backend.db.base import Base


class ModelEvaluation(Base):
    """
    모델 예측 평가 테이블.

    매일 장마감 후 자동으로 생성되며, 예측의 정확도를 추적합니다.

    Attributes:
        id: Primary key
        prediction_id: 평가 대상 예측 ID
        model_id: 모델 ID
        stock_code: 종목 코드

        # 예측 정보 (스냅샷)
        predicted_at: 예측 생성 일시
        prediction_period: 예측 기간 ("1일~1주", "1일~5일")
        predicted_target_price: 목표가
        predicted_support_price: 손절가 (지지선)
        predicted_base_price: 기준가 (예측 시점 가격)
        predicted_confidence: 신뢰도

        # 실제 결과 (자동 수집)
        actual_high_1d: 1일 후 최고가
        actual_low_1d: 1일 후 최저가
        actual_close_1d: 1일 후 종가

        actual_high_5d: 5일 후 최고가
        actual_low_5d: 5일 후 최저가
        actual_close_5d: 5일 후 종가

        target_achieved: 목표가 달성 여부
        target_achieved_days: 며칠만에 달성 (미달성 시 null)
        support_breached: 손절가 이탈 여부

        # 정확도 점수 (자동 계산, 0~100점)
        target_accuracy_score: 목표가 정확도 점수
        timing_score: 타이밍 점수
        risk_management_score: 리스크 관리 점수

        # 사람 평가 (수동 입력, 1~5점)
        human_rating_quality: 분석 품질 점수
        human_rating_usefulness: 실용성 점수
        human_rating_overall: 종합 만족도 점수
        human_evaluated_by: 평가자 이름
        human_evaluated_at: 사람 평가 일시

        # 종합
        final_score: 최종 점수 (자동 70% + 사람 30%)
        evaluated_at: 평가 일시
        created_at: 레코드 생성 일시
    """

    __tablename__ = "model_evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_id = Column(Integer, nullable=False, index=True)
    model_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False, index=True)

    # 예측 정보 (스냅샷)
    predicted_at = Column(DateTime, nullable=False)
    prediction_period = Column(String(20), nullable=True)  # "1일~1주"
    predicted_target_price = Column(Float, nullable=True)
    predicted_support_price = Column(Float, nullable=True)
    predicted_base_price = Column(Float, nullable=False)
    predicted_confidence = Column(Float, nullable=True)

    # 실제 결과 (1일)
    actual_high_1d = Column(Float, nullable=True)
    actual_low_1d = Column(Float, nullable=True)
    actual_close_1d = Column(Float, nullable=True)

    # 실제 결과 (5일)
    actual_high_5d = Column(Float, nullable=True)
    actual_low_5d = Column(Float, nullable=True)
    actual_close_5d = Column(Float, nullable=True)

    # 달성 여부
    target_achieved = Column(Boolean, nullable=True)
    target_achieved_days = Column(Integer, nullable=True)
    support_breached = Column(Boolean, nullable=True)

    # 자동 점수 (0~100)
    target_accuracy_score = Column(Float, nullable=True)
    timing_score = Column(Float, nullable=True)
    risk_management_score = Column(Float, nullable=True)

    # 사람 평가 (1~5점)
    human_rating_quality = Column(Integer, nullable=True)
    human_rating_usefulness = Column(Integer, nullable=True)
    human_rating_overall = Column(Integer, nullable=True)
    human_evaluated_by = Column(String(50), nullable=True)
    human_evaluated_at = Column(DateTime, nullable=True)

    # 종합
    final_score = Column(Float, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 복합 인덱스
    __table_args__ = (
        Index("ix_model_eval_model_date", "model_id", "predicted_at"),
        Index("ix_model_eval_stock_date", "stock_code", "predicted_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ModelEvaluation(id={self.id}, "
            f"model_id={self.model_id}, stock_code={self.stock_code}, "
            f"final_score={self.final_score})>"
        )
