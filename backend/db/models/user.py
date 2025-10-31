"""
TelegramUser model for storing telegram bot subscribers.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.db.base import Base


class TelegramUser(Base):
    """
    텔레그램 사용자 모델.

    Attributes:
        id: Primary key
        user_id: 텔레그램 사용자 ID (고유값)
        subscribed_at: 구독 시작 시간
        is_active: 활성화 상태
    """

    __tablename__ = "telegram_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), unique=True, nullable=False)
    subscribed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<TelegramUser(id={self.id}, user_id='{self.user_id}', "
            f"is_active={self.is_active})>"
        )
