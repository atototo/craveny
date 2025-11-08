"""
11월 1-10일 주가 데이터 수집 스크립트
평가 시스템을 위한 과거 주가 데이터 백필
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from backend.db.session import SessionLocal
from backend.crawlers.stock_crawler import StockCrawler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("\n" + "="*80)
    logger.info("📈 11월 1-10일 주가 데이터 수집")
    logger.info("="*80)

    # 크롤러 초기화
    crawler = StockCrawler(use_db=True)
    stock_codes = crawler.get_stock_codes()

    logger.info(f"📊 수집 대상: {len(stock_codes)}개 종목")

    # 11월 1일부터 수집
    start_date = datetime(2025, 11, 1)

    db = SessionLocal()
    try:
        total_saved = 0
        success_count = 0

        for stock_code in stock_codes:
            logger.info(f"\n🔄 {stock_code} 수집 중...")

            # 데이터 수집
            df = crawler.fetch_stock_data(stock_code, start_date=start_date)

            if df is not None and not df.empty:
                # 저장
                saved = crawler.save_stock_data(stock_code, df, db)
                total_saved += saved

                if saved > 0:
                    success_count += 1
                    logger.info(f"✅ {stock_code}: {saved}건 저장")
                else:
                    logger.warning(f"⚠️  {stock_code}: 저장 실패")
            else:
                logger.warning(f"⚠️  {stock_code}: 데이터 없음")

        logger.info("\n" + "="*80)
        logger.info("🎉 주가 데이터 수집 완료")
        logger.info(f"  - 성공: {success_count}/{len(stock_codes)}개 종목")
        logger.info(f"  - 총 저장: {total_saved}건")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
