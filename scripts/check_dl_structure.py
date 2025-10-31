"""
네이버 뉴스 dl 구조 상세 확인
"""
import requests
from bs4 import BeautifulSoup

url = "https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258&page=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Compatible; Craveny/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

response = requests.get(url, headers=headers, timeout=10)
response.encoding = "utf-8"

soup = BeautifulSoup(response.text, "html.parser")

# 첫 번째 newsList 가져오기
newslist = soup.select_one(".newsList")

if newslist:
    # 첫 3개 dd.articleSubject 확인
    articles = newslist.select("dd.articleSubject")[:3]

    for i, article_dd in enumerate(articles, 1):
        print(f"\n{'='*60}")
        print(f"뉴스 {i}:")
        print(f"{'='*60}")

        # 부모 dl 찾기
        parent_dl = article_dd.find_parent("dl")

        if parent_dl:
            print("parent_dl 구조:")
            # dl 안의 모든 요소 확인
            for child in parent_dl.children:
                if child.name:
                    print(f"  {child.name}: {child.get('class', [])} - {child.get_text(strip=True)[:80]}")
