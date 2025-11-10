"""
KIS 일봉 수집기 테스트 스크립트

Usage:
    uv run python scripts/test_kis_daily_collector.py
"""
import asyncio
import logging
from datetime import datetime, timedelta

from backend.crawlers.kis_daily_crawler import get_kis_daily_crawler
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock, StockPrice


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_single_stock():
    """
    단일 종목 일봉 수집 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: 단일 종목 일봉 수집 (삼성전자)")
    logger.info("=" * 80)

    crawler = get_kis_daily_crawler()

    try:
        # 삼성전자 최근 30일 데이터 수집
        result = await crawler.collect_stock(
            stock_code="005930",
            days=30
        )

        logger.info(f"\n✅ 테스트 결과:")
        logger.info(f"   - 종목: {result['stock_code']}")
        logger.info(f"   - 상태: {result['status']}")
        logger.info(f"   - 저장: {result['count']}건")

        if result["status"] == "success":
            logger.info("✅ TEST 1 성공!")
        else:
            logger.error(f"❌ TEST 1 실패: {result.get('error', 'Unknown error')}")

    except Exception as e:
        logger.error(f"❌ TEST 1 예외 발생: {e}", exc_info=True)


async def test_batch_collection():
    """
    배치 수집 테스트 (Priority 1 종목만)
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: 배치 수집 (Priority 1 종목)")
    logger.info("=" * 80)

    db = SessionLocal()
    crawler = get_kis_daily_crawler()

    try:
        # Priority 1 종목만 조회
        stocks = db.query(Stock).filter(
            Stock.is_active == True,
            Stock.priority == 1
        ).all()

        stock_codes = [stock.code for stock in stocks[:3]]  # 처음 3개만 테스트
        logger.info(f"테스트 대상 종목: {len(stock_codes)}개")

        # 배치 수집
        results = []
        for stock_code in stock_codes:
            result = await crawler.collect_stock(stock_code, days=30, db=db)
            results.append(result)

        # 결과 요약
        success_count = sum(1 for r in results if r["status"] == "success")
        total_saved = sum(r["count"] for r in results)

        logger.info(f"\n✅ 배치 테스트 결과:")
        logger.info(f"   - 성공: {success_count}/{len(stock_codes)}개 종목")
        logger.info(f"   - 저장: {total_saved}건")

        if success_count == len(stock_codes):
            logger.info("✅ TEST 2 성공!")
        else:
            logger.warning(f"⚠️  TEST 2 부분 성공: {success_count}/{len(stock_codes)}")

    except Exception as e:
        logger.error(f"❌ TEST 2 예외 발생: {e}", exc_info=True)

    finally:
        db.close()


async def test_data_verification():
    """
    DB 저장 데이터 검증 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: 데이터 검증 (삼성전자)")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 삼성전자 KIS 데이터 조회
        kis_prices = db.query(StockPrice).filter(
            StockPrice.stock_code == "005930",
            StockPrice.source == "kis"
        ).order_by(StockPrice.date.desc()).limit(5).all()

        if kis_prices:
            logger.info(f"✅ DB에서 {len(kis_prices)}건 조회 성공")
            logger.info("\n최근 5일 데이터:")
            for price in kis_prices:
                logger.info(
                    f"  - {price.date.date()}: "
                    f"시가 {price.open:,}원, "
                    f"종가 {price.close:,}원, "
                    f"거래량 {price.volume:,}주"
                )

            logger.info("✅ TEST 3 성공!")
        else:
            logger.warning("⚠️  KIS 데이터가 DB에 없습니다")

    except Exception as e:
        logger.error(f"❌ TEST 3 예외 발생: {e}", exc_info=True)

    finally:
        db.close()


async def test_source_comparison():
    """
    FDR vs KIS 데이터 비교 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: FDR vs KIS 데이터 비교")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 동일 날짜 FDR, KIS 데이터 조회
        target_date = datetime.now() - timedelta(days=1)

        fdr_price = db.query(StockPrice).filter(
            StockPrice.stock_code == "005930",
            StockPrice.source == "fdr",
            StockPrice.date >= target_date.replace(hour=0, minute=0, second=0),
            StockPrice.date < target_date.replace(hour=23, minute=59, second=59)
        ).first()

        kis_price = db.query(StockPrice).filter(
            StockPrice.stock_code == "005930",
            StockPrice.source == "kis",
            StockPrice.date >= target_date.replace(hour=0, minute=0, second=0),
            StockPrice.date < target_date.replace(hour=23, minute=59, second=59)
        ).first()

        if fdr_price and kis_price:
            logger.info("✅ 양쪽 데이터 모두 존재")
            logger.info(f"\n📊 FDR vs KIS 비교 ({target_date.date()}):")
            logger.info(f"  FDR - 종가: {fdr_price.close:,}원, 거래량: {fdr_price.volume:,}주")
            logger.info(f"  KIS - 종가: {kis_price.close:,}원, 거래량: {kis_price.volume:,}주")

            close_diff = abs(fdr_price.close - kis_price.close)
            volume_diff = abs(fdr_price.volume - kis_price.volume) if fdr_price.volume and kis_price.volume else 0

            logger.info(f"\n  종가 차이: {close_diff:,}원")
            logger.info(f"  거래량 차이: {volume_diff:,}주")

            if close_diff < 100:  # 100원 이내 차이면 정상
                logger.info("✅ TEST 4 성공! (데이터 일치)")
            else:
                logger.warning(f"⚠️  TEST 4 경고: 종가 차이 {close_diff}원")

        else:
            logger.warning("⚠️  비교 데이터 부족")
            if not fdr_price:
                logger.warning("   - FDR 데이터 없음")
            if not kis_price:
                logger.warning("   - KIS 데이터 없음")

    except Exception as e:
        logger.error(f"❌ TEST 4 예외 발생: {e}", exc_info=True)

    finally:
        db.close()


async def main():
    """
    전체 테스트 실행
    """
    logger.info("\n" + "=" * 80)
    logger.info("🚀 KIS 일봉 수집기 테스트 시작")
    logger.info("=" * 80)

    try:
        # TEST 1: 단일 종목 수집
        await test_single_stock()

        # TEST 2: 배치 수집
        await test_batch_collection()

        # TEST 3: 데이터 검증
        await test_data_verification()

        # TEST 4: 데이터 비교
        await test_source_comparison()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테스트 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 예상치 못한 에러: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
