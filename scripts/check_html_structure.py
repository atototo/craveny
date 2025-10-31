"""
네이버 뉴스 HTML 구조 확인 스크립트
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

# 페이지 제목 확인
print(f"페이지 제목: {soup.title.string if soup.title else '없음'}")

# 뉴스 리스트 찾기 - 다양한 선택자 시도
selectors_to_try = [
    ".newsList",
    ".articleSubject",
    ".type5",
    ".newsflash_body",
    ".section_strategy",
    "table.type5",
    ".articleSummary",
]

print("\n찾은 요소들:")
for selector in selectors_to_try:
    elements = soup.select(selector)
    print(f"{selector}: {len(elements)}개")

# 첫 번째 뉴스 아이템 출력
print("\n\n첫 번째 articleSubject:")
first_article = soup.select_one(".articleSubject")
if first_article:
    # 부모 요소들 확인
    parent = first_article.parent
    print(f"부모: {parent.name if parent else '없음'}")
    if parent:
        grandparent = parent.parent
        print(f"조부모: {grandparent.name if grandparent else '없음'}")

# newsList 구조 확인
print("\n\nnewsList 구조:")
newslist = soup.select(".newsList")
for i, nl in enumerate(newslist):
    print(f"\n{i+1}번째 newsList:")
    articles = nl.select(".articleSubject")
    print(f"  articleSubject: {len(articles)}개")
    if articles:
        print(f"  첫 번째 제목: {articles[0].get_text(strip=True)[:100]}")

        # 날짜 정보 찾기
        summaries = nl.select(".articleSummary")
        if summaries:
            print(f"  articleSummary: {len(summaries)}개")

# dl dt dd 구조 확인
print("\n\ndl dt dd 구조 확인:")
dls = soup.select("dl")
print(f"총 {len(dls)}개 dl")
if dls:
    first_dl = dls[0]
    dds = first_dl.select("dd")
    print(f"첫 번째 dl의 dd: {len(dds)}개")
