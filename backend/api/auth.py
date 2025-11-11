"""
인증 관련 API 엔드포인트.

로그인, 로그아웃, 현재 사용자 조회 기능을 제공합니다.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from backend.db.session import get_db
from backend.db.models.user import User
from backend.auth.security import authenticate_user, create_session_token
from backend.auth.dependencies import get_current_user, require_auth
from backend.config import settings


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """로그인 요청 모델."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 정보 응답 모델."""
    id: int
    email: str
    nickname: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """로그인 응답 모델."""
    user: UserResponse
    message: str


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    사용자 로그인.

    Args:
        credentials: 이메일과 비밀번호
        response: FastAPI Response 객체 (쿠키 설정용)
        db: 데이터베이스 세션

    Returns:
        LoginResponse: 사용자 정보와 성공 메시지

    Raises:
        HTTPException: 401 (인증 실패)
    """
    # 사용자 인증
    user = authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다"
        )

    # 세션 토큰 생성
    session_token = create_session_token(user.id, user.email, user.role)

    # 세션 쿠키 설정
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_MAX_AGE,
        httponly=True,  # JavaScript 접근 차단
        samesite="lax",  # CSRF 방어
        secure=False  # 개발 환경: False, 프로덕션: True (HTTPS 필요)
    )

    return LoginResponse(
        user=UserResponse.from_orm(user),
        message="로그인 성공"
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(response: Response):
    """
    사용자 로그아웃.

    세션 쿠키를 삭제하여 로그아웃 처리합니다.

    Args:
        response: FastAPI Response 객체 (쿠키 삭제용)

    Returns:
        dict: 성공 메시지
    """
    # 세션 쿠키 삭제
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax"
    )

    return {"message": "로그아웃 성공"}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: User = Depends(require_auth)
):
    """
    현재 로그인된 사용자 정보 조회.

    Args:
        current_user: 현재 인증된 사용자 (의존성 주입)

    Returns:
        UserResponse: 사용자 정보

    Raises:
        HTTPException: 401 (인증 필요)
    """
    return UserResponse.from_orm(current_user)


@router.get("/check", status_code=status.HTTP_200_OK)
async def check_auth(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    인증 상태 확인 (선택적).

    로그인 여부를 확인하며, 비로그인 시에도 에러를 반환하지 않습니다.

    Args:
        current_user: 현재 사용자 (없으면 None)
        db: 데이터베이스 세션

    Returns:
        dict: 인증 상태와 사용자 정보
    """
    if current_user:
        return {
            "authenticated": True,
            "user": UserResponse.from_orm(current_user)
        }
    else:
        return {
            "authenticated": False,
            "user": None
        }
