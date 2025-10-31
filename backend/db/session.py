"""
Database session management for SQLAlchemy.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings


# SQLAlchemy Engine 생성
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 연결 유효성 검사
    echo=False,  # SQL 로깅 비활성화 (프로덕션)
    pool_size=5,  # 연결 풀 크기
    max_overflow=10,  # 최대 초과 연결
)

# SessionLocal 팩토리
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.

    Yields:
        Session: SQLAlchemy database session

    Example:
        @app.get("/news")
        def get_news(db: Session = Depends(get_db)):
            return db.query(NewsArticle).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
