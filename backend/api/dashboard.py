"""
대시보드 API

메인 대시보드에 필요한 요약 통계를 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.stock import Stock, StockPrice
from backend.db.models.market_data import StockCurrentPrice, InvestorTrading, StockInfo
from backend.db.models.prediction import Prediction
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


@router.post("/reports/force-update/{stock_code}")
async def force_update_single_stock(
    stock_code: str,
    db: Session = Depends(get_db)
):
    """
    특정 종목 리포트 강제 업데이트

    Args:
        stock_code: 종목 코드

    Returns:
        업데이트 결과 (성공 여부, 메시지)
    """
    try:
        from backend.services.stock_analysis_service import update_stock_analysis_summary

        logger.info(f"종목 {stock_code} 리포트 강제 업데이트 시작")

        result = await update_stock_analysis_summary(
            stock_code,
            db,
            force_update=True
        )

        if result:
            logger.info(f"✅ 종목 {stock_code} 리포트 업데이트 성공")

            # 생성된 리포트 데이터를 직접 반환
            from backend.services.stock_analysis_service import get_stock_analysis_summary
            updated_summary = get_stock_analysis_summary(stock_code, db)

            return {
                "success": True,
                "message": f"종목 {stock_code} 리포트가 성공적으로 업데이트되었습니다.",
                "last_updated": result.last_updated.isoformat() if result.last_updated else None,
                "prediction_count": result.based_on_prediction_count,
                "analysis_summary": updated_summary  # 생성된 리포트 데이터 포함
            }
        else:
            logger.warning(f"❌ 종목 {stock_code} 리포트 업데이트 실패")
            return {
                "success": False,
                "message": f"종목 {stock_code} 리포트 생성 실패 (예측 부족 또는 LLM 오류)"
            }

    except Exception as e:
        logger.error(f"종목 {stock_code} 리포트 업데이트 오류: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"오류 발생: {str(e)}"
        }


@router.get("/dashboard/data-check")
async def check_data_availability(db: Session = Depends(get_db)):
    """데이터 존재 여부 확인"""
    try:
        stock_prices_count = db.query(func.count(StockPrice.id)).scalar()
        predictions_count = db.query(func.count(Prediction.id)).scalar()
        investor_count = db.query(func.count(InvestorTrading.id)).scalar()

        latest_price = db.query(StockPrice).order_by(StockPrice.date.desc()).first()
        latest_prediction = db.query(Prediction).order_by(Prediction.created_at.desc()).first()
        latest_investor = db.query(InvestorTrading).order_by(InvestorTrading.date.desc()).first()

        # 최신 주가 데이터 샘플 (종목별 최신 데이터)
        subq = db.query(
            StockPrice.stock_code,
            func.max(StockPrice.date).label('max_date')
        ).group_by(StockPrice.stock_code).subquery()

        latest_prices = db.query(StockPrice).join(
            subq,
            (StockPrice.stock_code == subq.c.stock_code) &
            (StockPrice.date == subq.c.max_date)
        ).limit(5).all()

        sample_prices = []
        for p in latest_prices:
            sample_prices.append({
                "stock_code": p.stock_code,
                "date": p.date.isoformat(),
                "open": p.open,
                "close": p.close,
                "has_open": p.open is not None and p.open > 0
            })

        return {
            "stock_prices": {
                "count": stock_prices_count,
                "latest_date": latest_price.date.isoformat() if latest_price else None
            },
            "predictions": {
                "count": predictions_count,
                "latest_date": latest_prediction.created_at.isoformat() if latest_prediction else None
            },
            "investor_trading": {
                "count": investor_count,
                "latest_date": latest_investor.date.isoformat() if latest_investor else None
            },
            "sample_latest_prices": sample_prices,
            "total_latest_stocks": db.query(func.count(func.distinct(StockPrice.stock_code))).scalar()
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/dashboard/market-momentum")
async def get_market_momentum(db: Session = Depends(get_db)):
    """
    실시간 시장 모멘텀 데이터 (KIS API 기반)

    급등/급락 종목, 투자자 동향, AI 시그널 등을 반환합니다.
    """
    try:
        from backend.crawlers.kis_client import get_kis_client
        from backend.utils.stock_mapping import get_stock_mapper

        stock_mapper = get_stock_mapper()

        # KIS API Client
        kis_client = await get_kis_client()

        # 1. 급등/급락 종목 조회 (변동율순 - 급등/급락 모두 포함)
        movers_response = await kis_client.get_top_movers(
            market="0000",  # 전체 시장
            sort_type="4"   # 변동율 (변동폭이 큰 순서)
        )

        def process_stock(stock):
            """종목 데이터 처리"""
            stock_code = stock["stck_shrn_iscd"]
            change_rate = float(stock["prdy_ctrt"])

            # AI 시그널 조회 (우리 DB)
            positive_signals = db.query(func.count(Prediction.id)).filter(
                Prediction.stock_code == stock_code,
                Prediction.sentiment_direction == 'positive'
            ).scalar() or 0

            negative_signals = db.query(func.count(Prediction.id)).filter(
                Prediction.stock_code == stock_code,
                Prediction.sentiment_direction == 'negative'
            ).scalar() or 0

            avg_sentiment = db.query(func.avg(Prediction.sentiment_score)).filter(
                Prediction.stock_code == stock_code,
                Prediction.sentiment_score.isnot(None)
            ).scalar()

            return {
                'stock_code': stock_code,
                'stock_name': stock["hts_kor_isnm"],
                'change_rate': change_rate,
                'current_price': int(stock["stck_prpr"]),
                'ai_signals': positive_signals + negative_signals,
                'positive_signals': positive_signals,
                'negative_signals': negative_signals,
                'confidence': int(avg_sentiment * 100) if avg_sentiment else None
            }

        # 변동율순 데이터를 급등/급락으로 분리
        all_movers = []
        if movers_response.get("rt_cd") == "0":
            for stock in movers_response.get("output", []):
                all_movers.append(process_stock(stock))

        # 급등/급락 분리
        gainers = sorted([m for m in all_movers if m['change_rate'] > 0],
                        key=lambda x: x['change_rate'], reverse=True)
        losers = sorted([m for m in all_movers if m['change_rate'] < 0],
                       key=lambda x: x['change_rate'])

        top_gainers = gainers[:5]
        top_losers = losers[:5]

        # 2. 투자자 동향 (최근 데이터)
        # 종목별 가장 최근 데이터 조회
        investor_subq = db.query(
            InvestorTrading.stock_code,
            func.max(InvestorTrading.date).label('max_date')
        ).group_by(InvestorTrading.stock_code).subquery()

        investor_data = db.query(InvestorTrading).join(
            investor_subq,
            (InvestorTrading.stock_code == investor_subq.c.stock_code) &
            (InvestorTrading.date == investor_subq.c.max_date)
        ).all()

        # 종목별 외국인/기관 순매수 집계
        foreign_net = {}
        institution_net = {}

        for data in investor_data:
            stock_name = stock_mapper.get_company_name(data.stock_code)
            if data.frgn_ntby_tr_pbmn:
                foreign_net[data.stock_code] = {
                    'name': stock_name or data.stock_code,
                    'amount': data.frgn_ntby_tr_pbmn
                }
            if data.orgn_ntby_tr_pbmn:
                institution_net[data.stock_code] = {
                    'name': stock_name or data.stock_code,
                    'amount': data.orgn_ntby_tr_pbmn
                }

        # 상위 3개씩
        top_foreign = sorted(foreign_net.items(),
                           key=lambda x: x[1]['amount'], reverse=True)[:3]
        top_institution = sorted(institution_net.items(),
                                key=lambda x: x[1]['amount'], reverse=True)[:3]

        # 3. AI 시그널이 많은 종목 TOP 5 (섹터 대신)
        # 전체 기간 AI 시그널 많은 종목
        signal_counts = db.query(
            Prediction.stock_code,
            func.count(Prediction.id).label('total'),
            func.sum(case(
                (Prediction.sentiment_direction == 'positive', 1),
                else_=0
            )).label('positive'),
            func.sum(case(
                (Prediction.sentiment_direction == 'negative', 1),
                else_=0
            )).label('negative')
        ).group_by(
            Prediction.stock_code
        ).order_by(
            func.count(Prediction.id).desc()
        ).limit(5).all()

        sector_trends = []
        for row in signal_counts:
            stock_name = stock_mapper.get_company_name(row.stock_code)
            sentiment = 'positive' if row.positive > row.negative else 'negative'
            sector_trends.append({
                'sector': stock_name or row.stock_code,  # 종목명을 섹터처럼 표시
                'positive_signals': row.positive or 0,
                'negative_signals': row.negative or 0,
                'total_signals': row.total,
                'sentiment': sentiment
            })

        return {
            'top_gainers': top_gainers,
            'top_losers': top_losers,
            'foreign_buying': [
                {'stock_code': code, 'stock_name': data['name'], 'amount': data['amount']}
                for code, data in top_foreign
            ],
            'institution_buying': [
                {'stock_code': code, 'stock_name': data['name'], 'amount': data['amount']}
                for code, data in top_institution
            ],
            'sector_trends': sector_trends
        }

    except Exception as e:
        logger.error(f"시장 모멘텀 조회 실패: {e}", exc_info=True)
        # 에러 시 빈 데이터 반환
        return {
            'top_gainers': [],
            'top_losers': [],
            'foreign_buying': [],
            'institution_buying': [],
            'sector_trends': []
        }


@router.post("/reports/force-update")
async def force_update_stale_reports(
    ttl_hours: float = 6.0,
    db: Session = Depends(get_db)
):
    """
    오래된 리포트 강제 업데이트

    버튼 누른 시점 기준으로 TTL 초과한 리포트를 강제 업데이트합니다.

    Args:
        ttl_hours: 업데이트 기준 시간 (기본 6시간)

    Returns:
        업데이트 통계 (검사 종목 수, 업데이트 필요 종목 수, 성공/실패 개수)
    """
    try:
        from backend.db.models.stock_analysis import StockAnalysisSummary
        from backend.services.stock_analysis_service import update_stock_analysis_summary
        from backend.utils.stock_mapping import get_stock_mapper
        import asyncio

        logger.info(f"리포트 강제 업데이트 시작 (TTL: {ttl_hours}시간)")

        # 모든 리포트 조회
        summaries = db.query(StockAnalysisSummary).all()
        stock_mapper = get_stock_mapper()

        now = datetime.utcnow()
        stale_stocks = []

        # 오래된 리포트 찾기
        for summary in summaries:
            if summary.last_updated:
                age_hours = (now - summary.last_updated).total_seconds() / 3600
                if age_hours > ttl_hours:
                    stock_name = stock_mapper.get_company_name(summary.stock_code)
                    stale_stocks.append({
                        'code': summary.stock_code,
                        'name': stock_name or summary.stock_code,
                        'age_hours': age_hours
                    })
            else:
                stock_name = stock_mapper.get_company_name(summary.stock_code)
                stale_stocks.append({
                    'code': summary.stock_code,
                    'name': stock_name or summary.stock_code,
                    'age_hours': 999
                })

        # 나이순으로 정렬 (가장 오래된 것부터)
        stale_stocks.sort(key=lambda x: x['age_hours'], reverse=True)

        logger.info(f"총 {len(summaries)}개 종목 중 {len(stale_stocks)}개 업데이트 필요")

        if not stale_stocks:
            return {
                "total_stocks": len(summaries),
                "stale_stocks": 0,
                "updated": 0,
                "failed": 0,
                "message": "모든 리포트가 최신 상태입니다."
            }

        # 순차적으로 업데이트
        success_count = 0
        fail_count = 0

        for stock in stale_stocks:
            try:
                result = await update_stock_analysis_summary(
                    stock['code'],
                    db,
                    force_update=True
                )

                if result:
                    success_count += 1
                    logger.info(f"✅ {stock['name']} ({stock['code']}) 업데이트 성공")
                else:
                    fail_count += 1
                    logger.warning(f"❌ {stock['name']} ({stock['code']}) 업데이트 실패")

                # API rate limit 고려
                await asyncio.sleep(0.5)

            except Exception as e:
                fail_count += 1
                logger.error(f"❌ {stock['name']} ({stock['code']}) 오류: {e}")

        logger.info(f"리포트 강제 업데이트 완료: 성공 {success_count}개, 실패 {fail_count}개")

        return {
            "total_stocks": len(summaries),
            "stale_stocks": len(stale_stocks),
            "updated": success_count,
            "failed": fail_count,
            "message": f"업데이트 완료: 성공 {success_count}개, 실패 {fail_count}개"
        }

    except Exception as e:
        logger.error(f"리포트 강제 업데이트 실패: {e}", exc_info=True)
        raise
