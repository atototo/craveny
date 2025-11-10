"""
1분봉 수집기 테스트

Usage:
    KIS_MOCK_MODE=False uv run python scripts/test_minute_collector.py
"""
import asyncio
import logging
from datetime import datetime

from backend.crawlers.kis_minute_collector import MinutePriceCollector
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_minute_collector():
    """1분봉 수집기 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 1분봉 수집기 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 상위 5개 종목만 테스트
        stocks = db.query(Stock).filter(
            Stock.is_active == True
        ).order_by(Stock.priority).limit(5).all()

        stock_codes = [stock.code for stock in stocks]

        logger.info(f"\n📊 테스트 종목 ({len(stock_codes)}개):")
        for stock in stocks:
            logger.info(f"  - {stock.code}: {stock.name} (우선순위: {stock.priority})")

        # 수집기 생성
        collector = MinutePriceCollector(batch_size=3)

        # 수집 실행
        result = await collector.collect_all_stocks(stock_codes)

        # 결과 확인
        logger.info("\n" + "=" * 80)
        logger.info("📊 테스트 결과")
        logger.info("=" * 80)
        logger.info(f"총 종목: {result['total_stocks']}개")
        logger.info(f"저장 건수: {result['total_saved']}건")
        logger.info(f"실패: {result['failed_count']}개")
        logger.info(f"스킵: {result['skipped_count']}개")

        # 종목별 결과
        logger.info("\n종목별 결과:")
        for r in result['results']:
            status_emoji = "✅" if r['status'] == 'success' else "⚠️" if r['status'] == 'skipped' else "❌"
            logger.info(
                f"  {status_emoji} {r['stock_code']}: "
                f"{r['status']} (저장: {r['saved']}건)"
            )

        # DB 검증
        logger.info("\n" + "=" * 80)
        logger.info("🔍 DB 저장 검증")
        logger.info("=" * 80)

        from backend.db.models.stock import StockPriceMinute
        from sqlalchemy import func

        for stock_code in stock_codes:
            count = db.query(func.count(StockPriceMinute.id)).filter(
                StockPriceMinute.stock_code == stock_code
            ).scalar()

            logger.info(f"  {stock_code}: {count}건")

            # 최근 데이터 샘플
            latest = db.query(StockPriceMinute).filter(
                StockPriceMinute.stock_code == stock_code
            ).order_by(StockPriceMinute.datetime.desc()).first()

            if latest:
                logger.info(
                    f"    최근: {latest.datetime} - "
                    f"종가 {latest.close:,.0f}원, 거래량 {latest.volume:,}주"
                )

        logger.info("\n" + "=" * 80)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        return False

    finally:
        db.close()


async def main():
    """메인 실행"""
    start_time = datetime.now()

    try:
        success = await test_minute_collector()

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
