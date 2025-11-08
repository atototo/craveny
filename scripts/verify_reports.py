"""
생성된 과거 Investment Reports 검증
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, func
from backend.db.session import SessionLocal
from backend.db.models.stock_analysis import StockAnalysisSummary
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def verify_reports():
    """생성된 리포트 검증"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info("📊 Investment Report 데이터 검증")
        logger.info("=" * 80)

        # 전체 레코드 수 확인
        total_count = db.query(StockAnalysisSummary).count()
        logger.info(f"\n📈 총 레코드 수: {total_count}개")

        # 날짜별 레코드 수 확인
        logger.info("\n📅 날짜별 리포트 수:")
        date_counts = db.query(
            func.date(StockAnalysisSummary.last_updated).label('date'),
            func.count(StockAnalysisSummary.id).label('count')
        ).group_by(
            func.date(StockAnalysisSummary.last_updated)
        ).order_by('date').all()

        for date, count in date_counts:
            logger.info(f"  {date}: {count}개")

        # 각 날짜별 상세 확인 (처음 3개만)
        target_dates = [
            datetime(2025, 11, 1),
            datetime(2025, 11, 4),
            datetime(2025, 11, 5),
            datetime(2025, 11, 6),
            datetime(2025, 11, 7),
        ]

        logger.info("\n" + "=" * 80)
        logger.info("📋 날짜별 상세 리포트 (샘플 3개)")
        logger.info("=" * 80)

        for target_date in target_dates:
            start_of_day = target_date.replace(hour=0, minute=0, second=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59)

            reports = db.query(StockAnalysisSummary).filter(
                StockAnalysisSummary.last_updated >= start_of_day,
                StockAnalysisSummary.last_updated <= end_of_day
            ).limit(3).all()

            logger.info(f"\n📅 {target_date.date()}:")
            for report in reports:
                logger.info(
                    f"  {report.stock_code}: "
                    f"기준가={report.base_price:,.0f}원, "
                    f"목표가={report.short_term_target_price:,.0f}원, "
                    f"손절가={report.short_term_support_price:,.0f}원"
                )

        # 종목별 중복 확인 (stock_code + date 조합)
        logger.info("\n" + "=" * 80)
        logger.info("🔍 종목별 날짜 분포 확인 (샘플 5개)")
        logger.info("=" * 80)

        stock_codes = ['005930', '034020', '009150', '000660', '035420']
        for stock_code in stock_codes:
            count = db.query(StockAnalysisSummary).filter(
                StockAnalysisSummary.stock_code == stock_code
            ).count()

            reports = db.query(
                func.date(StockAnalysisSummary.last_updated).label('date')
            ).filter(
                StockAnalysisSummary.stock_code == stock_code
            ).order_by('date').all()

            dates = [r.date for r in reports]
            logger.info(f"\n  {stock_code}: {count}개 리포트")
            logger.info(f"    날짜: {', '.join(map(str, dates))}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 검증 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 검증 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    verify_reports()
