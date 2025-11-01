"""
네이버 뉴스 검색 크롤러

키워드로 네이버 뉴스를 검색합니다.
"""
import logging
from typing import List, Optional
from datetime import datetime
from urllib.parse import quote

from bs4 import BeautifulSoup

from backend.crawlers.base_crawler import BaseNewsCrawler, NewsArticleData


logger = logging.getLogger(__name__)


class NaverNewsSearchCrawler(BaseNewsCrawler):
    """네이버 뉴스 검색 크롤러"""

    # 네이버 검색 URL
    BASE_URL = "https://search.naver.com/search.naver"

    def __init__(self):
        """네이버 뉴스 검색 크롤러 초기화"""
        super().__init__(source_name="네이버검색")

    def _get_search_url(
        self,
        query: str,
        page: int = 1,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        뉴스 검색 URL을 생성합니다.

        Args:
            query: 검색 키워드
            page: 페이지 번호
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            뉴스 검색 URL
        """
        # 기본 URL
        url = f"{self.BASE_URL}?where=news&query={quote(query)}"

        # 페이징: start=(page-1)*10 + 1
        start = (page - 1) * 10 + 1
        url += f"&start={start}"

        # 날짜 필터 (YYYY.MM.DD 형식)
        if start_date:
            url += f"&pd=3&ds={start_date.strftime('%Y.%m.%d')}"
        if end_date:
            url += f"&de={end_date.strftime('%Y.%m.%d')}"

        # 정렬: 관련도순(0), 최신순(1)
        url += "&sort=1"  # 최신순

        return url

    def _parse_news_item(self, article_div: BeautifulSoup) -> Optional[NewsArticleData]:
        """
        뉴스 아이템을 파싱합니다 (새로운 네이버 SDS 디자인 시스템).

        Args:
            article_div: div.vs1RfKE1eTzMZ5RqnhIv 요소

        Returns:
            NewsArticleData 또는 None (파싱 실패 시)
        """
        try:
            # 제목 및 URL 추출 (새 구조)
            title_link = article_div.select_one("a.VVZqvAlvnADQu8BVMc2n")
            if not title_link:
                return None

            url = title_link.get("href")
            title_elem = title_link.select_one(".sds-comps-text-type-headline1")
            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)

            # 요약 내용 (새 구조)
            content_link = article_div.select_one("a.IHHP42o8XWWWUySDAoa1")
            if content_link:
                content_elem = content_link.select_one(".sds-comps-text-ellipsis-3")
                content = content_elem.get_text(strip=True) if content_elem else title
            else:
                content = title

            # 언론사 (새 구조)
            press_elem = article_div.select_one(".sds-comps-profile-info-title-text a span")
            press = press_elem.get_text(strip=True) if press_elem else "네이버"

            # 날짜 (새 구조 - "N분 전", "N시간 전" 형식)
            date_elem = article_div.select_one(".sds-comps-profile-info-subtext .U1zN1wdZWj0pyvj9oyR0 span")
            date_str = date_elem.get_text(strip=True) if date_elem else ""
            published_at = self._parse_date(date_str)

            return NewsArticleData(
                title=title,
                content=content,
                published_at=published_at,
                source=f"네이버({press})",
                url=url,
            )

        except Exception as e:
            logger.error(f"뉴스 아이템 파싱 실패: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """
        네이버 날짜 문자열을 datetime으로 변환합니다.

        Args:
            date_str: 날짜 문자열
                - "N분 전", "N시간 전"
                - "2025.10.31."
                - "2025-10-31"

        Returns:
            datetime 객체
        """
        try:
            # "N분 전" 또는 "N시간 전"
            if "분 전" in date_str or "시간 전" in date_str or "일 전" in date_str:
                return datetime.now()

            # "2025.10.31." 형식
            if "." in date_str:
                date_str = date_str.rstrip(".")
                return datetime.strptime(date_str, "%Y.%m.%d")

            # "2025-10-31" 형식
            if "-" in date_str:
                return datetime.strptime(date_str, "%Y-%m-%d")

            logger.warning(f"날짜 파싱 실패: {date_str}, 현재 시간 사용")
            return datetime.now()

        except Exception as e:
            logger.warning(f"날짜 파싱 실패: {date_str} ({e}), 현재 시간 사용")
            return datetime.now()

    def search_news(
        self,
        query: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[NewsArticleData]:
        """
        네이버 뉴스를 검색합니다.

        Args:
            query: 검색 키워드
            start_date: 시작 날짜
            end_date: 종료 날짜
            limit: 가져올 뉴스 개수

        Returns:
            NewsArticleData 리스트
        """
        news_list: List[NewsArticleData] = []
        page = 1

        logger.info(f"네이버 뉴스 검색 시작: query={query}, limit={limit}")

        while len(news_list) < limit:
            # 페이지 HTML 가져오기
            url = self._get_search_url(query, page, start_date, end_date)
            html = self.fetch_html(url)

            if not html:
                logger.warning(f"페이지 {page} 가져오기 실패")
                break

            # HTML 파싱
            soup = BeautifulSoup(html, "html.parser")

            # 뉴스 리스트 추출 (새 구조)
            news_items = soup.select("div.vs1RfKE1eTzMZ5RqnhIv")

            if not news_items:
                logger.info(f"페이지 {page}에 더 이상 뉴스가 없습니다")
                break

            # 각 뉴스 아이템 파싱
            for article_div in news_items:
                if len(news_list) >= limit:
                    break

                news_data = self._parse_news_item(article_div)
                if news_data:
                    news_list.append(news_data)
                    logger.debug(f"뉴스 추가: {news_data.title[:50]}")

            page += 1

            # 안전장치: 최대 10페이지까지만
            if page > 10:
                logger.warning("최대 페이지 수(10) 도달")
                break

            # Rate limiting
            import time

            time.sleep(0.5)

        logger.info(f"네이버 뉴스 검색 완료: {len(news_list)}건")
        return news_list

    def fetch_news(self, limit: int = 10) -> List[NewsArticleData]:
        """
        네이버 뉴스를 가져옵니다. (BaseNewsCrawler 추상 메서드 구현)

        Args:
            limit: 가져올 뉴스 개수

        Returns:
            NewsArticleData 리스트
        """
        # 기본적으로 최신 뉴스를 검색
        return self.search_news(query="증권", limit=limit)
