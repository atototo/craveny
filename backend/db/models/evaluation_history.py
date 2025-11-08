"""
Evaluation modification history for audit trail.
"""
from sqlalchemy import Column, Integer, Float, DateTime, Text, Index
from datetime import datetime
from backend.db.base import Base


class EvaluationHistory(Base):
    """
    평가 수정 이력 테이블.

    사람 평가 수정 시 감사 추적을 위해 기록합니다.
    """
    __tablename__ = "evaluation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    evaluation_id = Column(Integer, nullable=False, index=True)

    # 수정 전 값
    old_human_rating_quality = Column(Integer, nullable=True)
    old_human_rating_usefulness = Column(Integer, nullable=True)
    old_human_rating_overall = Column(Integer, nullable=True)
    old_final_score = Column(Float, nullable=True)

    # 수정 후 값
    new_human_rating_quality = Column(Integer, nullable=True)
    new_human_rating_usefulness = Column(Integer, nullable=True)
    new_human_rating_overall = Column(Integer, nullable=True)
    new_final_score = Column(Float, nullable=True)

    # 메타데이터
    modified_by = Column(Text, nullable=False)
    modified_at = Column(DateTime, default=datetime.now, nullable=False)
    reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_eval_history_eval_id", "evaluation_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<EvaluationHistory(id={self.id}, "
            f"evaluation_id={self.evaluation_id}, "
            f"modified_by={self.modified_by})>"
        )
