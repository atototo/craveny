"""
뉴스 크롤러 테스트 스크립트

각 크롤러를 개별적으로 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from backend.crawlers.naver_crawler import NaverNewsCrawler
from backend.crawlers.hankyung_crawler import HankyungNewsCrawler
from backend.crawlers.maeil_crawler import MaeilNewsCrawler
from backend.crawlers.news_saver import NewsSaver
from backend.db.session import SessionLocal


# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_naver_crawler():
    """네이버 크롤러 테스트"""
    print("=" * 60)
    print("📰 네이버 크롤러 테스트")
    print("=" * 60)

    try:
        with NaverNewsCrawler() as crawler:
            news_list = crawler.fetch_news(limit=5)

            print(f"\n✅ 크롤링 성공: {len(news_list)}건")

            for i, news in enumerate(news_list, 1):
                print(f"\n{i}. {news.title}")
                print(f"   발표: {news.published_at}")
                print(f"   출처: {news.source}")
                print(f"   본문: {news.content[:100]}...")
                if news.url:
                    print(f"   URL: {news.url}")

            return news_list

    except Exception as e:
        print(f"\n❌ 네이버 크롤러 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return []


def test_hankyung_crawler():
    """한국경제 크롤러 테스트"""
    print("\n" + "=" * 60)
    print("📰 한국경제 크롤러 테스트")
    print("=" * 60)

    try:
        with HankyungNewsCrawler() as crawler:
            news_list = crawler.fetch_news(limit=5)

            print(f"\n✅ 크롤링 성공: {len(news_list)}건")

            for i, news in enumerate(news_list, 1):
                print(f"\n{i}. {news.title}")
                print(f"   발표: {news.published_at}")
                print(f"   출처: {news.source}")

            return news_list

    except Exception as e:
        print(f"\n❌ 한국경제 크롤러 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return []


def test_maeil_crawler():
    """매일경제 크롤러 테스트"""
    print("\n" + "=" * 60)
    print("📰 매일경제 크롤러 테스트")
    print("=" * 60)

    try:
        with MaeilNewsCrawler() as crawler:
            news_list = crawler.fetch_news(limit=5)

            print(f"\n✅ 크롤링 성공: {len(news_list)}건")

            for i, news in enumerate(news_list, 1):
                print(f"\n{i}. {news.title}")
                print(f"   발표: {news.published_at}")
                print(f"   출처: {news.source}")

            return news_list

    except Exception as e:
        print(f"\n❌ 매일경제 크롤러 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return []


def test_news_saver(news_list):
    """뉴스 저장 테스트"""
    print("\n" + "=" * 60)
    print("💾 뉴스 저장 테스트")
    print("=" * 60)

    if not news_list:
        print("⚠️  저장할 뉴스가 없습니다")
        return

    db = SessionLocal()

    try:
        saver = NewsSaver(db)
        saved, skipped = saver.save_news_batch(news_list)

        print(f"\n✅ 저장 완료: {saved}건 저장, {skipped}건 스킵")

    except Exception as e:
        print(f"\n❌ 저장 실패: {e}")
        import traceback

        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    print("🧪 뉴스 크롤러 통합 테스트")
    print("=" * 60)

    # 네이버 크롤러 테스트
    naver_news = test_naver_crawler()

    # 한국경제 크롤러 테스트 (주석 처리 - 실제 사이트 구조 확인 필요)
    # hankyung_news = test_hankyung_crawler()

    # 매일경제 크롤러 테스트 (주석 처리 - 실제 사이트 구조 확인 필요)
    # maeil_news = test_maeil_crawler()

    # 뉴스 저장 테스트
    if naver_news:
        test_news_saver(naver_news)

    print("\n" + "=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)
