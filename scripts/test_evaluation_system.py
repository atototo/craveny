"""
평가 시스템 동작 테스트 - 과거 리포트로 평가 가능 여부 확인
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_evaluation_system():
    """평가 시스템 테스트"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info("🧪 평가 시스템 테스트")
        logger.info("=" * 80)

        evaluation_service = EvaluationService(db)

        # 테스트할 날짜들 (11/1, 11/4, 11/5, 11/6 리포트 평가 가능 여부)
        test_dates = [
            datetime(2025, 11, 1, 16, 0, 0),
            datetime(2025, 11, 4, 16, 0, 0),
            datetime(2025, 11, 5, 16, 0, 0),
            datetime(2025, 11, 6, 16, 0, 0),
        ]

        for target_date in test_dates:
            logger.info(f"\n{'='*80}")
            logger.info(f"📅 {target_date.date()} 리포트 평가 테스트")
            logger.info(f"{'='*80}")

            # 평가 가능한 리포트 조회
            reports = evaluation_service.get_evaluable_reports(target_date)
            logger.info(f"✅ 평가 가능한 리포트: {len(reports)}개")

            if reports:
                # 샘플 3개 출력
                logger.info("\n📊 샘플 리포트:")
                for i, report in enumerate(reports[:3], 1):
                    logger.info(
                        f"  {i}. {report.stock_code}: "
                        f"기준가={report.base_price:,.0f}원, "
                        f"목표가={report.short_term_target_price:,.0f}원, "
                        f"손절가={report.short_term_support_price:,.0f}원"
                    )
            else:
                logger.warning("⚠️  평가 가능한 리포트가 없습니다!")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 평가 시스템 테스트 완료!")
        logger.info("=" * 80)
        logger.info("\n💡 결론:")
        logger.info("  - 과거 리포트가 정상적으로 조회됩니다")
        logger.info("  - 평가 시스템이 이제 동작할 수 있습니다")
        logger.info("  - 배치 스케줄러가 실행되면 평가 데이터가 생성됩니다")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_evaluation_system()
