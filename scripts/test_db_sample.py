"""
데이터베이스 샘플 데이터 삽입 및 조회 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models import NewsArticle, StockPrice, NewsStockMatch, TelegramUser


def test_sample_data():
    """샘플 데이터 삽입 및 조회 테스트"""
    print("=" * 60)
    print("🧪 샘플 데이터 삽입 및 조회 테스트")
    print("=" * 60)

    db = SessionLocal()

    try:
        # 1. NewsArticle 샘플 데이터
        print("\n📰 NewsArticle 샘플 데이터 삽입...")
        news = NewsArticle(
            title="삼성전자, 3나노 공정 개발 성공",
            content="삼성전자가 차세대 3나노 공정 개발에 성공했다고 발표했다.",
            published_at=datetime(2025, 10, 31, 9, 0, 0),
            source="naver",
            stock_code="005930",
        )
        db.add(news)
        db.commit()
        db.refresh(news)
        print(f"   ✅ {news}")

        # 2. StockPrice 샘플 데이터
        print("\n📊 StockPrice 샘플 데이터 삽입...")
        stock = StockPrice(
            stock_code="005930",
            date=datetime(2025, 10, 31),
            open=70000.0,
            high=71000.0,
            low=69500.0,
            close=70500.0,
            volume=10000000,
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
        print(f"   ✅ {stock}")

        # 3. NewsStockMatch 샘플 데이터
        print("\n🔗 NewsStockMatch 샘플 데이터 삽입...")
        match = NewsStockMatch(
            news_id=news.id,
            stock_code="005930",
            price_change_1d=2.5,
            price_change_3d=5.3,
            price_change_5d=7.8,
        )
        db.add(match)
        db.commit()
        db.refresh(match)
        print(f"   ✅ {match}")

        # 4. TelegramUser 샘플 데이터
        print("\n👤 TelegramUser 샘플 데이터 삽입...")
        user = TelegramUser(
            user_id="123456789",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"   ✅ {user}")

        # 5. 데이터 조회 테스트
        print("\n🔍 데이터 조회 테스트...")
        news_count = db.query(NewsArticle).count()
        stock_count = db.query(StockPrice).count()
        match_count = db.query(NewsStockMatch).count()
        user_count = db.query(TelegramUser).count()

        print(f"   📰 NewsArticle: {news_count}건")
        print(f"   📊 StockPrice: {stock_count}건")
        print(f"   🔗 NewsStockMatch: {match_count}건")
        print(f"   👤 TelegramUser: {user_count}건")

        # 6. 외래 키 제약 조건 테스트
        print("\n🔗 외래 키 관계 테스트...")
        match_with_news = (
            db.query(NewsStockMatch).filter(NewsStockMatch.news_id == news.id).first()
        )
        if match_with_news and match_with_news.news_article:
            print(f"   ✅ Foreign Key 동작 확인: {match_with_news.news_article.title[:30]}...")
        else:
            print(f"   ❌ Foreign Key 관계 조회 실패")

        print("\n✅ 모든 테스트 통과!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        print(f"   에러 타입: {type(e).__name__}")
        print("=" * 60)
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = test_sample_data()
    sys.exit(0 if success else 1)
