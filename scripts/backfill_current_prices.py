"""
최근 prediction들에 current_price를 채워주는 스크립트.

Usage:
    python scripts/backfill_current_prices.py
"""
import logging
from datetime import datetime, timedelta
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.stock import StockPrice


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def backfill_current_prices(days_ago: int = 7):
    """최근 N일간의 prediction들에 current_price 채우기."""
    db = SessionLocal()

    try:
        # 최근 N일간의 prediction 조회 (current_price가 없는 것만)
        start_date = datetime.now() - timedelta(days=days_ago)

        predictions = db.query(Prediction).filter(
            Prediction.created_at >= start_date,
            Prediction.current_price.is_(None)
        ).all()

        logger.info(f"📊 업데이트 대상 prediction: {len(predictions)}건")

        updated_count = 0
        failed_count = 0

        for pred in predictions:
            try:
                # 예측 생성 시점의 주가 데이터 조회
                pred_date = pred.created_at.replace(hour=0, minute=0, second=0, microsecond=0)

                # 예측 생성일 또는 그 전 영업일의 종가 조회
                stock_price = None
                for day_offset in range(0, 5):  # 최대 5일 전까지 검색
                    check_date = pred_date - timedelta(days=day_offset)

                    stock_price = db.query(StockPrice).filter(
                        StockPrice.stock_code == pred.stock_code,
                        StockPrice.date >= check_date,
                        StockPrice.date < check_date + timedelta(days=1)
                    ).first()

                    if stock_price:
                        break

                if stock_price:
                    pred.current_price = stock_price.close
                    updated_count += 1

                    if updated_count % 100 == 0:
                        logger.info(f"  진행 중... {updated_count}건 업데이트")
                else:
                    logger.warning(f"  주가 데이터 없음: {pred.stock_code} at {pred_date.date()}")
                    failed_count += 1

            except Exception as e:
                logger.error(f"  오류: prediction {pred.id} - {e}")
                failed_count += 1
                continue

        # 커밋
        db.commit()

        logger.info(f"✅ 완료: {updated_count}건 업데이트, {failed_count}건 실패")

    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("📊 Prediction Current Price Backfill")
    print("=" * 80)

    backfill_current_prices(days_ago=30)  # 최근 30일
