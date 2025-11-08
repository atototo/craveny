"""
과거 날짜 Investment Report INSERT

stock_analysis_summaries 테이블에 과거 날짜 레코드를 직접 삽입하여
배치 평가 테스트용 데이터를 생성합니다.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.stock import Stock
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def copy_reports_to_past_date(source_date: datetime, target_date: datetime):
    """
    특정 날짜의 리포트를 복사하여 과거 날짜로 저장

    Args:
        source_date: 복사할 원본 리포트 날짜 (예: 11/7)
        target_date: 저장할 목표 날짜 (예: 11/1)
    """
    db = SessionLocal()
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"📅 {target_date.date()} Investment Report 생성")
        logger.info(f"   원본: {source_date.date()} 리포트 복사")
        logger.info(f"{'='*80}")

        # 원본 리포트 조회 (최신 리포트)
        source_start = source_date.replace(hour=0, minute=0, second=0)
        source_end = source_date.replace(hour=23, minute=59, second=59)

        source_reports = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.last_updated >= source_start,
            StockAnalysisSummary.last_updated <= source_end,
            StockAnalysisSummary.base_price.isnot(None),
            StockAnalysisSummary.short_term_target_price.isnot(None),
            StockAnalysisSummary.short_term_support_price.isnot(None)
        ).all()

        logger.info(f"📊 복사 대상: {len(source_reports)}개 리포트")

        if not source_reports:
            logger.warning("⚠️  복사할 리포트가 없습니다!")
            return 0

        # 목표 날짜에 이미 있는 리포트 확인
        target_start = target_date.replace(hour=0, minute=0, second=0)
        target_end = target_date.replace(hour=23, minute=59, second=59)

        existing_count = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.last_updated >= target_start,
            StockAnalysisSummary.last_updated <= target_end
        ).count()

        if existing_count > 0:
            logger.info(f"ℹ️  {target_date.date()}에 이미 {existing_count}개 리포트 존재")

        success_count = 0
        for report in source_reports:
            try:
                # 새 리포트 생성 (복사)
                new_report = StockAnalysisSummary(
                    stock_code=report.stock_code,
                    overall_summary=report.overall_summary,
                    short_term_scenario=report.short_term_scenario,
                    medium_term_scenario=report.medium_term_scenario,
                    long_term_scenario=report.long_term_scenario,
                    risk_factors=report.risk_factors,
                    opportunity_factors=report.opportunity_factors,
                    recommendation=report.recommendation,
                    total_predictions=report.total_predictions,
                    up_count=report.up_count,
                    down_count=report.down_count,
                    hold_count=report.hold_count,
                    avg_confidence=report.avg_confidence,
                    last_updated=target_date,  # 목표 날짜로 설정
                    based_on_prediction_count=report.based_on_prediction_count,
                    custom_data=report.custom_data,
                    short_term_target_price=report.short_term_target_price,
                    short_term_support_price=report.short_term_support_price,
                    medium_term_target_price=report.medium_term_target_price,
                    medium_term_support_price=report.medium_term_support_price,
                    long_term_target_price=report.long_term_target_price,
                    base_price=report.base_price
                )

                db.add(new_report)
                success_count += 1

                if success_count <= 3:  # 처음 3개만 로그
                    logger.info(
                        f"  ✅ {report.stock_code}: "
                        f"기준가 {report.base_price:,.0f}원, "
                        f"목표가 {report.short_term_target_price:,.0f}원"
                    )

            except Exception as e:
                logger.error(f"  ❌ {report.stock_code} 복사 실패: {e}")

        db.commit()

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 {target_date.date()} 리포트 생성 완료: {success_count}건")
        logger.info(f"{'='*80}")

        return success_count

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        db.rollback()
        return 0
    finally:
        db.close()


def main():
    """
    11월 1일, 4일, 5일, 6일 리포트 생성
    11월 7일 리포트를 복사하여 사용
    """
    logger.info("\n" + "="*80)
    logger.info("🚀 과거 Investment Report 생성 (복사 방식)")
    logger.info("="*80)

    # 원본: 11월 7일 리포트
    source_date = datetime(2025, 11, 7, 16, 0, 0)

    # 목표 날짜들
    target_dates = [
        datetime(2025, 11, 1, 16, 0, 0),   # 금요일 16:00
        datetime(2025, 11, 4, 16, 0, 0),   # 월요일 16:00
        datetime(2025, 11, 5, 16, 0, 0),   # 화요일 16:00
        datetime(2025, 11, 6, 16, 0, 0),   # 수요일 16:00
    ]

    total_count = 0
    for target_date in target_dates:
        count = copy_reports_to_past_date(source_date, target_date)
        total_count += count

    logger.info("\n" + "="*80)
    logger.info(f"✅ 모든 과거 리포트 생성 완료! (총 {total_count}건)")
    logger.info("="*80)


if __name__ == "__main__":
    main()
