"""
Craveny FastAPI 애플리케이션 진입점
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.scheduler.crawler_scheduler import get_crawler_scheduler


# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="Craveny API",
    version="1.0.0",
    description="증권 뉴스 예측 및 텔레그램 알림 시스템",
    debug=settings.DEBUG,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from backend.api import health, prediction, dashboard, news, stocks, stock_management, ab_test, models, evaluations, auth, users
app.include_router(auth.router)  # 인증은 tags가 router에 이미 정의됨
app.include_router(users.router)  # 사용자 관리는 tags가 router에 이미 정의됨
app.include_router(health.router, tags=["Health"])
app.include_router(prediction.router, tags=["Prediction"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(news.router, tags=["News"])
app.include_router(stocks.router, tags=["Stocks"])
app.include_router(stock_management.router, tags=["Stock Management"])
app.include_router(ab_test.router, tags=["A/B Test"])
app.include_router(models.router, tags=["Models"])
app.include_router(evaluations.router, tags=["Evaluations"])


@app.on_event("startup")
async def startup_event():
    """애플리케이션 시작 이벤트"""
    logger.info(f"🚀 {settings.APP_NAME} 애플리케이션 시작")

    # APScheduler 시작 (뉴스: 10분, 주가: 1분)
    scheduler = get_crawler_scheduler(news_interval_minutes=10, stock_interval_minutes=1)
    scheduler.start()
    logger.info("✅ 크롤러 스케줄러 시작 (뉴스 + 주가)")


@app.on_event("shutdown")
async def shutdown_event():
    """애플리케이션 종료 이벤트"""
    logger.info(f"🛑 {settings.APP_NAME} 애플리케이션 종료")

    # APScheduler 종료
    scheduler = get_crawler_scheduler()
    scheduler.shutdown()
    logger.info("✅ 크롤러 스케줄러 종료 (뉴스 + 주가)")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": f"{settings.APP_NAME} API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "stats": "/stats",
    }


def main():
    """메인 진입점 - uvicorn으로 서버 실행"""
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
