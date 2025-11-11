"""
User models for authentication and telegram bot subscribers.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index
from backend.db.base import Base


class User(Base):
    """
    사용자 인증 모델 (로그인 사용자).

    Attributes:
        id: Primary key
        email: 이메일 (고유값, 로그인 ID)
        nickname: 닉네임
        password_hash: bcrypt 해시된 비밀번호
        role: 사용자 역할 ('user' | 'admin')
        is_active: 활성화 상태
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    nickname = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user", index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, email='{self.email}', "
            f"nickname='{self.nickname}', role='{self.role}')>"
        )


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
