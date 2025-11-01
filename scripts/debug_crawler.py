"""
크롤러 디버깅 스크립트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta
from backend.crawlers.naver_search_crawler import NaverNewsSearchCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

def main():
    crawler = NaverNewsSearchCrawler()

    # 최근 30일 뉴스 검색
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    url = crawler._get_search_url("삼성전자", 1, start_date, end_date)
    print(f"URL: {url}")
    print()

    html = crawler.fetch_html(url)

    if html:
        # HTML의 일부를 파일로 저장
        with open("/tmp/naver_search.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("HTML 저장됨: /tmp/naver_search.html")
        print(f"HTML 길이: {len(html)}")

        # 새로운 네이버 SDS 구조 확인
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 새 구조 테스트
        news_items = soup.select("div.vs1RfKE1eTzMZ5RqnhIv")
        print(f"찾은 div.vs1RfKE1eTzMZ5RqnhIv 요소 수: {len(news_items)}")

        if news_items:
            # 첫 번째 뉴스로 파싱 테스트
            print("\n첫 번째 뉴스 파싱 테스트:")
            first_news = news_items[0]

            # 제목
            title_link = first_news.select_one("a.VVZqvAlvnADQu8BVMc2n")
            if title_link:
                title = title_link.select_one(".sds-comps-text-type-headline1")
                print(f"제목: {title.get_text(strip=True) if title else '없음'}")
                print(f"URL: {title_link.get('href')}")

            # 내용
            content_link = first_news.select_one("a.IHHP42o8XWWWUySDAoa1")
            if content_link:
                content = content_link.select_one(".sds-comps-text-ellipsis-3")
                print(f"내용: {content.get_text(strip=True)[:50] if content else '없음'}...")

            # 언론사
            press = first_news.select_one(".sds-comps-profile-info-title-text a span")
            print(f"언론사: {press.get_text(strip=True) if press else '없음'}")

            # 날짜
            date = first_news.select_one(".sds-comps-profile-info-subtext .U1zN1wdZWj0pyvj9oyR0 span")
            print(f"날짜: {date.get_text(strip=True) if date else '없음'}")
    else:
        print("HTML 가져오기 실패")

if __name__ == "__main__":
    main()
