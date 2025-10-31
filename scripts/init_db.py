"""
PostgreSQL 데이터베이스 초기화 스크립트
테이블 생성 및 기본 데이터 설정
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from backend.config import settings

Base = declarative_base()


# 테이블 정의
class NewsArticle(Base):
    """뉴스 기사 테이블"""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(100), nullable=False)
    published_at = Column(DateTime, nullable=False)
    stock_code = Column(String(10), nullable=True, index=True)
    collected_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Prediction(Base):
    """예측 결과 테이블"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_article_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False, index=True)
    predicted_direction = Column(String(10), nullable=False)  # UP, DOWN, NEUTRAL
    confidence_score = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Notification(Base):
    """텔레그램 알림 테이블"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    stock_code = Column(String(10), nullable=False)
    message_content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class StockPrice(Base):
    """주가 데이터 테이블"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)


class TelegramSubscription(Base):
    """텔레그램 구독 정보 테이블"""
    __tablename__ = "telegram_subscriptions"

    user_id = Column(String(50), primary_key=True)
    chat_id = Column(String(50), nullable=False)
    subscribed_stocks = Column(JSON, nullable=True)  # List of stock codes
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


def init_database():
    """데이터베이스 초기화 함수"""
    print("=" * 60)
    print("🗄️  PostgreSQL 데이터베이스 초기화 시작")
    print("=" * 60)

    # 데이터베이스 연결
    print(f"\n📡 데이터베이스 연결 중...")
    print(f"   호스트: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    print(f"   데이터베이스: {settings.POSTGRES_DB}")

    try:
        engine = create_engine(settings.DATABASE_URL)

        # 테이블 생성
        print(f"\n📋 테이블 생성 중...")
        Base.metadata.create_all(engine)

        print(f"   ✅ news_articles")
        print(f"   ✅ predictions")
        print(f"   ✅ notifications")
        print(f"   ✅ stock_prices")
        print(f"   ✅ telegram_subscriptions")

        # 연결 테스트
        Session = sessionmaker(bind=engine)
        session = Session()
        session.execute("SELECT 1")
        session.close()

        print(f"\n✅ 데이터베이스 초기화 완료!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 데이터베이스 초기화 실패: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
