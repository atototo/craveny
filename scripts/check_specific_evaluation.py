"""
특정 종목의 평가 상세 내역 확인
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.stock import StockPrice
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_evaluation(stock_code: str, evaluation_date: datetime):
    """특정 종목의 평가 내역 확인"""
    db = SessionLocal()
    try:
        logger.info("=" * 80)
        logger.info(f"📊 {stock_code} 평가 내역 확인")
        logger.info("=" * 80)

        # 1. 평가 결과 조회
        start_of_day = evaluation_date.replace(hour=0, minute=0, second=0)
        end_of_day = evaluation_date.replace(hour=23, minute=59, second=59)

        evaluation = db.query(ModelEvaluation).filter(
            ModelEvaluation.stock_code == stock_code,
            ModelEvaluation.predicted_at >= start_of_day,
            ModelEvaluation.predicted_at <= end_of_day
        ).first()

        if not evaluation:
            logger.warning(f"⚠️  평가 데이터 없음: {stock_code} on {evaluation_date.date()}")
            return

        logger.info(f"\n📋 평가 결과:")
        logger.info(f"  예측 날짜: {evaluation.predicted_at}")
        logger.info(f"  기준가: {evaluation.predicted_base_price:,}원")
        logger.info(f"  목표가: {evaluation.predicted_target_price:,}원")
        logger.info(f"  손절가: {evaluation.predicted_support_price:,}원")
        logger.info(f"  목표가 달성: {'✅ 달성' if evaluation.target_achieved else '❌ 미달성'}")
        logger.info(f"  달성일: {evaluation.target_achieved_days}일")
        logger.info(f"  손절가 이탈: {'⚠️ 이탈' if evaluation.support_breached else '✅ 안전'}")
        logger.info(f"  최종 점수: {evaluation.final_score:.1f}점")

        # 2. 실제 주가 데이터 확인
        logger.info(f"\n📈 실제 주가 데이터:")
        for day in range(1, 6):
            target_date = evaluation.predicted_at + timedelta(days=day)

            # 주말 스킵
            if target_date.weekday() >= 5:
                continue

            stock_data = db.query(StockPrice).filter(
                StockPrice.stock_code == stock_code,
                StockPrice.date >= target_date.replace(hour=0, minute=0, second=0),
                StockPrice.date <= target_date.replace(hour=23, minute=59, second=59)
            ).first()

            if stock_data:
                logger.info(
                    f"  T+{day} ({stock_data.date.date()}): "
                    f"고가={stock_data.high:,}원, "
                    f"저가={stock_data.low:,}원, "
                    f"종가={stock_data.close:,}원"
                )

                # 목표가/손절가 달성 여부 표시
                target_hit = "✅ 목표가 달성" if stock_data.high >= evaluation.predicted_target_price else ""
                support_hit = "⚠️ 손절가 이탈" if stock_data.low <= evaluation.predicted_support_price else ""
                if target_hit or support_hit:
                    logger.info(f"       → {target_hit} {support_hit}")

        logger.info("\n" + "=" * 80)

    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    # 현대모비스 11/6 평가 확인
    check_evaluation("012330", datetime(2025, 11, 6, 16, 0, 0))
