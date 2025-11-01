"""
Health Check API

시스템 상태 및 통계 정보를 제공하는 API
"""
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from pymilvus import connections, Collection
import redis

from backend.config import settings
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.stock import StockPrice
from backend.db.models.match import NewsStockMatch
from backend.scheduler.crawler_scheduler import get_crawler_scheduler


logger = logging.getLogger(__name__)

router = APIRouter()


def check_postgres() -> Dict[str, Any]:
    """PostgreSQL 연결 상태 확인"""
    try:
        db = SessionLocal()
        # 간단한 쿼리로 연결 확인
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "error": None}
    except Exception as e:
        logger.error(f"PostgreSQL 연결 실패: {e}")
        return {"status": "unhealthy", "error": str(e)}


def check_milvus() -> Dict[str, Any]:
    """Milvus 연결 상태 확인"""
    try:
        # 기존 연결이 있으면 재사용
        try:
            connections.connect(
                alias="health_check",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
        except Exception:
            # 이미 연결되어 있으면 무시
            pass

        # 컬렉션 존재 확인
        collection = Collection("news_embeddings", using="health_check")
        collection.load()
        count = collection.num_entities

        return {
            "status": "healthy",
            "error": None,
            "embeddings_count": count
        }
    except Exception as e:
        logger.error(f"Milvus 연결 실패: {e}")
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> Dict[str, Any]:
    """Redis 연결 상태 확인"""
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
        r.ping()
        return {"status": "healthy", "error": None}
    except Exception as e:
        logger.error(f"Redis 연결 실패: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health")
async def health_check():
    """
    시스템 전체 헬스 체크

    Returns:
        시스템 상태 정보
    """
    postgres = check_postgres()
    milvus = check_milvus()
    redis_check = check_redis()

    # 전체 상태 판단
    overall_healthy = all([
        postgres["status"] == "healthy",
        milvus["status"] == "healthy",
        redis_check["status"] == "healthy",
    ])

    return {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "postgres": postgres,
            "milvus": milvus,
            "redis": redis_check,
        }
    }


@router.get("/health/liveness")
async def liveness():
    """
    Liveness Probe (Kubernetes용)

    애플리케이션이 살아있는지 확인
    """
    return {"status": "alive"}


@router.get("/health/readiness")
async def readiness():
    """
    Readiness Probe (Kubernetes용)

    애플리케이션이 요청을 처리할 준비가 되었는지 확인
    """
    postgres = check_postgres()

    if postgres["status"] != "healthy":
        raise HTTPException(status_code=503, detail="Database not ready")

    return {"status": "ready"}


@router.get("/stats")
async def get_stats():
    """
    시스템 통계 정보

    Returns:
        뉴스, 주가, 매칭 통계
    """
    db = SessionLocal()

    try:
        # 뉴스 통계
        total_news = db.query(NewsArticle).count()
        news_by_stock = db.query(
            NewsArticle.stock_code,
            text("COUNT(*) as count")
        ).filter(
            NewsArticle.stock_code.isnot(None)
        ).group_by(
            NewsArticle.stock_code
        ).all()

        # 주가 통계
        total_stock_prices = db.query(StockPrice).count()
        stock_codes = db.query(StockPrice.stock_code).distinct().count()

        # 매칭 통계
        total_matches = db.query(NewsStockMatch).count()

        # Milvus 임베딩 통계
        try:
            connections.connect(
                alias="stats",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            collection = Collection("news_embeddings")
            embeddings_count = collection.num_entities
            connections.disconnect("stats")
        except Exception as e:
            logger.warning(f"Milvus 통계 조회 실패: {e}")
            embeddings_count = 0

        # 스케줄러 통계
        scheduler = get_crawler_scheduler()
        scheduler_stats = {
            "news_crawler": {
                "total_crawls": scheduler.news_total_crawls,
                "total_saved": scheduler.news_total_saved,
                "total_skipped": scheduler.news_total_skipped,
                "total_errors": scheduler.news_total_errors,
            },
            "stock_crawler": {
                "total_crawls": scheduler.stock_total_crawls,
                "total_stocks": scheduler.stock_total_stocks,
                "total_saved": scheduler.stock_total_saved,
                "total_errors": scheduler.stock_total_errors,
            },
            "matching": {
                "total_runs": scheduler.matching_total_runs,
                "total_success": scheduler.matching_total_success,
                "total_fail": scheduler.matching_total_fail,
            },
            "embedding": {
                "total_runs": scheduler.embedding_total_runs,
                "total_success": scheduler.embedding_total_success,
                "total_fail": scheduler.embedding_total_fail,
            },
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "database": {
                "news": {
                    "total": total_news,
                    "by_stock": dict(news_by_stock) if news_by_stock else {},
                },
                "stock_prices": {
                    "total": total_stock_prices,
                    "stock_codes": stock_codes,
                },
                "matches": total_matches,
            },
            "milvus": {
                "embeddings": embeddings_count,
            },
            "scheduler": scheduler_stats,
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()
