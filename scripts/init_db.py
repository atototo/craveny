"""
PostgreSQL 데이터베이스 초기화 스크립트
테이블 생성 및 기본 데이터 설정
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings
from backend.db.base import Base
from backend.db.models import NewsArticle, StockPrice, NewsStockMatch, TelegramUser
from backend.db.session import engine


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
        # 테이블 생성
        print(f"\n📋 테이블 생성 중...")
        Base.metadata.create_all(engine)

        print(f"   ✅ news_articles (뉴스 기사)")
        print(f"   ✅ stock_prices (주가 데이터)")
        print(f"   ✅ news_stock_matches (뉴스-주가 매칭)")
        print(f"   ✅ telegram_users (텔레그램 사용자)")

        # 연결 테스트
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        result = session.execute("SELECT 1")
        session.close()

        print(f"\n✅ 데이터베이스 초기화 완료!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 데이터베이스 초기화 실패: {e}")
        print("   에러 상세: {type(e).__name__}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
