"""
FDR + KIS Dual-run 모드 테스트

Usage:
    uv run python scripts/test_dual_run.py
"""
import asyncio
import logging
from datetime import datetime, timedelta

from backend.crawlers.stock_crawler import get_stock_crawler
from backend.crawlers.kis_daily_crawler import get_kis_daily_crawler
from backend.utils.data_source_selector import get_data_source_selector
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_dual_collection():
    """
    TEST 1: FDR + KIS 동시 수집 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: FDR + KIS 동시 수집")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # Priority 1 종목 3개만 테스트
        stocks = db.query(Stock).filter(
            Stock.is_active == True,
            Stock.priority == 1
        ).limit(3).all()

        stock_codes = [stock.code for stock in stocks]

        logger.info(f"테스트 종목: {[f'{s.name}({s.code})' for s in stocks]}")

        # 1. FDR 수집
        logger.info("\n📰 FDR 데이터 수집...")
        fdr_crawler = get_stock_crawler()
        fdr_results = {}

        for stock_code in stock_codes:
            start_date = datetime.now() - timedelta(days=7)
            df = fdr_crawler.fetch_stock_data(stock_code, start_date)

            if df is not None and not df.empty:
                saved = fdr_crawler.save_stock_data(stock_code, df, db)
                fdr_results[stock_code] = saved
                logger.info(f"  ✅ {stock_code}: {saved}건 저장 (FDR)")
            else:
                fdr_results[stock_code] = 0
                logger.warning(f"  ⚠️  {stock_code}: 데이터 없음 (FDR)")

        # 2. KIS 수집
        logger.info("\n📈 KIS 데이터 수집...")
        kis_crawler = get_kis_daily_crawler()
        kis_results = []

        for stock_code in stock_codes:
            result = await kis_crawler.collect_stock(
                stock_code=stock_code,
                days=7,
                db=db
            )
            kis_results.append(result)

            if result["status"] == "success":
                logger.info(f"  ✅ {stock_code}: {result['count']}건 저장 (KIS)")
            else:
                logger.warning(f"  ⚠️  {stock_code}: 수집 실패 (KIS)")

        # 결과 요약
        fdr_success = sum(1 for c in fdr_results.values() if c > 0)
        kis_success = sum(1 for r in kis_results if r["status"] == "success")

        logger.info("\n📊 수집 결과:")
        logger.info(f"  FDR: {fdr_success}/{len(stock_codes)}개 성공")
        logger.info(f"  KIS: {kis_success}/{len(stock_codes)}개 성공")

        if fdr_success == len(stock_codes) and kis_success == len(stock_codes):
            logger.info("✅ TEST 1 성공!")
        else:
            logger.warning("⚠️  TEST 1 부분 성공")

    finally:
        db.close()


def test_data_source_selector():
    """
    TEST 2: 데이터 소스 선택기 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: 데이터 소스 선택기")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        selector = get_data_source_selector(db)

        # 삼성전자 품질 점수 확인
        stock_code = "005930"

        fdr_score = selector.get_data_quality_score("fdr", stock_code, days=7)
        kis_score = selector.get_data_quality_score("kis", stock_code, days=7)

        logger.info(f"\n{stock_code} 데이터 품질 점수:")
        logger.info(f"  FDR: {fdr_score:.2f}")
        logger.info(f"  KIS: {kis_score:.2f}")

        # 최적 소스 선택
        best_source = selector.select_best_source(stock_code, prefer_kis=True)
        logger.info(f"  선택된 소스: {best_source.upper()}")

        # 데이터 조회 (auto 모드)
        today = datetime.now()
        price = selector.get_stock_price(stock_code, today, source="auto")

        if price:
            logger.info(f"\n최신 가격 조회 성공:")
            logger.info(f"  날짜: {price.date.date()}")
            logger.info(f"  종가: {price.close:,}원")
            logger.info(f"  소스: {price.source.upper()}")
            logger.info("✅ TEST 2 성공!")
        else:
            logger.warning("⚠️  최신 가격 조회 실패")

    finally:
        db.close()


def test_dual_run_comparison():
    """
    TEST 3: FDR vs KIS 데이터 비교
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: FDR vs KIS 데이터 비교")
    logger.info("=" * 80)

    # 인라인 구현 (import 에러 회피)
    from sqlalchemy import and_

    def compare_stock_prices(stock_code: str, date: datetime, db):
        from backend.db.models.stock import StockPrice

        fdr_price = db.query(StockPrice).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == "fdr",
                StockPrice.date >= date.replace(hour=0, minute=0, second=0),
                StockPrice.date < date.replace(hour=23, minute=59, second=59)
            )
        ).first()

        kis_price = db.query(StockPrice).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == "kis",
                StockPrice.date >= date.replace(hour=0, minute=0, second=0),
                StockPrice.date < date.replace(hour=23, minute=59, second=59)
            )
        ).first()

        if not fdr_price or not kis_price:
            return {"stock_code": stock_code, "date": date.date(), "status": "missing_data"}

        close_diff = abs(fdr_price.close - kis_price.close)
        close_diff_pct = (close_diff / fdr_price.close) * 100 if fdr_price.close > 0 else 0

        volume_diff = abs(fdr_price.volume - kis_price.volume) if fdr_price.volume and kis_price.volume else 0
        volume_diff_pct = (volume_diff / fdr_price.volume) * 100 if fdr_price.volume and fdr_price.volume > 0 else 0

        is_close_match = close_diff_pct <= 0.1
        is_volume_match = volume_diff_pct <= 1.0
        is_perfect_match = is_close_match and is_volume_match

        return {
            "stock_code": stock_code,
            "date": date.date(),
            "status": "compared",
            "fdr_close": fdr_price.close,
            "kis_close": kis_price.close,
            "close_diff_pct": close_diff_pct,
            "volume_diff_pct": volume_diff_pct,
            "is_perfect_match": is_perfect_match,
            "is_close_match": is_close_match
        }

    db = SessionLocal()

    try:
        stock_code = "005930"
        date = datetime.now() - timedelta(days=1)

        result = compare_stock_prices(stock_code, date, db)

        if result["status"] == "compared":
            logger.info(f"\n{stock_code} 비교 결과 ({result['date']}):")
            logger.info(f"  FDR 종가: {result['fdr_close']:,}원")
            logger.info(f"  KIS 종가: {result['kis_close']:,}원")
            logger.info(f"  종가 차이: {result['close_diff_pct']:.2f}%")
            logger.info(f"  거래량 차이: {result['volume_diff_pct']:.2f}%")

            if result["is_perfect_match"]:
                logger.info("✅ TEST 3 성공! (완벽 일치)")
            elif result["is_close_match"]:
                logger.info("✅ TEST 3 성공! (근사 일치)")
            else:
                logger.warning(f"⚠️  TEST 3 경고: 차이가 큼 ({result['close_diff_pct']:.2f}%)")
        else:
            logger.warning(f"⚠️  비교 데이터 부족: {result['status']}")

    finally:
        db.close()


async def main():
    """전체 테스트 실행"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 FDR + KIS Dual-run 모드 테스트 시작")
    logger.info("=" * 80)

    try:
        # TEST 1: 동시 수집
        await test_dual_collection()

        # TEST 2: 소스 선택기
        test_data_source_selector()

        # TEST 3: 데이터 비교
        test_dual_run_comparison()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테스트 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
