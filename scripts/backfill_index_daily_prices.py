"""
업종/지수 일자별 데이터 백필 스크립트

KIS API를 사용하여 과거 업종/지수 일봉 데이터를 채웁니다.
최대 100일치 데이터를 수집할 수 있습니다.

Usage:
    # 기본: 최근 100일 데이터 수집
    uv run python scripts/backfill_index_daily_prices.py

    # 특정 기간 지정
    uv run python scripts/backfill_index_daily_prices.py --days 30
"""
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.crawlers.index_daily_collector import IndexDailyCollector


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """백필 메인 함수"""
    parser = argparse.ArgumentParser(description="업종/지수 일자별 데이터 백필")
    parser.add_argument(
        "--days",
        type=int,
        default=100,
        help="수집할 일수 (기본: 100일, 최대: 100일)"
    )
    args = parser.parse_args()

    # 최대 100일 제한
    days = min(args.days, 100)

    logger.info("=" * 80)
    logger.info("🚀 업종/지수 일자별 데이터 백필 시작")
    logger.info(f"📅 수집 기간: 최근 {days}일")
    logger.info("=" * 80)

    # 시작/종료 날짜 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    logger.info(f"📊 기간: {start_str} ~ {end_str}")

    # 수집 시작
    collector = IndexDailyCollector(batch_size=5)

    try:
        result = await collector.collect_range(
            start_date=start_str,
            end_date=end_str,
            max_days=days
        )

        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 백필 완료 요약")
        logger.info("=" * 80)
        logger.info(f"✅ 성공: {result['collected']}건")
        logger.info(f"❌ 실패: {result['failed']}건")
        logger.info("")

        # 개별 지수별 결과 출력
        logger.info("📋 지수별 결과:")
        logger.info("-" * 80)

        success_list = [r for r in result['results'] if r.get('status') == 'success']
        failed_list = [r for r in result['results'] if r.get('status') == 'error']

        for item in success_list:
            index_name = item.get('index_name', '?')
            index_code = item.get('index_code', '?')
            saved = item.get('saved', 0)
            logger.info(f"  ✅ {index_name:10s} ({index_code}) - {saved}건")

        if failed_list:
            logger.info("")
            logger.info("❌ 실패 목록:")
            for item in failed_list:
                index_name = item.get('index_name', '?')
                index_code = item.get('index_code', '?')
                message = item.get('message', 'Unknown error')
                logger.info(f"  ❌ {index_name:10s} ({index_code}) - {message}")

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ 백필 작업 완료!")
        logger.info("=" * 80)

        return result['failed'] == 0

    except Exception as e:
        logger.error(f"❌ 백필 중 오류 발생: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
