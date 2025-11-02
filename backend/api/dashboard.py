"""
대시보드 API

메인 대시보드에 필요한 요약 통계를 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.scheduler.crawler_scheduler import get_crawler_scheduler


logger = logging.getLogger(__name__)

router = APIRouter()


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/dashboard/summary")
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    대시보드 요약 통계

    오늘의 예측 수, 평균 신뢰도, 총 예측 건수, 예측 방향 분포 등을 반환합니다.
    """
    try:
        # 오늘 날짜 (UTC 기준)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. 오늘의 알림 발송 건수 (notified_at이 오늘인 것)
        today_predictions = db.query(func.count(NewsArticle.id)).filter(
            NewsArticle.notified_at >= today_start,
            NewsArticle.notified_at.isnot(None)
        ).scalar() or 0

        # 2. 전체 알림 발송 건수
        total_predictions = db.query(func.count(NewsArticle.id)).filter(
            NewsArticle.notified_at.isnot(None)
        ).scalar() or 0

        # 3. 전체 뉴스 건수 (종목 코드가 있는 것)
        total_news_with_stock = db.query(func.count(NewsArticle.id)).filter(
            NewsArticle.stock_code.isnot(None)
        ).scalar() or 0

        # 4. 최근 1시간 뉴스 건수
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_news_count = db.query(func.count(NewsArticle.id)).filter(
            NewsArticle.created_at >= one_hour_ago
        ).scalar() or 0

        # 참고: 실제 예측 방향 분포는 예측 결과 테이블이 있어야 계산 가능
        # 현재는 더미 데이터로 대체
        direction_distribution = {
            "up": 60,
            "down": 25,
            "hold": 15
        }

        return {
            "today_predictions": today_predictions,
            "total_predictions": total_predictions,
            "total_news": total_news_with_stock,
            "recent_news": recent_news_count,
            "average_confidence": 78,  # TODO: 실제 평균 신뢰도 계산 (예측 결과 테이블 필요)
            "direction_distribution": direction_distribution,
        }

    except Exception as e:
        logger.error(f"대시보드 요약 조회 실패: {e}", exc_info=True)
        raise


@router.get("/predictions/recent")
async def get_recent_predictions(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    최근 예측 목록

    최근에 알림이 발송된 뉴스 목록을 반환합니다.
    """
    try:
        # notified_at이 있는 뉴스를 최신순으로 조회
        news_list = db.query(NewsArticle).filter(
            NewsArticle.notified_at.isnot(None)
        ).order_by(
            NewsArticle.notified_at.desc()
        ).limit(limit).all()

        # 종목명 매핑
        from backend.utils.stock_mapping import get_stock_mapper
        stock_mapper = get_stock_mapper()

        result = []
        for news in news_list:
            stock_name = stock_mapper.get_company_name(news.stock_code) if news.stock_code else None

            result.append({
                "id": news.id,
                "stock_code": news.stock_code,
                "stock_name": stock_name,
                "news_title": news.title,
                "source": news.source,
                "notified_at": news.notified_at.isoformat() if news.notified_at else None,
                "created_at": news.created_at.isoformat() if news.created_at else None,
            })

        return result

    except Exception as e:
        logger.error(f"최근 예측 목록 조회 실패: {e}", exc_info=True)
        raise


@router.get("/system/status")
async def get_system_status():
    """
    시스템 상태

    크롤러, 주가 수집, 알림 시스템의 상태를 반환합니다.
    """
    try:
        scheduler = get_crawler_scheduler()
        stats = scheduler.get_stats()

        return {
            "crawler": {
                "status": "running" if scheduler.is_running else "stopped",
                "total_crawls": stats["news"]["total_crawls"],
                "total_saved": stats["news"]["total_saved"],
                "success_rate": stats["news"]["success_rate"],
            },
            "stock_collector": {
                "status": "running" if scheduler.is_running else "stopped",
                "total_crawls": stats["stock"]["total_crawls"],
                "total_saved": stats["stock"]["total_saved"],
                "success_rate": stats["stock"]["success_rate"],
            },
            "notifier": {
                "status": "running" if scheduler.is_running else "stopped",
                "total_runs": stats.get("notify", {}).get("total_runs", 0),
                "total_success": stats.get("notify", {}).get("total_success", 0),
            },
            "cache_hit_rate": 67,  # TODO: 실제 캐시 히트율 가져오기
        }

    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}", exc_info=True)
        raise
