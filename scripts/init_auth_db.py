"""
사용자 인증 데이터베이스 초기화 스크립트.

Users 테이블을 생성하고 기본 관리자 계정을 추가합니다.
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect
from passlib.context import CryptContext
from dotenv import load_dotenv

from backend.db.base import Base
from backend.db.models.user import User
from backend.db.session import SessionLocal

# 환경 변수 로드
load_dotenv()

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_database_url() -> str:
    """환경 변수에서 데이터베이스 URL 생성."""
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    db_name = os.getenv("POSTGRES_DB", "craveny")

    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def create_tables(engine):
    """Users 테이블 생성 (이미 존재하면 스킵)."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if "users" in existing_tables:
        print("✅ 'users' 테이블이 이미 존재합니다.")
    else:
        print("📋 'users' 테이블을 생성합니다...")
        Base.metadata.create_all(bind=engine, tables=[User.__table__])
        print("✅ 'users' 테이블 생성 완료!")


def create_admin_user(db: SessionLocal):
    """기본 관리자 계정 생성 (이미 존재하면 스킵)."""
    admin_email = "admin@craveny.com"

    # 이미 존재하는지 확인
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin:
        print(f"✅ 관리자 계정 '{admin_email}'이 이미 존재합니다.")
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

    print(f"✅ 기본 관리자 계정 생성 완료!")
    print(f"   - 이메일: {admin_email}")
    print(f"   - 비밀번호: {admin_password}")
    print(f"   - 역할: admin")
    print(f"\n⚠️  보안 주의: 최초 로그인 후 반드시 비밀번호를 변경하세요!")


def main():
    """메인 실행 함수."""
    print("=" * 60)
    print("🔐 Craveny 사용자 인증 데이터베이스 초기화")
    print("=" * 60)
    print()

    try:
        # 데이터베이스 연결
        database_url = get_database_url()
        print(f"📡 데이터베이스 연결 중... ({database_url.split('@')[1]})")
        engine = create_engine(database_url)

        # 연결 테스트
        with engine.connect() as conn:
            print("✅ 데이터베이스 연결 성공!")

        print()

        # 테이블 생성
        create_tables(engine)
        print()

        # 기본 관리자 계정 생성
        db = SessionLocal()
        try:
            create_admin_user(db)
        finally:
            db.close()

        print()
        print("=" * 60)
        print("✅ 초기화 완료!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 오류 발생: {e}")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
