"""
관리자 계정 추가 스크립트 (기존 데이터 유지).

이미 존재하는 users 테이블에 관리자 계정만 추가합니다.
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from passlib.context import CryptContext
from dotenv import load_dotenv

from backend.db.models.user import User
from backend.db.session import SessionLocal

# 환경 변수 로드
load_dotenv()

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def add_admin_user():
    """관리자 계정 추가 (이미 존재하면 스킵)."""
    admin_email = "admin@craveny.com"

    db = SessionLocal()
    try:
        # 이미 존재하는지 확인
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if existing_admin:
            print(f"✅ 관리자 계정 '{admin_email}'이 이미 존재합니다.")
            print(f"   - 이메일: {existing_admin.email}")
            print(f"   - 닉네임: {existing_admin.nickname}")
            print(f"   - 역할: {existing_admin.role}")
            return

        # 환경 변수에서 비밀번호 로드
        admin_password = os.getenv("ADMIN_DEFAULT_PASSWORD")
        if not admin_password:
            print("⚠️  경고: ADMIN_DEFAULT_PASSWORD 환경 변수가 설정되지 않았습니다.")
            print("   기본값 'admin123'을 사용합니다.")
            admin_password = "admin123"

        # 비밀번호 해싱
        password_hash = pwd_context.hash(admin_password)

        # 관리자 계정 생성
        admin_user = User(
            email=admin_email,
            nickname="관리자",
            password_hash=password_hash,
            role="admin",
            is_active=True
        )

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        print("=" * 60)
        print("✅ 기본 관리자 계정 생성 완료!")
        print("=" * 60)
        print(f"   - 이메일: {admin_email}")
        print(f"   - 비밀번호: {admin_password}")
        print(f"   - 역할: admin")
        print()
        print("⚠️  보안 주의: 최초 로그인 후 반드시 비밀번호를 변경하세요!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 오류 발생: {e}")
        print("=" * 60)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🔐 관리자 계정 추가")
    print("=" * 60)
    print()
    add_admin_user()
