"""
뉴스 저장 로직

크롤링한 뉴스를 데이터베이스에 저장합니다.
"""
import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from backend.crawlers.base_crawler import NewsArticleData
from backend.db.models.news import NewsArticle
from backend.utils.stock_mapping import get_stock_mapper
from backend.utils.deduplicator import get_deduplicator


logger = logging.getLogger(__name__)


class NewsSaver:
    """뉴스 저장 클래스"""

    def __init__(self, db: Session):
        """
        Args:
            db: 데이터베이스 세션
        """
        self.db = db
        self.stock_mapper = get_stock_mapper()
        self.deduplicator = get_deduplicator()

    def _extract_stock_code(self, news_data: NewsArticleData) -> Optional[str]:
        """
        뉴스 데이터에서 종목코드를 추출합니다.

        Args:
            news_data: 뉴스 데이터

        Returns:
            종목코드 또는 None
        """
        # 1. 뉴스 데이터에 기업명이 있으면 직접 매핑
        if news_data.company_name:
            stock_code = self.stock_mapper.get_stock_code(news_data.company_name)
            if stock_code:
                logger.debug(f"기업명으로 종목코드 매칭: {news_data.company_name} -> {stock_code}")
                return stock_code

        # 2. 제목에서 기업명 찾기
        stock_code = self.stock_mapper.find_stock_code_in_text(news_data.title)
        if stock_code:
            logger.debug(f"제목에서 종목코드 발견: {news_data.title[:50]} -> {stock_code}")
            return stock_code

        # 3. 본문에서 기업명 찾기
        stock_code = self.stock_mapper.find_stock_code_in_text(news_data.content)
        if stock_code:
            logger.debug(f"본문에서 종목코드 발견 -> {stock_code}")
            return stock_code

        logger.debug("종목코드를 찾을 수 없음")
        return None

    def save_news(self, news_data: NewsArticleData) -> Optional[NewsArticle]:
        """
        뉴스를 데이터베이스에 저장합니다.

        중복 검사를 수행하고, 중복이 아닌 경우에만 저장합니다.

        Args:
            news_data: 뉴스 데이터

        Returns:
            저장된 NewsArticle 또는 None (중복인 경우)
        """
        # 중복 검사
        is_duplicate, duplicate_id = self.deduplicator.find_duplicate_in_db(
            news_data.title, self.db
        )

        if is_duplicate:
            logger.info(f"중복 뉴스 스킵: {news_data.title[:50]}")
            return None

        # 종목코드 추출
        stock_code = self._extract_stock_code(news_data)

        # NewsArticle 모델 인스턴스 생성
        news_article = NewsArticle(
            title=news_data.title,
            content=news_data.content,
            published_at=news_data.published_at,
            source=news_data.source,
            stock_code=stock_code,
        )

        # DB에 저장
        try:
            self.db.add(news_article)
            self.db.commit()
            self.db.refresh(news_article)

            logger.info(
                f"뉴스 저장 완료: ID={news_article.id}, "
                f"제목='{news_article.title[:50]}', "
                f"종목코드={stock_code or 'N/A'}"
            )

            return news_article

        except Exception as e:
            self.db.rollback()
            logger.error(f"뉴스 저장 실패: {e}")
            return None

    def save_news_batch(
        self, news_list: List[NewsArticleData]
    ) -> tuple[int, int]:
        """
        여러 뉴스를 배치로 저장합니다.

        Args:
            news_list: 뉴스 데이터 리스트

        Returns:
            (저장 성공 수, 중복 스킵 수) 튜플
        """
        saved_count = 0
        skipped_count = 0

        for news_data in news_list:
            result = self.save_news(news_data)
            if result:
                saved_count += 1
            else:
                skipped_count += 1

        logger.info(
            f"배치 저장 완료: 총 {len(news_list)}건 -> "
            f"저장 {saved_count}건, 중복 스킵 {skipped_count}건"
        )

        return (saved_count, skipped_count)
