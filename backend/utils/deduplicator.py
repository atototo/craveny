"""
뉴스 중복 검사 유틸리티

제목 유사도 기반으로 중복 뉴스를 필터링합니다.
"""
import logging
from typing import List
from difflib import SequenceMatcher
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.db.models.news import NewsArticle


logger = logging.getLogger(__name__)


class NewsDuplicator:
    """뉴스 중복 검사 클래스"""

    def __init__(self, similarity_threshold: float = 0.8, lookback_hours: int = 24):
        """
        Args:
            similarity_threshold: 중복 판정 유사도 임계값 (0.0 ~ 1.0)
            lookback_hours: 중복 검사 대상 시간 범위 (시간 단위)
        """
        self.similarity_threshold = similarity_threshold
        self.lookback_hours = lookback_hours

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 유사도를 계산합니다.

        Args:
            text1: 첫 번째 텍스트
            text2: 두 번째 텍스트

        Returns:
            유사도 (0.0 ~ 1.0)

        Examples:
            >>> dup = NewsDuplicator()
            >>> dup.calculate_similarity("삼성전자 주가 상승", "삼성전자 주가 하락")
            0.75
            >>> dup.calculate_similarity("삼성전자 주가 상승", "삼성전자 주가 상승")
            1.0
        """
        return SequenceMatcher(None, text1, text2).ratio()

    def is_duplicate(self, title1: str, title2: str) -> bool:
        """
        두 제목이 중복인지 판정합니다.

        Args:
            title1: 첫 번째 제목
            title2: 두 번째 제목

        Returns:
            중복 여부 (True: 중복, False: 중복 아님)
        """
        similarity = self.calculate_similarity(title1, title2)
        return similarity >= self.similarity_threshold

    def get_recent_news_titles(self, db: Session) -> List[tuple[int, str]]:
        """
        최근 뉴스 제목을 가져옵니다.

        Args:
            db: 데이터베이스 세션

        Returns:
            (뉴스 ID, 제목) 튜플 리스트
        """
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)

        recent_news = (
            db.query(NewsArticle.id, NewsArticle.title)
            .filter(NewsArticle.created_at >= cutoff_time)
            .all()
        )

        return [(news.id, news.title) for news in recent_news]

    def find_duplicate_in_db(self, title: str, db: Session) -> tuple[bool, int | None]:
        """
        데이터베이스에서 중복 뉴스를 찾습니다.

        Args:
            title: 검사할 뉴스 제목
            db: 데이터베이스 세션

        Returns:
            (중복 여부, 중복 뉴스 ID) 튜플
            중복이 아니면 (False, None) 반환
        """
        recent_news = self.get_recent_news_titles(db)

        for news_id, existing_title in recent_news:
            if self.is_duplicate(title, existing_title):
                logger.info(
                    f"중복 뉴스 발견 (유사도: {self.calculate_similarity(title, existing_title):.2f})"
                )
                logger.debug(f"  기존: {existing_title}")
                logger.debug(f"  신규: {title}")
                return (True, news_id)

        return (False, None)

    def filter_duplicates(
        self, titles: List[str], db: Session
    ) -> List[tuple[str, bool]]:
        """
        뉴스 제목 리스트에서 중복을 필터링합니다.

        Args:
            titles: 뉴스 제목 리스트
            db: 데이터베이스 세션

        Returns:
            (제목, 중복 여부) 튜플 리스트
        """
        results = []

        for title in titles:
            is_dup, _ = self.find_duplicate_in_db(title, db)
            results.append((title, is_dup))

        return results


# 싱글톤 인스턴스
_deduplicator: NewsDuplicator | None = None


def get_deduplicator(
    similarity_threshold: float = 0.8, lookback_hours: int = 24
) -> NewsDuplicator:
    """
    NewsDuplicator 싱글톤 인스턴스를 반환합니다.

    Args:
        similarity_threshold: 중복 판정 유사도 임계값
        lookback_hours: 중복 검사 대상 시간 범위

    Returns:
        NewsDuplicator 인스턴스
    """
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = NewsDuplicator(similarity_threshold, lookback_hours)
    return _deduplicator
