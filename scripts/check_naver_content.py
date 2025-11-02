"""
NAVER 뉴스의 실제 내용을 확인하는 스크립트
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle


def check_naver_content():
    db = SessionLocal()

    try:
        # NAVER 종목(035420)으로 분류된 뉴스 조회
        naver_news = db.query(NewsArticle).filter(
            NewsArticle.stock_code == "035420"
        ).limit(3).all()

        for news in naver_news:
            print("="*80)
            print(f"ID: {news.id}")
            print(f"제목: {news.title}")
            print(f"출처: {news.source}")
            print(f"\n본문:")
            print(news.content[:500])
            print("\n...")
            print(f"\n'네이버' 포함 여부: {'네이버' in news.content}")
            print(f"'NAVER' 포함 여부: {'NAVER' in news.content or 'naver' in news.content.lower()}")
            print("="*80)
            print()

    finally:
        db.close()


if __name__ == "__main__":
    check_naver_content()
