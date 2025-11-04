"""
A/B Test configuration model.
"""
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.db.base import Base


class ABTestConfig(Base):
    """
    A/B 테스트 설정 테이블.

    Attributes:
        id: Primary key
        model_a_id: Model A 외래키
        model_b_id: Model B 외래키
        is_active: 활성화 상태 (시스템에서 단 하나만 is_active=true)
        created_at: 생성 일시
    """

    __tablename__ = "ab_test_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_a_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    model_b_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # Relationships
    model_a = relationship("Model", foreign_keys=[model_a_id])
    model_b = relationship("Model", foreign_keys=[model_b_id])

    def __repr__(self) -> str:
        return (
            f"<ABTestConfig(id={self.id}, "
            f"model_a_id={self.model_a_id}, model_b_id={self.model_b_id}, "
            f"is_active={self.is_active})>"
        )
