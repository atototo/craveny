"""
APScheduler 설정 및 크론 작업 관리

주요 스케줄:
- 1분봉 데이터 수집: 매 1분 (장 시간 09:00-15:30)
- 일봉 데이터 수집: 매일 16:00
- 리포트 생성: 매일 16:30
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from backend.utils.market_hours import is_market_open
from backend.crawlers.kis_minute_collector import run_minute_collector

logger = logging.getLogger(__name__)

# 전역 스케줄러 인스턴스
scheduler: AsyncIOScheduler = None


def get_scheduler() -> AsyncIOScheduler:
    """
    스케줄러 싱글톤 인스턴스 반환

    Returns:
        AsyncIOScheduler 인스턴스
    """
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        logger.info("📅 APScheduler 초기화 완료")
    return scheduler


async def minute_price_job():
    """
    1분봉 데이터 수집 작업

    - 실행 주기: 매 1분
    - 실행 조건: 장 시간 (09:00-15:30)
    """
    try:
        # 시장 시간 체크
        if not is_market_open():
            logger.debug("⏸️  장 시간이 아님, 1분봉 수집 스킵")
            return

        logger.info("⏰ 1분봉 데이터 수집 작업 시작")
        await run_minute_collector()

    except Exception as e:
        logger.error(f"❌ 1분봉 수집 작업 실패: {e}", exc_info=True)


def setup_jobs():
    """
    모든 스케줄 작업 등록

    작업 목록:
    - minute_price_job: 1분봉 데이터 수집 (매 1분)
    """
    sched = get_scheduler()

    # 1분봉 데이터 수집 (매 1분)
    sched.add_job(
        minute_price_job,
        trigger=IntervalTrigger(minutes=1),
        id="minute_price_collector",
        name="1분봉 데이터 수집",
        replace_existing=True,
        max_instances=1,  # 동시 실행 방지
        coalesce=True,  # 누적된 작업 병합
        misfire_grace_time=30,  # 30초 이내 지연 허용
    )

    logger.info("✅ 스케줄 작업 등록 완료")
    logger.info(f"   - 1분봉 수집: 매 1분 (장 시간만)")


def start_scheduler():
    """
    스케줄러 시작

    Returns:
        AsyncIOScheduler 인스턴스
    """
    sched = get_scheduler()

    if not sched.running:
        setup_jobs()
        sched.start()
        logger.info("🚀 APScheduler 시작 완료")

        # 등록된 작업 목록 출력
        jobs = sched.get_jobs()
        logger.info(f"📋 등록된 작업: {len(jobs)}개")
        for job in jobs:
            logger.info(f"   - {job.name} (ID: {job.id})")

    return sched


def stop_scheduler():
    """스케줄러 중지"""
    sched = get_scheduler()

    if sched.running:
        sched.shutdown(wait=True)
        logger.info("⏹️  APScheduler 중지 완료")


def get_job_status() -> dict:
    """
    스케줄러 및 작업 상태 조회

    Returns:
        상태 정보 딕셔너리
    """
    sched = get_scheduler()

    jobs = sched.get_jobs()
    job_list = []

    for job in jobs:
        job_list.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": sched.running,
        "total_jobs": len(jobs),
        "jobs": job_list,
        "market_open": is_market_open(),
    }
