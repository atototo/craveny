"""
뉴스 벡터 검색 모듈

Milvus에서 유사한 과거 뉴스를 검색하고, 해당 뉴스의 주가 변동률을 조회합니다.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from pymilvus import Collection, connections
from sqlalchemy.orm import Session

from backend.config import settings
from backend.llm.embedder import NewsEmbedder
from backend.db.models.news import NewsArticle
from backend.db.models.match import NewsStockMatch


logger = logging.getLogger(__name__)


class NewsVectorSearch:
    """뉴스 벡터 검색 클래스"""

    def __init__(self):
        """벡터 검색 초기화"""
        self.embedder = NewsEmbedder()
        self.collection_name = "news_embeddings"

    def search_similar_news(
        self,
        news_text: str,
        stock_code: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        유사한 과거 뉴스를 검색합니다.

        Args:
            news_text: 검색할 뉴스 텍스트
            stock_code: 종목 코드 (필터링용, 선택사항)
            top_k: 반환할 최대 개수
            similarity_threshold: 유사도 임계값 (0.0 ~ 1.0)

        Returns:
            유사 뉴스 리스트 [
                {
                    "news_id": int,
                    "similarity": float,
                    "stock_code": str,
                    "published_at": int
                },
                ...
            ]
        """
        try:
            # 1. 뉴스 텍스트 임베딩
            embedding = self.embedder.embed_text(news_text)
            if not embedding:
                logger.error("뉴스 임베딩 생성 실패")
                return []

            # 2. Milvus 연결
            connections.connect(
                alias="search",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )

            # 3. 컬렉션 로드
            collection = Collection(self.collection_name, using="search")
            collection.load()

            # 4. 검색 파라미터 설정
            search_params = {
                "metric_type": "L2",  # 유클리디안 거리
                "params": {"nprobe": 10},
            }

            # 5. 필터 표현식 (종목 코드가 있는 경우)
            expr = f'stock_code == "{stock_code}"' if stock_code else ""

            # 6. 벡터 검색
            results = collection.search(
                data=[embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k * 2,  # 임계값 필터링을 위해 여유있게 가져옴
                expr=expr,
                output_fields=["news_article_id", "stock_code", "published_timestamp"],
            )

            # 7. 결과 파싱
            similar_news = []
            if results and len(results) > 0:
                for hit in results[0]:
                    # L2 거리를 코사인 유사도로 변환
                    # L2 거리가 작을수록 유사함
                    # 유사도 = 1 / (1 + L2_distance)
                    distance = hit.distance
                    similarity = 1 / (1 + distance)

                    if similarity >= similarity_threshold:
                        similar_news.append({
                            "news_id": hit.entity.get("news_article_id"),
                            "similarity": round(similarity, 4),
                            "stock_code": hit.entity.get("stock_code"),
                            "published_at": hit.entity.get("published_timestamp"),
                        })

                    # top_k개만 반환
                    if len(similar_news) >= top_k:
                        break

            logger.info(f"유사 뉴스 검색 완료: {len(similar_news)}건 (임계값: {similarity_threshold})")
            return similar_news

        except Exception as e:
            logger.error(f"벡터 검색 실패: {e}", exc_info=True)
            return []

        finally:
            try:
                connections.disconnect("search")
            except Exception:
                pass

    def get_news_with_price_changes(
        self,
        news_text: str,
        stock_code: Optional[str] = None,
        db: Session = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        유사 뉴스와 해당 뉴스의 주가 변동률을 함께 조회합니다.

        Args:
            news_text: 검색할 뉴스 텍스트
            stock_code: 종목 코드 (필터링용)
            db: 데이터베이스 세션
            top_k: 반환할 최대 개수
            similarity_threshold: 유사도 임계값

        Returns:
            유사 뉴스 및 주가 변동률 리스트 [
                {
                    "news_id": int,
                    "similarity": float,
                    "news_title": str,
                    "news_content": str,
                    "stock_code": str,
                    "published_at": datetime,
                    "price_changes": {
                        "1d": float or None,
                        "2d": float or None,
                        "3d": float or None,
                        "5d": float or None,
                        "10d": float or None,
                        "20d": float or None
                    }
                },
                ...
            ]
        """
        # 1. 유사 뉴스 검색
        similar_news = self.search_similar_news(
            news_text=news_text,
            stock_code=stock_code,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        if not similar_news or not db:
            return []

        # 2. 뉴스 상세 정보 및 주가 변동률 조회
        enriched_news = []

        for news in similar_news:
            news_id = news["news_id"]

            # 뉴스 정보 조회
            news_article = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()
            if not news_article:
                continue

            # 주가 변동률 조회
            match = (
                db.query(NewsStockMatch)
                .filter(
                    NewsStockMatch.news_id == news_id,
                    NewsStockMatch.stock_code == news["stock_code"]
                )
                .first()
            )

            price_changes = {
                "1d": match.price_change_1d if match else None,
                "2d": match.price_change_2d if match else None,
                "3d": match.price_change_3d if match else None,
                "5d": match.price_change_5d if match else None,
                "10d": match.price_change_10d if match else None,
                "20d": match.price_change_20d if match else None,
            }

            enriched_news.append({
                "news_id": news_id,
                "similarity": news["similarity"],
                "news_title": news_article.title,
                "news_content": news_article.content[:200] + "...",  # 요약
                "stock_code": news["stock_code"],
                "published_at": news_article.published_at,
                "price_changes": price_changes,
            })

        logger.info(f"유사 뉴스 + 주가 변동률 조회 완료: {len(enriched_news)}건")
        return enriched_news


# 싱글톤 인스턴스
_vector_search: Optional[NewsVectorSearch] = None


def get_vector_search() -> NewsVectorSearch:
    """
    NewsVectorSearch 싱글톤 인스턴스를 반환합니다.

    Returns:
        NewsVectorSearch 인스턴스
    """
    global _vector_search
    if _vector_search is None:
        _vector_search = NewsVectorSearch()
    return _vector_search
