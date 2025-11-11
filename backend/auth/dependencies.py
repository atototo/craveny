"""
FastAPI 인증 의존성.

미들웨어로 사용되는 인증 및 권한 체크 함수들을 제공합니다.
"""
from typing import Optional
from fastapi import Cookie, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.db.models.user import User
from backend.config import settings
from backend.auth.security import verify_session_token, get_user_by_id


def get_current_user(
    session_token: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    현재 로그인된 사용자를 반환합니다 (선택적).

    Args:
        session_token: 세션 쿠키 토큰
        db: 데이터베이스 세션

    Returns:
        User | None: 사용자 객체 (비로그인 시 None)
    """
    if not session_token:
        return None

    payload = verify_session_token(session_token)
    if not payload:
        return None

    user_id = int(payload.get("sub"))
    user = get_user_by_id(db, user_id)
    return user


def require_auth(
    session_token: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME),
    db: Session = Depends(get_db)
) -> User:
    """
    로그인이 필요한 엔드포인트에서 사용합니다.

    Args:
        session_token: 세션 쿠키 토큰
        db: 데이터베이스 세션

    Returns:
        User: 현재 로그인된 사용자

    Raises:
        HTTPException: 401 (인증 필요)
    """
    user = get_current_user(session_token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다"
        )
    return user


def require_admin(
    current_user: User = Depends(require_auth)
) -> User:
    """
    관리자 권한이 필요한 엔드포인트에서 사용합니다.

    Args:
        current_user: 현재 로그인된 사용자

    Returns:
        User: 관리자 사용자

    Raises:
        HTTPException: 403 (권한 없음)
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user
