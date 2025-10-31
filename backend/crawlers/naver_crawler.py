"""
네이버 증권 뉴스 크롤러

네이버 금융 증권 뉴스를 크롤링합니다.
"""
import logging
from typing import List, Optional
from datetime import datetime

from bs4 import BeautifulSoup

from backend.crawlers.base_crawler import BaseNewsCrawler, NewsArticleData


logger = logging.getLogger(__name__)


class NaverNewsCrawler(BaseNewsCrawler):
    """네이버 증권 뉴스 크롤러"""

    # 네이버 증권 뉴스 URL
    BASE_URL = "https://finance.naver.com/news/news_list.naver"

    def __init__(self):
        """네이버 뉴스 크롤러 초기화"""
        super().__init__(source_name="네이버")

    def _get_news_list_url(self, page: int = 1) -> str:
        """
        뉴스 목록 URL을 생성합니다.

        Args:
            page: 페이지 번호

        Returns:
            뉴스 목록 URL
        """
        # 증권 > 종목 뉴스 섹션
        # mode=LSS2D: 2depth 리스트
        # section_id=101: 증권
        # section_id2=258: 종목
        return f"{self.BASE_URL}?mode=LSS2D&section_id=101&section_id2=258&page={page}"

    def _parse_news_item(self, article_dd: BeautifulSoup) -> Optional[NewsArticleData]:
        """
        뉴스 아이템을 파싱합니다.

        Args:
            article_dd: dd.articleSubject 요소

        Returns:
            NewsArticleData 또는 None (파싱 실패 시)
        """
        try:
            # 제목 및 URL 추출
            link_elem = article_dd.select_one("a")
            if not link_elem:
                return None

            title = link_elem.get_text(strip=True)
            url = link_elem.get("href")
            if url and not url.startswith("http"):
                url = f"https://finance.naver.com{url}"

            # 바로 다음 형제 요소인 dd.articleSummary 찾기
            summary_dd = article_dd.find_next_sibling("dd", class_="articleSummary")
            content = summary_dd.get_text(strip=True) if summary_dd else title

            # 날짜 및 언론사 정보는 summary_dd 안에 있음
            if summary_dd:
                wdate_elem = summary_dd.select_one(".wdate")
                if wdate_elem:
                    date_str = wdate_elem.get_text(strip=True)
                    published_at = self._parse_date(date_str)
                else:
                    published_at = datetime.now()

                press_elem = summary_dd.select_one(".press")
                press = press_elem.get_text(strip=True) if press_elem else "네이버"
            else:
                published_at = datetime.now()
                press = "네이버"

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
            date_str: 날짜 문자열 (예: "2025.10.31 14:30" or "2025-10-31 20:23")

        Returns:
            datetime 객체
        """
        try:
            # "2025-10-31 20:23" 형식 (하이픈)
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # "2025.10.31 14:30" 형식 (점)
                return datetime.strptime(date_str, "%Y.%m.%d %H:%M")
            except ValueError:
                try:
                    # "2025.10.31" 형식
                    return datetime.strptime(date_str, "%Y.%m.%d")
                except ValueError:
                    try:
                        # "2025-10-31" 형식
                        return datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        logger.warning(f"날짜 파싱 실패: {date_str}, 현재 시간 사용")
                        return datetime.now()

    def fetch_news(self, limit: int = 10) -> List[NewsArticleData]:
        """
        네이버 증권 뉴스를 크롤링합니다.

        Args:
            limit: 가져올 뉴스 개수

        Returns:
            NewsArticleData 리스트
        """
        news_list: List[NewsArticleData] = []
        page = 1

        logger.info(f"네이버 뉴스 크롤링 시작 (limit={limit})")

        while len(news_list) < limit:
            # 페이지 HTML 가져오기
            url = self._get_news_list_url(page)
            html = self.fetch_html(url)

            if not html:
                logger.warning(f"페이지 {page} 가져오기 실패")
                break

            # HTML 파싱
            soup = BeautifulSoup(html, "html.parser")

            # 뉴스 리스트 추출
            news_items = soup.select(".newsList .articleSubject")

            if not news_items:
                logger.info(f"페이지 {page}에 더 이상 뉴스가 없습니다")
                break

            # 각 뉴스 아이템 파싱 (dd.articleSubject를 직접 파싱)
            for article_dd in news_items:
                if len(news_list) >= limit:
                    break

                news_data = self._parse_news_item(article_dd)
                if news_data:
                    news_list.append(news_data)
                    logger.debug(f"뉴스 추가: {news_data.title[:50]}")

            page += 1

            # 안전장치: 최대 5페이지까지만
            if page > 5:
                logger.warning("최대 페이지 수(5) 도달")
                break

        logger.info(f"네이버 뉴스 크롤링 완료: {len(news_list)}건")
        return news_list
