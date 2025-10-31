"""
주가 수집기 테스트 스크립트

주가 데이터를 수집하고 DB에 저장하는지 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime

from backend.crawlers.stock_crawler import get_stock_crawler
from backend.db.session import SessionLocal
from backend.db.models.stock import StockPrice
from backend.utils.market_time import is_market_open, get_market_status

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_market_time():
    """장 시간 체크 테스트"""
    logger.info("=" * 60)
    logger.info("📊 장 시간 체크 테스트")
    logger.info("=" * 60)

    now = datetime.now()
    is_open = is_market_open()
    status = get_market_status()

    logger.info(f"현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"장 개장 여부: {is_open}")
    logger.info(f"시장 상태: {status}")
    logger.info("")


def test_single_stock_collection():
    """단일 종목 주가 수집 테스트"""
    logger.info("=" * 60)
    logger.info("📈 단일 종목 주가 수집 테스트")
    logger.info("=" * 60)

    # 삼성전자 테스트
    stock_code = "005930"
    stock_name = "삼성전자"

    logger.info(f"테스트 종목: {stock_name} ({stock_code})")

    # 크롤러 생성
    crawler = get_stock_crawler()

    # 주가 데이터 수집
    df = crawler.fetch_stock_data(stock_code)

    if df is None:
        logger.error(f"❌ {stock_name} 주가 데이터 수집 실패")
        return

    logger.info(f"✅ {stock_name} 주가 데이터 수집 성공: {len(df)}건")
    logger.info(f"   날짜 범위: {df.index[0]} ~ {df.index[-1]}")
    logger.info(f"   컬럼: {list(df.columns)}")

    # 최근 5건 출력
    logger.info("   최근 5건 데이터:")
    for idx, row in df.tail(5).iterrows():
        logger.info(
            f"      {idx.strftime('%Y-%m-%d')}: "
            f"시가 {row['Open']:,.0f}, "
            f"고가 {row['High']:,.0f}, "
            f"저가 {row['Low']:,.0f}, "
            f"종가 {row['Close']:,.0f}, "
            f"거래량 {row['Volume']:,.0f}"
        )

    # DB 저장 테스트
    db = SessionLocal()
    try:
        saved_count = crawler.save_stock_data(stock_code, df, db)
        logger.info(f"✅ DB 저장 완료: {saved_count}건")

        # 저장된 데이터 확인
        saved_records = (
            db.query(StockPrice)
            .filter(StockPrice.stock_code == stock_code)
            .order_by(StockPrice.date.desc())
            .limit(5)
            .all()
        )

        logger.info(f"   DB에서 확인된 최근 5건:")
        for record in saved_records:
            logger.info(
                f"      {record.date.strftime('%Y-%m-%d')}: "
                f"종가 {record.close:,.0f}, "
                f"거래량 {record.volume:,.0f}"
            )

    finally:
        db.close()

    logger.info("")


def test_priority_stock_collection():
    """우선순위 종목 일괄 수집 테스트"""
    logger.info("=" * 60)
    logger.info("📊 Priority 1 종목 일괄 수집 테스트")
    logger.info("=" * 60)

    # 크롤러 생성
    crawler = get_stock_crawler()

    # Priority 1 종목 코드 확인
    priority1_codes = crawler.get_stock_codes(priority=1)
    logger.info(f"Priority 1 종목 수: {len(priority1_codes)}개")
    logger.info(f"종목 코드: {', '.join(priority1_codes)}")

    # 일괄 수집
    logger.info("주가 데이터 수집 중...")
    results = crawler.collect_all_stocks(priority=1)

    # 결과 출력
    logger.info("=" * 60)
    logger.info("수집 결과:")
    logger.info("=" * 60)

    total_saved = 0
    success_count = 0

    for stock_code, saved_count in results.items():
        status = "✅" if saved_count > 0 else "❌"
        logger.info(f"{status} {stock_code}: {saved_count}건 저장")

        total_saved += saved_count
        if saved_count > 0:
            success_count += 1

    logger.info("=" * 60)
    logger.info(f"✅ 일괄 수집 완료:")
    logger.info(f"   성공: {success_count}/{len(results)}개 종목")
    logger.info(f"   총 저장: {total_saved}건")
    logger.info("=" * 60)


def main():
    """메인 실행 함수"""
    try:
        # 1. 장 시간 체크
        test_market_time()

        # 2. 단일 종목 테스트
        test_single_stock_collection()

        # 3. 일괄 수집 테스트 (Priority 1만)
        test_priority_stock_collection()

        logger.info("✅ 모든 테스트 완료")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
