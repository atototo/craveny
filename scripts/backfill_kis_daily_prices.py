"""
KIS API 과거 90일 데이터 백필 스크립트

Usage:
    uv run python scripts/backfill_kis_daily_prices.py [--days 90]
"""
import asyncio
import logging
import argparse
from datetime import datetime

from backend.crawlers.kis_daily_crawler import get_kis_daily_crawler
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def backfill_kis_data(days: int = 90):
    """
    KIS API 과거 데이터 백필

    Args:
        days: 백필 기간 (일)
    """
    logger.info("=" * 80)
    logger.info(f"🚀 KIS API 과거 {days}일 데이터 백필 시작")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 활성 종목 수 확인
        active_stocks = db.query(Stock).filter(Stock.is_active == True).count()
        logger.info(f"📊 활성 종목 수: {active_stocks}개")
        logger.info(f"📅 백필 기간: {days}일")

        expected_records = active_stocks * days * 0.7  # 주말 제외
        logger.info(f"🎯 예상 수집 건수: 약 {int(expected_records):,}건")
        logger.info("")

        # 백필 실행
        crawler = get_kis_daily_crawler()
        result = await crawler.backfill_historical_data(days=days)

        # 결과 출력
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 백필 결과 요약")
        logger.info("=" * 80)
        logger.info(f"총 종목 수: {result['total_stocks']}개")
        logger.info(f"성공: {result['success_count']}개")
        logger.info(f"실패: {result['failed_count']}개")
        logger.info(f"성공률: {result['success_rate']:.1f}%")
        logger.info(f"총 저장 건수: {result['total_saved']:,}건")
        logger.info("")

        # 실패한 종목 체크 (있다면)
        failed_stocks = [r for r in result['results'] if r['status'] != 'success']
        if failed_stocks:
            logger.warning(f"⚠️  실패한 종목 ({len(failed_stocks)}개):")
            for r in failed_stocks[:10]:  # 최대 10개만 표시
                logger.warning(f"  - {r['stock_code']}: {r.get('error', 'Unknown error')}")

            if len(failed_stocks) > 10:
                logger.warning(f"  ... 외 {len(failed_stocks) - 10}개")

        logger.info("=" * 80)

        # 성공 기준 확인
        if result['success_rate'] >= 99.0:
            logger.info("✅ 백필 완료! (성공률 ≥99%)")
            return True
        else:
            logger.warning(f"⚠️  성공률 {result['success_rate']:.1f}% - 목표 99% 미달")
            return False

    except Exception as e:
        logger.error(f"❌ 백필 중 에러 발생: {e}", exc_info=True)
        return False

    finally:
        db.close()


async def verify_backfill(days: int = 90):
    """
    백필 결과 검증

    Args:
        days: 백필 기간 (일)
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("🔍 백필 결과 검증")
    logger.info("=" * 80)

    from datetime import timedelta
    from sqlalchemy import and_, func
    from backend.db.models.stock import StockPrice

    db = SessionLocal()

    try:
        # KIS 소스 데이터 통계
        start_date = datetime.now() - timedelta(days=days)

        total_records = db.query(func.count(StockPrice.id)).filter(
            and_(
                StockPrice.source == "kis",
                StockPrice.date >= start_date
            )
        ).scalar()

        unique_stocks = db.query(func.count(func.distinct(StockPrice.stock_code))).filter(
            and_(
                StockPrice.source == "kis",
                StockPrice.date >= start_date
            )
        ).scalar()

        logger.info(f"📊 DB 저장 현황:")
        logger.info(f"  총 레코드 수: {total_records:,}건")
        logger.info(f"  종목 수: {unique_stocks}개")
        logger.info(f"  종목당 평균: {total_records / unique_stocks:.1f}건" if unique_stocks > 0 else "  종목당 평균: 0건")

        # 최근 데이터 샘플 확인
        latest_prices = db.query(StockPrice).filter(
            StockPrice.source == "kis"
        ).order_by(StockPrice.date.desc()).limit(5).all()

        logger.info(f"\n최근 데이터 샘플 (KIS 소스):")
        for price in latest_prices:
            logger.info(
                f"  {price.stock_code} - {price.date.date()}: "
                f"종가 {price.close:,}원, 거래량 {price.volume:,}주"
            )

        logger.info("=" * 80)

        return total_records > 0

    except Exception as e:
        logger.error(f"❌ 검증 중 에러 발생: {e}", exc_info=True)
        return False

    finally:
        db.close()


async def main():
    """메인 실행"""
    parser = argparse.ArgumentParser(description="KIS API 과거 데이터 백필")
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="백필 기간 (일, 기본: 90)"
    )
    args = parser.parse_args()

    start_time = datetime.now()

    try:
        # 백필 실행
        success = await backfill_kis_data(days=args.days)

        # 검증
        if success:
            verified = await verify_backfill(days=args.days)

            if verified:
                logger.info("\n✅ 백필 및 검증 완료!")
            else:
                logger.warning("\n⚠️  백필 완료했으나 검증 실패")
        else:
            logger.error("\n❌ 백필 실패")

        # 소요 시간 계산
        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️  소요 시간: {elapsed.total_seconds():.1f}초")

    except Exception as e:
        logger.error(f"\n❌ 실행 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
