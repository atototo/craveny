"""
임베딩 기반 뉴스 중복 검사 모듈

유사한 뉴스를 임베딩 유사도로 판별하여 중복 예측 및 알림을 방지합니다.
"""
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.llm.vector_search import get_vector_search
from backend.db.models.news import NewsArticle


logger = logging.getLogger(__name__)


class EmbeddingDeduplicator:
    """임베딩 기반 중복 검사 클래스"""

    def __init__(
        self,
        high_similarity_threshold: float = 0.95,
        medium_similarity_threshold: float = 0.90,
        lookback_hours: int = 24,
    ):
        """
        임베딩 기반 중복 검사기 초기화

        Args:
            high_similarity_threshold: 높은 유사도 임계값 (>= 이 값이면 중복으로 간주)
            medium_similarity_threshold: 중간 유사도 임계값 (>= 이 값이면 낮은 우선순위)
            lookback_hours: 과거 몇 시간 동안의 뉴스와 비교할지
        """
        self.high_similarity_threshold = high_similarity_threshold
        self.medium_similarity_threshold = medium_similarity_threshold
        self.lookback_hours = lookback_hours
        self.vector_search = get_vector_search()

    def should_skip_prediction(
        self,
        news_text: str,
        stock_code: str,
        db: Session,
    ) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        예측 생성을 skip 해야 하는지 판단합니다.

        Args:
            news_text: 뉴스 텍스트 (제목 + 내용)
            stock_code: 종목 코드
            db: 데이터베이스 세션

        Returns:
            (should_skip, similar_news_id, similarity) 튜플
            - should_skip: True면 예측 skip, False면 예측 진행
            - similar_news_id: 유사 뉴스 ID (중복일 경우)
            - similarity: 유사도 점수
        """
        try:
            # 1. 최근 뉴스 중 유사도가 높은 뉴스 검색
            similar_news = self.vector_search.search_similar_news(
                news_text=news_text,
                stock_code=stock_code,
                top_k=3,  # 상위 3개만 확인
                similarity_threshold=self.medium_similarity_threshold,
            )

            if not similar_news:
                logger.debug(f"유사 뉴스 없음 → 예측 진행 (종목: {stock_code})")
                return False, None, None

            # 2. 가장 유사한 뉴스 선택
            most_similar = similar_news[0]
            similarity = most_similar["similarity"]
            news_id = most_similar["news_id"]

            # 3. 시간 범위 내 뉴스인지 확인
            cutoff_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
            recent_news = (
                db.query(NewsArticle)
                .filter(
                    NewsArticle.id == news_id,
                    NewsArticle.created_at >= cutoff_time,
                )
                .first()
            )

            if not recent_news:
                logger.debug(
                    f"유사 뉴스가 시간 범위 밖 (뉴스 ID={news_id}) → 예측 진행"
                )
                return False, None, None

            # 4. 유사도 기반 판단
            if similarity >= self.high_similarity_threshold:
                logger.info(
                    f"🔴 높은 유사도 ({similarity:.3f}) → 예측 skip "
                    f"(뉴스 ID={news_id}, 종목={stock_code})"
                )
                return True, news_id, similarity

            elif similarity >= self.medium_similarity_threshold:
                logger.info(
                    f"🟡 중간 유사도 ({similarity:.3f}) → 낮은 우선순위 "
                    f"(뉴스 ID={news_id}, 종목={stock_code})"
                )
                # 중간 유사도는 skip하지 않고 우선순위만 낮춤
                return False, news_id, similarity

            else:
                logger.debug(f"낮은 유사도 ({similarity:.3f}) → 예측 진행")
                return False, None, similarity

        except Exception as e:
            logger.error(f"임베딩 중복 검사 실패: {e}", exc_info=True)
            # 오류 발생 시 안전하게 예측 진행
            return False, None, None

    def should_skip_notification(
        self,
        news_text: str,
        stock_code: str,
        db: Session,
        notification_lookback_hours: int = 4,
    ) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        알림 전송을 skip 해야 하는지 판단합니다.

        Args:
            news_text: 뉴스 텍스트 (제목 + 내용)
            stock_code: 종목 코드
            db: 데이터베이스 세션
            notification_lookback_hours: 최근 몇 시간 내 알림과 비교할지

        Returns:
            (should_skip, similar_news_id, similarity) 튜플
            - should_skip: True면 알림 skip, False면 알림 전송
            - similar_news_id: 유사 뉴스 ID
            - similarity: 유사도 점수
        """
        try:
            # 1. 최근 알림 전송된 뉴스 중 유사도가 높은 뉴스 검색
            similar_news = self.vector_search.search_similar_news(
                news_text=news_text,
                stock_code=stock_code,
                top_k=3,
                similarity_threshold=self.high_similarity_threshold,
            )

            if not similar_news:
                return False, None, None

            # 2. 최근 알림 전송된 뉴스인지 확인
            cutoff_time = datetime.utcnow() - timedelta(hours=notification_lookback_hours)

            for similar in similar_news:
                news_id = similar["news_id"]
                similarity = similar["similarity"]

                # 최근 알림 전송된 뉴스 조회
                notified_news = (
                    db.query(NewsArticle)
                    .filter(
                        NewsArticle.id == news_id,
                        NewsArticle.notified_at.isnot(None),
                        NewsArticle.notified_at >= cutoff_time,
                    )
                    .first()
                )

                if notified_news and similarity >= self.high_similarity_threshold:
                    logger.info(
                        f"🔕 유사 뉴스 알림 이력 존재 (유사도={similarity:.3f}) "
                        f"→ 알림 skip (뉴스 ID={news_id}, 종목={stock_code})"
                    )
                    return True, news_id, similarity

            return False, None, None

        except Exception as e:
            logger.error(f"알림 중복 검사 실패: {e}", exc_info=True)
            # 오류 발생 시 안전하게 알림 전송
            return False, None, None


# 싱글톤 인스턴스
_embedding_deduplicator: Optional[EmbeddingDeduplicator] = None


def get_embedding_deduplicator() -> EmbeddingDeduplicator:
    """
    EmbeddingDeduplicator 싱글톤 인스턴스를 반환합니다.

    Returns:
        EmbeddingDeduplicator 인스턴스
    """
    global _embedding_deduplicator
    if _embedding_deduplicator is None:
        _embedding_deduplicator = EmbeddingDeduplicator()
    return _embedding_deduplicator
