"""
매일경제 증권 뉴스 크롤러

매일경제 증권 뉴스를 크롤링합니다.
"""
import logging
from typing import List, Optional
from datetime import datetime

from bs4 import BeautifulSoup

from backend.crawlers.base_crawler import BaseNewsCrawler, NewsArticleData


logger = logging.getLogger(__name__)


class MaeilNewsCrawler(BaseNewsCrawler):
    """매일경제 증권 뉴스 크롤러"""

    BASE_URL = "https://www.mk.co.kr/news/stock/"

    def __init__(self):
        """매일경제 뉴스 크롤러 초기화"""
        super().__init__(source_name="매일경제")

    def _parse_news_item(self, item: BeautifulSoup) -> Optional[NewsArticleData]:
        """
        뉴스 아이템을 파싱합니다.

        Args:
            item: BeautifulSoup 뉴스 아이템

        Returns:
            NewsArticleData 또는 None (파싱 실패 시)
        """
        try:
            # 제목 추출 (실제 사이트 구조에 맞게 조정 필요)
            title_elem = item.select_one(".news_ttl, h3, .headline, .title")
            if not title_elem:
                return None
            title = title_elem.get_text(strip=True)

            # URL 추출
            link_elem = item.select_one("a")
            url = link_elem.get("href") if link_elem else None
            if url and not url.startswith("http"):
                url = f"https://www.mk.co.kr{url}"

            # 본문 요약 추출
            summary_elem = item.select_one(".news_desc, .summary, p")
            content = summary_elem.get_text(strip=True) if summary_elem else title

            # 발표 시간 추출
            date_elem = item.select_one(".news_date, .date, time")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
                published_at = self._parse_date(date_str)
            else:
                published_at = datetime.now()

            return NewsArticleData(
                title=title,
                content=content,
                published_at=published_at,
                source="매일경제",
                url=url,
            )

        except Exception as e:
            logger.error(f"뉴스 아이템 파싱 실패: {e}")
            return None

    def _parse_date(self, date_str: str) -> datetime:
        """
        매일경제 날짜 문자열을 datetime으로 변환합니다.

        Args:
            date_str: 날짜 문자열

        Returns:
            datetime 객체
        """
        try:
            # 다양한 날짜 형식 시도
            for fmt in [
                "%Y.%m.%d %H:%M",
                "%Y-%m-%d %H:%M",
                "%Y.%m.%d",
                "%Y-%m-%d",
                "%m.%d %H:%M",  # 같은 해인 경우
            ]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    # %m.%d %H:%M 형식인 경우 현재 연도 추가
                    if dt.year == 1900:
                        dt = dt.replace(year=datetime.now().year)
                    return dt
                except ValueError:
                    continue

            logger.warning(f"날짜 파싱 실패: {date_str}, 현재 시간 사용")
            return datetime.now()

        except Exception as e:
            logger.error(f"날짜 파싱 에러: {e}")
            return datetime.now()

    def fetch_news(self, limit: int = 10) -> List[NewsArticleData]:
        """
        매일경제 증권 뉴스를 크롤링합니다.

        Args:
            limit: 가져올 뉴스 개수

        Returns:
            NewsArticleData 리스트
        """
        news_list: List[NewsArticleData] = []

        logger.info(f"매일경제 뉴스 크롤링 시작 (limit={limit})")

        # HTML 가져오기
        html = self.fetch_html(self.BASE_URL)

        if not html:
            logger.error("페이지 가져오기 실패")
            return news_list

        # HTML 파싱
        soup = BeautifulSoup(html, "html.parser")

        # 뉴스 리스트 추출 (실제 사이트 구조에 맞게 조정 필요)
        news_items = soup.select(".news_node, .list_area li, article, .news-item")

        if not news_items:
            logger.warning("뉴스를 찾을 수 없습니다 (CSS 선택자 확인 필요)")
            return news_list

        # 각 뉴스 아이템 파싱
        for item in news_items[:limit]:
            news_data = self._parse_news_item(item)
            if news_data:
                news_list.append(news_data)
                logger.debug(f"뉴스 추가: {news_data.title[:50]}")

        logger.info(f"매일경제 뉴스 크롤링 완료: {len(news_list)}건")
        return news_list
