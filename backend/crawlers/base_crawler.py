"""
뉴스 크롤러 Base 클래스

모든 뉴스 크롤러의 기본 클래스를 정의합니다.
"""
import time
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class NewsArticleData:
    """크롤링된 뉴스 기사 데이터 클래스"""

    def __init__(
        self,
        title: str,
        content: str,
        published_at: datetime,
        source: str,
        url: Optional[str] = None,
        company_name: Optional[str] = None,
    ):
        """
        Args:
            title: 뉴스 제목
            content: 뉴스 본문
            published_at: 발표 시간
            source: 언론사 (예: "네이버", "한국경제")
            url: 뉴스 URL (선택)
            company_name: 관련 기업명 (선택)
        """
        self.title = title
        self.content = content
        self.published_at = published_at
        self.source = source
        self.url = url
        self.company_name = company_name

    def __repr__(self) -> str:
        return f"<NewsArticleData(title='{self.title[:30]}...', source='{self.source}')>"


class BaseNewsCrawler(ABC):
    """뉴스 크롤러 추상 베이스 클래스"""

    def __init__(
        self,
        source_name: str,
        timeout: int = 10,
        max_retries: int = 3,
        rate_limit_seconds: float = 1.0,
    ):
        """
        Args:
            source_name: 언론사 이름
            timeout: HTTP 요청 타임아웃 (초)
            max_retries: 최대 재시도 횟수
            rate_limit_seconds: Rate limiting 간격 (초)
        """
        self.source_name = source_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_seconds = rate_limit_seconds
        self.session = self._create_session()
        self.last_request_time: Optional[float] = None

    def _create_session(self) -> requests.Session:
        """
        HTTP 세션을 생성합니다.
        Retry 로직과 User-Agent를 설정합니다.

        Returns:
            requests.Session 객체
        """
        session = requests.Session()

        # Retry 전략 설정 (exponential backoff)
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # 1초, 2초, 4초...
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # User-Agent 설정
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Compatible; Craveny/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )

        return session

    def _apply_rate_limit(self) -> None:
        """Rate limiting을 적용합니다."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_seconds:
                sleep_time = self.rate_limit_seconds - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}초")
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch_html(self, url: str) -> Optional[str]:
        """
        URL에서 HTML을 가져옵니다.

        Args:
            url: 요청할 URL

        Returns:
            HTML 문자열 또는 None (실패 시)
        """
        self._apply_rate_limit()

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = "utf-8"  # 한글 인코딩 설정
            return response.text

        except requests.exceptions.Timeout:
            logger.error(f"Timeout error for {url}")
            return None

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None

    @abstractmethod
    def fetch_news(self, limit: int = 10) -> List[NewsArticleData]:
        """
        뉴스를 크롤링합니다.

        Args:
            limit: 가져올 뉴스 개수

        Returns:
            NewsArticleData 리스트
        """
        pass

    def close(self) -> None:
        """HTTP 세션을 닫습니다."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager 진입"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.close()
