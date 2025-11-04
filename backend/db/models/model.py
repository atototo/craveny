"""
Model configuration for dynamic A/B testing.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from backend.db.base import Base


class Model(Base):
    """
    LLM 모델 설정 테이블.

    Attributes:
        id: Primary key
        name: 모델 표시 이름 (예: "GPT-4o", "DeepSeek V3.2")
        provider: 모델 제공자 (예: "openai", "openrouter")
        model_identifier: 실제 모델 식별자 (예: "gpt-4o", "deepseek/deepseek-v3.2-exp")
        is_active: 활성화 상태
        description: 모델 설명
        created_at: 생성 일시
    """

    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    provider = Column(String(50), nullable=False)  # "openai", "openrouter"
    model_identifier = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Model(id={self.id}, name='{self.name}', "
            f"provider='{self.provider}', is_active={self.is_active})>"
        )
