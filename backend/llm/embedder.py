"""
뉴스 임베딩 모듈

OpenAI Embedding API를 사용하여 뉴스를 벡터화합니다.
"""
import logging
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import time

from openai import OpenAI
from pymilvus import Collection, connections
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models.news import NewsArticle
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class NewsEmbedder:
    """뉴스 임베딩 클래스"""

    def __init__(self):
        """임베더 초기화"""
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        self.embedding_dim = 768  # text-embedding-3-small의 차원

    def embed_text(self, text: str) -> Optional[List[float]]:
        """
        텍스트를 OpenAI Embedding API로 벡터화합니다.

        Args:
            text: 임베딩할 텍스트

        Returns:
            768차원 임베딩 벡터 또는 None (실패 시)
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                dimensions=self.embedding_dim,  # 768차원으로 명시
            )

            embedding = response.data[0].embedding
            logger.debug(f"임베딩 생성 완료: {len(embedding)}차원")

            return embedding

        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """
        여러 텍스트를 배치로 임베딩합니다.

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트 (실패한 항목은 None)
        """
        embeddings = []

        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)

            # API rate limit 방지 (1초 대기)
            time.sleep(0.1)

        return embeddings

    def get_unembedded_news(self, db: Session, limit: int = 100) -> List[NewsArticle]:
        """
        아직 임베딩되지 않은 뉴스를 조회합니다.

        Args:
            db: 데이터베이스 세션
            limit: 조회할 최대 개수

        Returns:
            임베딩되지 않은 뉴스 리스트
        """
        try:
            # Milvus 연결
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )

            # Milvus 컬렉션 로드
            collection = Collection("news_embeddings")
            collection.load()

            # Milvus에 이미 저장된 news_article_id 조회
            results = collection.query(
                expr="",  # 모든 레코드
                output_fields=["news_article_id"],
                limit=16384,  # 최대 조회 개수
            )

            embedded_news_ids = set(r["news_article_id"] for r in results)
            logger.info(f"Milvus에 이미 저장된 뉴스: {len(embedded_news_ids)}건")

        except Exception as e:
            logger.warning(f"Milvus 조회 실패 (모든 뉴스를 대상으로 처리): {e}")
            embedded_news_ids = set()

        # PostgreSQL에서 미임베딩 뉴스 조회
        if embedded_news_ids:
            unembedded_news = (
                db.query(NewsArticle)
                .filter(NewsArticle.id.notin_(embedded_news_ids))
                .order_by(NewsArticle.published_at.desc())
                .limit(limit)
                .all()
            )
        else:
            unembedded_news = (
                db.query(NewsArticle)
                .order_by(NewsArticle.published_at.desc())
                .limit(limit)
                .all()
            )

        logger.info(f"미임베딩 뉴스: {len(unembedded_news)}건")
        return unembedded_news

    def save_to_milvus(
        self, news_list: List[NewsArticle], embeddings: List[List[float]]
    ) -> int:
        """
        뉴스 임베딩을 Milvus에 저장합니다.

        Args:
            news_list: 뉴스 리스트
            embeddings: 임베딩 벡터 리스트

        Returns:
            저장된 레코드 수
        """
        if len(news_list) != len(embeddings):
            logger.error("뉴스와 임베딩 개수가 일치하지 않습니다")
            return 0

        try:
            # Milvus 연결
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )

            # Milvus 컬렉션 로드
            collection = Collection("news_embeddings")

            # 데이터 준비
            news_ids = [news.id for news in news_list]
            stock_codes = [news.stock_code or "" for news in news_list]
            published_timestamps = [
                int(news.published_at.timestamp()) for news in news_list
            ]

            # Milvus에 삽입
            data = [
                news_ids,
                embeddings,
                stock_codes,
                published_timestamps,
            ]

            collection.insert(data)
            collection.flush()

            logger.info(f"Milvus에 {len(news_ids)}건 저장 완료")
            return len(news_ids)

        except Exception as e:
            logger.error(f"Milvus 저장 실패: {e}")
            return 0

    def embed_and_save_news(
        self, db: Session, batch_size: int = 100
    ) -> Tuple[int, int]:
        """
        미임베딩 뉴스를 임베딩하여 Milvus에 저장합니다.

        Args:
            db: 데이터베이스 세션
            batch_size: 배치 크기

        Returns:
            (성공 건수, 실패 건수) 튜플
        """
        logger.info("=" * 60)
        logger.info("🔤 뉴스 임베딩 작업 시작")
        logger.info("=" * 60)

        try:
            # 미임베딩 뉴스 조회
            unembedded_news = self.get_unembedded_news(db, limit=batch_size)

            if not unembedded_news:
                logger.info("임베딩할 뉴스가 없습니다")
                return 0, 0

            logger.info(f"임베딩 대상 뉴스: {len(unembedded_news)}건")

            # 텍스트 준비 (제목 + 본문)
            texts = [f"{news.title}\n{news.content}" for news in unembedded_news]

            # 임베딩 생성
            logger.info("OpenAI Embedding API 호출 중...")
            embeddings = self.embed_batch(texts)

            # 성공/실패 분류
            success_news = []
            success_embeddings = []
            fail_count = 0

            for news, embedding in zip(unembedded_news, embeddings):
                if embedding is not None:
                    success_news.append(news)
                    success_embeddings.append(embedding)
                else:
                    fail_count += 1
                    logger.warning(f"뉴스 ID {news.id} 임베딩 실패")

            # Milvus에 저장
            if success_embeddings:
                saved_count = self.save_to_milvus(success_news, success_embeddings)
                logger.info(
                    f"✅ 임베딩 완료: 성공 {saved_count}건, 실패 {fail_count}건"
                )
                return saved_count, fail_count
            else:
                logger.warning("저장할 임베딩이 없습니다")
                return 0, fail_count

        except Exception as e:
            logger.error(f"뉴스 임베딩 작업 중 에러: {e}", exc_info=True)
            return 0, 0


# 싱글톤 인스턴스
_news_embedder: Optional[NewsEmbedder] = None


def get_news_embedder() -> NewsEmbedder:
    """
    NewsEmbedder 싱글톤 인스턴스를 반환합니다.

    Returns:
        NewsEmbedder 인스턴스
    """
    global _news_embedder
    if _news_embedder is None:
        _news_embedder = NewsEmbedder()
    return _news_embedder


def run_daily_embedding(batch_size: int = 100) -> Tuple[int, int]:
    """
    일일 뉴스 임베딩 작업을 실행합니다.

    Args:
        batch_size: 배치 크기 (기본값: 100)

    Returns:
        (성공 건수, 실패 건수) 튜플
    """
    db = SessionLocal()
    embedder = get_news_embedder()

    try:
        return embedder.embed_and_save_news(db, batch_size=batch_size)
    finally:
        db.close()
