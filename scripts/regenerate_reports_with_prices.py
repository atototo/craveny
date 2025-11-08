"""
기존 Investment Report를 구조화된 가격 정보와 함께 재생성

현재 StockAnalysisSummary 테이블에 있는 리포트들을 재생성하여
새로 추가된 target_price/support_price 필드를 채움
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.services.stock_analysis_service import update_stock_analysis_summary
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("\n" + "="*80)
    logger.info("🔄 Investment Report 재생성 (구조화된 가격 포함)")
    logger.info("="*80)

    db = SessionLocal()
    try:
        # 기존 리포트 조회
        reports = db.query(StockAnalysisSummary).all()

        logger.info(f"📊 총 {len(reports)}개 리포트 재생성 시작")

        success_count = 0
        error_count = 0

        for report in reports:
            try:
                logger.info(f"\n🔄 {report.stock_code} 재생성 중...")

                # force_update=True로 강제 업데이트
                result = await update_stock_analysis_summary(
                    stock_code=report.stock_code,
                    db=db,
                    force_update=True
                )

                if result:
                    success_count += 1
                    logger.info(f"  ✅ 재생성 완료: {report.stock_code}")

                    # 구조화된 가격 정보 확인
                    if result.base_price and result.short_term_target_price:
                        logger.info(
                            f"  💰 기준가: {result.base_price:,.0f}원, "
                            f"목표가: {result.short_term_target_price:,.0f}원, "
                            f"손절가: {result.short_term_support_price:,.0f}원"
                        )
                    else:
                        logger.warning(f"  ⚠️  구조화된 가격 정보 없음")
                else:
                    error_count += 1
                    logger.warning(f"  ⚠️  재생성 실패: {report.stock_code}")

            except Exception as e:
                error_count += 1
                logger.error(f"  ❌ 오류: {report.stock_code}, {e}")

        logger.info("\n" + "="*80)
        logger.info("🎉 Investment Report 재생성 완료")
        logger.info(f"  - 성공: {success_count}/{len(reports)}개")
        logger.info(f"  - 실패: {error_count}개")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
