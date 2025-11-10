"""
스케줄러 테스트

Usage:
    KIS_MOCK_MODE=False uv run python scripts/test_scheduler.py
"""
import asyncio
import logging
import time
from datetime import datetime

from backend.scheduler.crawler_scheduler import CrawlerScheduler
from backend.utils.market_hours import is_market_open


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_market_hours():
    """시장 시간 체크 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 시장 시간 체크 테스트")
    logger.info("=" * 80)

    now = datetime.now()
    is_open = is_market_open(now)

    logger.info(f"현재 시각: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")
    logger.info(f"장 상태: {'✅ 열림' if is_open else '⏸️  닫힘'}")

    if is_open:
        logger.info("💡 1분봉 수집이 실행됩니다")
    else:
        logger.info("💡 1분봉 수집이 스킵됩니다")

    logger.info("")


async def test_scheduler():
    """스케줄러 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 스케줄러 시작 테스트")
    logger.info("=" * 80)

    try:
        # 스케줄러 생성
        scheduler = CrawlerScheduler(
            news_interval_minutes=10,
            stock_interval_minutes=1
        )

        # 스케줄러 시작
        logger.info("\n1. 스케줄러 시작 중...")
        scheduler.start()

        # 등록된 작업 확인
        logger.info("\n2. 등록된 작업 목록:")
        jobs = scheduler.scheduler.get_jobs()
        for job in jobs:
            next_run = job.next_run_time.strftime('%H:%M:%S') if job.next_run_time else "N/A"
            logger.info(f"   - {job.name} (ID: {job.id})")
            logger.info(f"     다음 실행: {next_run}")
            logger.info(f"     트리거: {job.trigger}")

        # 통계 확인
        logger.info("\n3. 현재 통계:")
        stats = scheduler.get_stats()
        logger.info(f"   - 스케줄러 실행 중: {stats['is_running']}")
        logger.info(f"   - 뉴스 크롤링: {stats['news']['total_crawls']}회")
        logger.info(f"   - 주가 수집: {stats['stock']['total_crawls']}회")
        logger.info(f"   - KIS 일봉: {stats['kis_daily']['total_runs']}회")
        logger.info(f"   - KIS 1분봉: {stats['kis_minute']['total_runs']}회")

        # 2분 동안 대기 (1분봉 수집 1~2회 실행 확인)
        logger.info("\n4. 2분 동안 스케줄러 동작 테스트...")
        logger.info("   (1분봉 수집이 실행되는지 확인)")

        for i in range(12):  # 10초 * 12 = 2분
            await asyncio.sleep(10)
            logger.info(f"   {(i+1)*10}초 경과... (장 상태: {'열림' if is_market_open() else '닫힘'})")

        # 최종 통계 확인
        logger.info("\n5. 최종 통계:")
        stats = scheduler.get_stats()
        logger.info(f"   - KIS 1분봉 실행 횟수: {stats['kis_minute']['total_runs']}회")
        logger.info(f"   - KIS 1분봉 저장 건수: {stats['kis_minute']['total_saved']}건")
        logger.info(f"   - KIS 1분봉 에러 횟수: {stats['kis_minute']['total_errors']}회")
        logger.info(f"   - KIS 1분봉 성공률: {stats['kis_minute']['success_rate']}%")

        # 스케줄러 종료
        logger.info("\n6. 스케줄러 종료 중...")
        scheduler.shutdown()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        return False


async def main():
    """메인 실행"""
    start_time = datetime.now()

    try:
        # 1. 시장 시간 체크 테스트
        test_market_hours()

        # 2. 스케줄러 테스트
        success = await test_scheduler()

        # 소요 시간 계산
        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️  소요 시간: {elapsed.total_seconds():.1f}초")

        if success:
            logger.info("✅ 모든 테스트 통과!")
        else:
            logger.error("❌ 테스트 실패")

    except Exception as e:
        logger.error(f"❌ 실행 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
