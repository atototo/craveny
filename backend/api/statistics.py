"""
통계 API

시스템 전체 통계 및 성능 분석 정보를 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.scheduler.crawler_scheduler import get_crawler_scheduler


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/statistics/daily")
async def get_daily_statistics(
    days: int = Query(30, ge=1, le=365, description="조회할 일수"),
    db: Session = Depends(get_db)
):
    """
    일별 통계

    지정된 기간 동안의 일별 뉴스 수집 및 알림 발송 통계를 반환합니다.
    """
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # 일별 뉴스 생성 건수
        daily_news = db.query(
            func.date(NewsArticle.created_at).label("date"),
            func.count(NewsArticle.id).label("news_count")
        ).filter(
            NewsArticle.created_at >= start_date,
            NewsArticle.created_at <= end_date
        ).group_by(
            func.date(NewsArticle.created_at)
        ).all()

        # 일별 알림 발송 건수
        daily_notifications = db.query(
            func.date(NewsArticle.notified_at).label("date"),
            func.count(NewsArticle.id).label("notification_count")
        ).filter(
            NewsArticle.notified_at >= start_date,
            NewsArticle.notified_at <= end_date,
            NewsArticle.notified_at.isnot(None)
        ).group_by(
            func.date(NewsArticle.notified_at)
        ).all()

        # 날짜별로 매핑
        news_dict = {str(date): count for date, count in daily_news}
        notification_dict = {str(date): count for date, count in daily_notifications}

        # 전체 날짜 범위 생성
        result = []
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            result.append({
                "date": date_str,
                "news_count": news_dict.get(date_str, 0),
                "notification_count": notification_dict.get(date_str, 0),
                # TODO: 평균 신뢰도 추가 (예측 결과 테이블 필요)
                "avg_confidence": None,
            })
            current_date += timedelta(days=1)

        return result

    except Exception as e:
        logger.error(f"일별 통계 조회 실패: {e}", exc_info=True)
        raise


@router.get("/statistics/confidence-distribution")
async def get_confidence_distribution():
    """
    신뢰도 분포

    예측 신뢰도의 구간별 분포를 반환합니다.

    TODO: 예측 결과 테이블이 생기면 실제 데이터로 계산
    """
    try:
        # 현재는 더미 데이터
        return {
            "ranges": [
                {"min": 0, "max": 20, "count": 5},
                {"min": 20, "max": 40, "count": 12},
                {"min": 40, "max": 60, "count": 45},
                {"min": 60, "max": 80, "count": 120},
                {"min": 80, "max": 100, "count": 165},
            ]
        }

    except Exception as e:
        logger.error(f"신뢰도 분포 조회 실패: {e}", exc_info=True)
        raise


@router.get("/statistics/crawler")
async def get_crawler_statistics():
    """
    크롤러 통계

    뉴스 크롤링, 주가 수집, 알림 발송 등의 통계를 반환합니다.
    """
    try:
        scheduler = get_crawler_scheduler()
        stats = scheduler.get_stats()

        return {
            "news": {
                "total_crawls": stats["news"]["total_crawls"],
                "total_saved": stats["news"]["total_saved"],
                "total_skipped": stats["news"]["total_skipped"],
                "total_errors": stats["news"]["total_errors"],
                "success_rate": stats["news"]["success_rate"],
            },
            "stocks": {
                "total_crawls": stats["stock"]["total_crawls"],
                "total_stocks": stats["stock"]["total_stocks"],
                "total_saved": stats["stock"]["total_saved"],
                "total_errors": stats["stock"]["total_errors"],
                "success_rate": stats["stock"]["success_rate"],
            },
            "matching": {
                "total_runs": stats["matching"]["total_runs"],
                "total_success": stats["matching"]["total_success"],
                "total_fail": stats["matching"]["total_fail"],
                "success_rate": stats["matching"]["success_rate"],
            },
            "embedding": {
                "total_runs": stats["embedding"]["total_runs"],
                "total_success": stats["embedding"]["total_success"],
                "total_fail": stats["embedding"]["total_fail"],
                "success_rate": stats["embedding"]["success_rate"],
            },
        }

    except Exception as e:
        logger.error(f"크롤러 통계 조회 실패: {e}", exc_info=True)
        raise
