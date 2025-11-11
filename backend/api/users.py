"""
사용자 관리 API 엔드포인트 (관리자 전용).

사용자 CRUD 작업을 제공합니다.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator

from backend.db.session import get_db
from backend.db.models.user import User
from backend.auth.dependencies import require_admin
from backend.auth.security import hash_password


router = APIRouter(prefix="/api/users", tags=["User Management"])


# Request/Response Models
class UserCreate(BaseModel):
    """사용자 생성 요청 모델."""
    email: EmailStr
    nickname: str
    password: str
    role: str = "user"

    @validator("password")
    def validate_password(cls, v):
        """비밀번호 검증 (8자 이상)."""
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다")
        return v

    @validator("role")
    def validate_role(cls, v):
        """역할 검증 (user 또는 admin)."""
        if v not in ["user", "admin"]:
            raise ValueError("역할은 'user' 또는 'admin'이어야 합니다")
        return v


class UserUpdate(BaseModel):
    """사용자 수정 요청 모델."""
    nickname: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None

    @validator("password")
    def validate_password(cls, v):
        """비밀번호 검증 (8자 이상)."""
        if v is not None and len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다")
        return v

    @validator("role")
    def validate_role(cls, v):
        """역할 검증 (user 또는 admin)."""
        if v is not None and v not in ["user", "admin"]:
            raise ValueError("역할은 'user' 또는 'admin'이어야 합니다")
        return v


class UserResponse(BaseModel):
    """사용자 정보 응답 모델."""
    id: int
    email: str
    nickname: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[UserResponse], status_code=status.HTTP_200_OK)
async def list_users(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin)
):
    """
    사용자 목록 조회 (관리자 전용).

    Args:
        db: 데이터베이스 세션
        _current_user: 현재 관리자 사용자 (권한 체크용)

    Returns:
        List[UserResponse]: 사용자 목록
    """
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
        for user in users
    ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin)
):
    """
    사용자 생성 (관리자 전용).

    Args:
        user_data: 사용자 생성 데이터
        db: 데이터베이스 세션
        _current_user: 현재 관리자 사용자 (권한 체크용)

    Returns:
        UserResponse: 생성된 사용자 정보

    Raises:
        HTTPException: 409 (이메일 중복)
    """
    # 이메일 중복 체크
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다"
        )

    # 비밀번호 해싱
    password_hash = hash_password(user_data.password)

    # 사용자 생성
    new_user = User(
        email=user_data.email,
        nickname=user_data.nickname,
        password_hash=password_hash,
        role=user_data.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        nickname=new_user.nickname,
        role=new_user.role,
        is_active=new_user.is_active,
        created_at=new_user.created_at.isoformat(),
        updated_at=new_user.updated_at.isoformat(),
    )


@router.patch("/{user_id}", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_admin)
):
    """
    사용자 정보 수정 (관리자 전용).

    Args:
        user_id: 사용자 ID
        user_data: 수정할 사용자 데이터
        db: 데이터베이스 세션
        _current_user: 현재 관리자 사용자 (권한 체크용)

    Returns:
        UserResponse: 수정된 사용자 정보

    Raises:
        HTTPException: 404 (사용자 없음)
    """
    # 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 수정 가능한 필드만 업데이트
    if user_data.nickname is not None:
        user.nickname = user_data.nickname
    if user_data.password is not None:
        user.password_hash = hash_password(user_data.password)
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    사용자 삭제 (관리자 전용).

    Args:
        user_id: 사용자 ID
        db: 데이터베이스 세션
        current_user: 현재 관리자 사용자 (권한 체크용)

    Raises:
        HTTPException: 400 (자기 자신 삭제), 404 (사용자 없음)
    """
    # 자기 자신을 삭제하려는 경우 방지
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="자기 자신을 삭제할 수 없습니다"
        )

    # 사용자 조회
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )

    # 사용자 삭제
    db.delete(user)
    db.commit()

    return None
