"""
DART 크롤러 테스트 스크립트

DART 공시 크롤링 기능을 테스트합니다.
"""
import sys
import os
from datetime import datetime, timedelta

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.crawlers.dart_crawler import DartCrawler
from backend.config import settings


def test_dart_crawler():
    """DART 크롤러 테스트"""

    print("=" * 60)
    print("🔍 DART 크롤러 테스트 시작")
    print("=" * 60)

    # DART API 키 확인
    if not settings.DART_API_KEY:
        print("⚠️  DART_API_KEY가 설정되지 않았습니다")
        print("📝 .env 파일에 DART_API_KEY를 추가하세요")
        print("🔗 API 키 발급: https://opendart.fss.or.kr/")
        return

    # 크롤러 초기화
    crawler = DartCrawler()

    # 테스트 종목 코드 (삼성전자)
    test_stock_code = "005930"

    print(f"\n📊 테스트 종목: 삼성전자 ({test_stock_code})")

    # 최근 3일간 공시 조회
    start_date = datetime.now() - timedelta(days=3)
    end_date = datetime.now()

    print(f"📅 조회 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print()

    try:
        # 공시 수집
        disclosures = crawler.fetch_disclosures_by_stock_code(
            stock_code=test_stock_code,
            start_date=start_date,
            end_date=end_date,
        )

        if disclosures:
            print(f"✅ {len(disclosures)}건의 공시를 찾았습니다\n")

            # 공시 정보 출력
            for i, disclosure in enumerate(disclosures, 1):
                print(f"[공시 {i}]")
                print(f"  제목: {disclosure.title}")
                print(f"  출처: {disclosure.source}")
                print(f"  회사: {disclosure.company_name or 'N/A'}")
                print(f"  발행일: {disclosure.published_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  내용 미리보기: {disclosure.content[:100]}...")
                print()
        else:
            print("⚠️  조회 기간 내 공시가 없습니다")

        print("=" * 60)
        print("✅ DART 크롤러 테스트 완료")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_dart_crawler()
