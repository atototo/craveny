"""
11월 3-7일 StockAnalysisSummary (종합 투자 리포트) 재생성

새 프롬프트(KIS API 데이터 포함)로 모든 종목/모델의 종합 투자 리포트를 재생성합니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock
from backend.db.models.prediction import Prediction
from backend.services.stock_analysis_service import update_stock_analysis_summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def regenerate_reports_for_date(target_date: datetime):
    """
    특정 날짜의 종합 투자 리포트 재생성

    Args:
        target_date: 생성할 날짜
    """
    db = SessionLocal()
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"📅 {target_date.date()} 종합 투자 리포트 재생성 시작")
        logger.info(f"{'='*80}")

        # 해당 날짜에 Prediction이 있는 종목 조회
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        stock_codes = db.query(Prediction.stock_code).filter(
            Prediction.created_at >= start_of_day,
            Prediction.created_at <= end_of_day
        ).distinct().all()

        stock_codes = [code[0] for code in stock_codes]
        logger.info(f"📊 대상 종목: {len(stock_codes)}개")

        success_count = 0
        error_count = 0

        for stock_code in stock_codes:
            try:
                # 종목명 조회
                stock = db.query(Stock).filter(Stock.code == stock_code).first()
                stock_name = stock.name if stock else stock_code

                logger.info(f"\n🔄 {stock_name} ({stock_code}) 리포트 재생성 중...")

                # 종합 투자 리포트 생성 (모든 활성 모델에 대해)
                result = await update_stock_analysis_summary(
                    stock_code=stock_code,
                    db=db,
                    force_update=True
                )

                if result:
                    # 생성 시간을 target_date로 수정
                    result.last_updated = target_date
                    db.commit()

                    success_count += 1
                    logger.info(f"  ✅ 재생성 완료 (시간: {target_date})")

                    if result.base_price and result.short_term_target_price:
                        logger.info(
                            f"  💰 기준가: {result.base_price:,.0f}원, "
                            f"목표가: {result.short_term_target_price:,.0f}원, "
                            f"손절가: {result.short_term_support_price:,.0f}원"
                        )
                else:
                    error_count += 1
                    logger.warning(f"  ⚠️  재생성 실패: {stock_code}")

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 오류: {stock_code}, {e}")

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 {target_date.date()} 리포트 재생성 완료")
        logger.info(f"  성공: {success_count}개, 실패: {error_count}개")
        logger.info(f"{'='*80}\n")

        return success_count, error_count

    except Exception as e:
        logger.error(f"\n❌ 날짜 처리 실패: {target_date.date()}, {e}")
        import traceback
        traceback.print_exc()
        return 0, 0
    finally:
        db.close()


async def regenerate_all_reports():
    """11월 3-7일 모든 종합 투자 리포트 재생성"""
    logger.info("=" * 80)
    logger.info("🔄 11월 3-7일 종합 투자 리포트 재생성 시작")
    logger.info("=" * 80)

    # 11월 3-7일
    dates = [
        datetime(2025, 11, 3, 9, 0, 0),
        datetime(2025, 11, 4, 9, 0, 0),
        datetime(2025, 11, 5, 9, 0, 0),
        datetime(2025, 11, 6, 9, 0, 0),
        datetime(2025, 11, 7, 9, 0, 0),
    ]

    total_success = 0
    total_error = 0

    for target_date in dates:
        success, error = await regenerate_reports_for_date(target_date)
        total_success += success
        total_error += error

        # 다음 날짜 처리 전 잠시 대기 (rate limiting)
        await asyncio.sleep(2)

    logger.info("\n" + "=" * 80)
    logger.info("🎯 전체 재생성 완료 요약")
    logger.info("=" * 80)
    logger.info(f"  총 성공: {total_success}개")
    logger.info(f"  총 실패: {total_error}개")
    logger.info(f"  성공률: {total_success / (total_success + total_error) * 100:.1f}%")
    logger.info("=" * 80)
    logger.info("\n✅ 11월 3-7일 종합 투자 리포트 재생성 완료!")


if __name__ == "__main__":
    print("\n📢 11월 3-7일 모든 종합 투자 리포트를 새 프롬프트로 재생성합니다.")
    print("   (KIS API 데이터 포함)")
    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        asyncio.run(regenerate_all_reports())
    else:
        print("❌ 취소되었습니다.")
