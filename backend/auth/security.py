"""
인증 및 보안 유틸리티.

비밀번호 해싱, 세션 관리, 사용자 검증 등의 기능을 제공합니다.
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models.user import User

# 비밀번호 해싱 컨텍스트 (bcrypt, cost factor: 10)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱합니다.

    Args:
        password: 평문 비밀번호

    Returns:
        str: 해시된 비밀번호
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호가 해시와 일치하는지 검증합니다.

    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해시된 비밀번호

    Returns:
        bool: 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int, email: str, role: str) -> str:
    """
    사용자 세션 토큰을 생성합니다 (JWT).

    Args:
        user_id: 사용자 ID
        email: 사용자 이메일
        role: 사용자 역할

    Returns:
        str: JWT 토큰
    """
    expire = datetime.utcnow() + timedelta(seconds=settings.SESSION_MAX_AGE)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_session_token(token: str) -> Optional[dict]:
    """
    세션 토큰을 검증하고 페이로드를 반환합니다.

    Args:
        token: JWT 토큰

    Returns:
        dict | None: 페이로드 (실패 시 None)
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    이메일과 비밀번호로 사용자를 인증합니다.

    Args:
        db: 데이터베이스 세션
        email: 사용자 이메일
        password: 평문 비밀번호

    Returns:
        User | None: 인증된 사용자 객체 (실패 시 None)
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    사용자 ID로 사용자를 조회합니다.

    Args:
        db: 데이터베이스 세션
        user_id: 사용자 ID

    Returns:
        User | None: 사용자 객체 (없으면 None)
    """
    return db.query(User).filter(User.id == user_id, User.is_active == True).first()
