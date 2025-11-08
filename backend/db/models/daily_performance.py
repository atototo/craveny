"""
Daily model performance aggregation.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Date, UniqueConstraint
from datetime import datetime
from backend.db.base import Base


class DailyModelPerformance(Base):
    """
    일일 모델 성능 집계 테이블.

    매일 17:00 배치 작업으로 업데이트됩니다.
    """
    __tablename__ = "daily_model_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # 건수
    total_predictions = Column(Integer, default=0, nullable=False)
    evaluated_count = Column(Integer, default=0, nullable=False)
    human_evaluated_count = Column(Integer, default=0, nullable=False)

    # 평균 점수
    avg_final_score = Column(Float, nullable=True)
    avg_auto_score = Column(Float, nullable=True)
    avg_human_score = Column(Float, nullable=True)
    avg_target_accuracy = Column(Float, nullable=True)
    avg_timing_score = Column(Float, nullable=True)
    avg_risk_management = Column(Float, nullable=True)

    # 성과 지표 (%)
    target_achieved_rate = Column(Float, nullable=True)
    support_breach_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (
        UniqueConstraint("model_id", "date", name="uq_model_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<DailyModelPerformance(id={self.id}, "
            f"model_id={self.model_id}, date={self.date}, "
            f"avg_final_score={self.avg_final_score})>"
        )
