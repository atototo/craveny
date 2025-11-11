"""
뉴스 API

뉴스 목록 조회, 검색, 필터링 기능을 제공합니다.
"""
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.utils.stock_mapping import get_stock_mapper


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/news")


def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
async def get_news_list(
    page: int = Query(1, ge=1, description="페이지 번호"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    search: Optional[str] = Query(None, description="검색어 (제목/내용)"),
    stock_code: Optional[str] = Query(None, description="종목 코드 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    has_stock: Optional[bool] = Query(None, description="종목 코드 유무 필터"),
    notified: Optional[bool] = Query(None, description="알림 발송 여부 필터"),
    source: Optional[str] = Query(None, description="출처 필터"),
    sort_by: str = Query("created_at", description="정렬 기준"),
    sort_order: str = Query("desc", description="정렬 순서 (asc/desc)"),
    db: Session = Depends(get_db)
):
    """
    뉴스 목록 조회

    검색, 필터링, 정렬, 페이지네이션을 지원합니다.
    """
    try:
        # 기본 쿼리
        query = db.query(NewsArticle)

        # 검색어 필터
        if search:
            search_filter = or_(
                NewsArticle.title.ilike(f"%{search}%"),
                NewsArticle.content.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # 종목 코드 필터
        if stock_code:
            query = query.filter(NewsArticle.stock_code == stock_code)

        # 종목 코드 유무 필터
        if has_stock is not None:
            if has_stock:
                query = query.filter(NewsArticle.stock_code.isnot(None))
            else:
                query = query.filter(NewsArticle.stock_code.is_(None))

        # 알림 발송 여부 필터
        if notified is not None:
            if notified:
                query = query.filter(NewsArticle.notified_at.isnot(None))
            else:
                query = query.filter(NewsArticle.notified_at.is_(None))

        # 출처 필터
        if source:
            query = query.filter(NewsArticle.source.ilike(f"%{source}%"))

        # 날짜 범위 필터
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(NewsArticle.published_at >= start_dt)

        if end_date:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(NewsArticle.published_at <= end_dt)

        # 총 개수 (페이지네이션용)
        total_count = query.count()

        # 정렬
        sort_column = getattr(NewsArticle, sort_by, NewsArticle.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # 페이지네이션
        offset = (page - 1) * limit
        news_list = query.offset(offset).limit(limit).all()

        # 종목명 매핑
        stock_mapper = get_stock_mapper()

        result = []
        for news in news_list:
            stock_name = stock_mapper.get_company_name(news.stock_code) if news.stock_code else None

            result.append({
                "id": news.id,
                "title": news.title,
                "content": news.content[:200] + "..." if len(news.content) > 200 else news.content,
                "url": "#",  # URL 필드가 없으므로 임시값
                "source": news.source,
                "published_at": news.published_at.isoformat() if news.published_at else None,
                "stock_code": news.stock_code,
                "stock_name": stock_name,
                "notified": news.notified_at is not None,
                "notified_at": news.notified_at.isoformat() if news.notified_at else None,
                "created_at": news.created_at.isoformat() if news.created_at else None,
                "prediction_direction": None,  # TODO: 예측 결과 저장 후 조회하도록 개선 필요
                "prediction_confidence": None,  # TODO: 예측 결과 저장 후 조회하도록 개선 필요
            })

        # 페이지 정보
        total_pages = (total_count + limit - 1) // limit

        return {
            "items": result,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": total_pages,
        }

    except Exception as e:
        logger.error(f"뉴스 목록 조회 실패: {e}", exc_info=True)
        raise


@router.get("/{news_id}")
async def get_news_detail(
    news_id: int,
    db: Session = Depends(get_db)
):
    """
    뉴스 상세 조회

    특정 뉴스의 전체 정보를 반환합니다.
    """
    try:
        news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()

        if not news:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다")

        # 종목명 매핑
        from backend.utils.stock_mapping import get_stock_mapper
        stock_mapper = get_stock_mapper()
        stock_name = stock_mapper.get_company_name(news.stock_code) if news.stock_code else None

        return {
            "id": news.id,
            "title": news.title,
            "content": news.content,
            "source": news.source,
            "url": news.url,
            "published_at": news.published_at.isoformat() if news.published_at else None,
            "stock_code": news.stock_code,
            "stock_name": stock_name,
            "notified_at": news.notified_at.isoformat() if news.notified_at else None,
            "created_at": news.created_at.isoformat() if news.created_at else None,
            "updated_at": news.updated_at.isoformat() if news.updated_at else None,
        }

    except Exception as e:
        logger.error(f"뉴스 상세 조회 실패: {e}", exc_info=True)
        raise
