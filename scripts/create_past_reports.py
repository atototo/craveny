"""
과거 날짜 Investment Report 생성

11월 1일, 4일, 5일, 6일 Investment Report를 생성하여
배치 평가 테스트를 위한 데이터를 준비합니다.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime, timedelta
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock
from backend.services.stock_analysis_service import update_stock_analysis_summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_reports_for_date(target_date: datetime):
    """
    특정 날짜의 Investment Report 생성

    Args:
        target_date: 생성할 날짜
    """
    db = SessionLocal()
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"📅 {target_date.date()} Investment Report 생성 시작")
        logger.info(f"{'='*80}")

        # Priority 1-2 종목 조회 (중요 종목만)
        stocks = db.query(Stock).filter(
            Stock.is_active == True,
            Stock.priority <= 2
        ).all()

        logger.info(f"📊 대상 종목: {len(stocks)}개")

        success_count = 0
        error_count = 0

        for stock in stocks:
            try:
                logger.info(f"\n🔄 {stock.name} ({stock.code}) 리포트 생성 중...")

                # Investment Report 생성
                result = await update_stock_analysis_summary(
                    stock_code=stock.code,
                    db=db,
                    force_update=True
                )

                if result:
                    # 생성 시간을 target_date로 수정
                    result.last_updated = target_date
                    db.commit()

                    success_count += 1
                    logger.info(f"  ✅ 생성 완료 (시간: {target_date})")

                    if result.base_price and result.short_term_target_price:
                        logger.info(
                            f"  💰 기준가: {result.base_price:,.0f}원, "
                            f"목표가: {result.short_term_target_price:,.0f}원, "
                            f"손절가: {result.short_term_support_price:,.0f}원"
                        )
                else:
                    error_count += 1
                    logger.warning(f"  ⚠️  생성 실패: {stock.code}")

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 오류: {stock.code}, {e}")

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 {target_date.date()} 리포트 생성 완료")
        logger.info(f"  - 성공: {success_count}/{len(stocks)}개")
        logger.info(f"  - 실패: {error_count}개")
        logger.info(f"{'='*80}")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
    finally:
        db.close()


async def main():
    """
    11월 1일, 4일, 5일, 6일 Investment Report 생성
    """
    logger.info("\n" + "="*80)
    logger.info("🚀 과거 Investment Report 생성 시작")
    logger.info("="*80)

    # 생성할 날짜 리스트 (영업일)
    target_dates = [
        datetime(2025, 11, 1, 16, 0, 0),   # 금요일 16:00
        datetime(2025, 11, 4, 16, 0, 0),   # 월요일 16:00
        datetime(2025, 11, 5, 16, 0, 0),   # 화요일 16:00
        datetime(2025, 11, 6, 16, 0, 0),   # 수요일 16:00
    ]

    for target_date in target_dates:
        await create_reports_for_date(target_date)
        await asyncio.sleep(1)  # 서버 부하 방지

    logger.info("\n" + "="*80)
    logger.info("✅ 모든 과거 리포트 생성 완료!")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
