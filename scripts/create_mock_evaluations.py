"""
Mock evaluation 데이터 생성 스크립트 (데모용).

Usage:
    python scripts/create_mock_evaluations.py
"""
import logging
import random
from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.model_evaluation import ModelEvaluation


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def create_mock_evaluations(limit: int = 100):
    """Mock evaluation 데이터 생성 (데모용)."""
    db = SessionLocal()

    try:
        # current_price가 있는 최근 prediction들 조회
        predictions = db.query(Prediction).filter(
            Prediction.current_price.isnot(None)
        ).order_by(Prediction.created_at.desc()).limit(limit).all()

        logger.info(f"📊 Mock 평가 생성 대상: {len(predictions)}건")

        created_count = 0

        for pred in predictions:
            try:
                # 이미 평가가 있는지 확인
                existing = db.query(ModelEvaluation).filter(
                    ModelEvaluation.prediction_id == pred.id
                ).first()

                if existing:
                    continue

                # Mock 데이터 생성
                base_price = pred.current_price
                target_price = base_price * random.uniform(1.05, 1.15)  # +5~15%
                support_price = base_price * random.uniform(0.9, 0.95)  # -5~10%

                # 가상의 실제 가격 (목표가 달성 여부를 랜덤하게)
                target_achieved = random.random() > 0.4  # 60% 확률로 달성

                if target_achieved:
                    actual_high_1d = base_price * random.uniform(1.05, target_price / base_price)
                    actual_close_1d = base_price * random.uniform(1.02, actual_high_1d / base_price)
                else:
                    actual_high_1d = base_price * random.uniform(1.0, 1.04)
                    actual_close_1d = base_price * random.uniform(0.98, actual_high_1d / base_price)

                actual_low_1d = base_price * random.uniform(0.97, 1.0)

                # 5일차 데이터
                if target_achieved:
                    actual_high_5d = actual_high_1d * random.uniform(1.0, 1.05)
                    actual_close_5d = actual_close_1d * random.uniform(1.0, 1.03)
                else:
                    actual_high_5d = actual_high_1d * random.uniform(0.95, 1.02)
                    actual_close_5d = actual_close_1d * random.uniform(0.95, 1.02)

                actual_low_5d = min(actual_low_1d, actual_close_5d * random.uniform(0.95, 0.98))

                # 손절가 이탈 여부
                support_breached = actual_low_5d < support_price

                # 점수 계산
                if target_achieved:
                    target_accuracy_score = 100.0
                    timing_score = random.uniform(60.0, 100.0)
                else:
                    # 미달성 시 도달 비율
                    if actual_high_5d > base_price and target_price > base_price:
                        ratio = (actual_high_5d - base_price) / (target_price - base_price)
                        target_accuracy_score = min(100.0, max(0.0, ratio * 100))
                    else:
                        target_accuracy_score = 0.0
                    timing_score = 0.0

                risk_management_score = 0.0 if support_breached else 100.0

                # 최종 점수 (40:30:30)
                final_score = (
                    target_accuracy_score * 0.4 +
                    timing_score * 0.3 +
                    risk_management_score * 0.3
                )

                # ModelEvaluation 생성
                evaluation = ModelEvaluation(
                    prediction_id=pred.id,
                    model_id=pred.model_id or random.choice([1, 2, 3, 4, 5]),
                    stock_code=pred.stock_code,

                    # 예측 정보
                    predicted_at=pred.created_at,
                    prediction_period="1일~5일",
                    predicted_target_price=target_price,
                    predicted_support_price=support_price,
                    predicted_base_price=base_price,
                    predicted_confidence=pred.confidence,

                    # 실제 결과 (mock)
                    actual_high_1d=actual_high_1d,
                    actual_low_1d=actual_low_1d,
                    actual_close_1d=actual_close_1d,
                    actual_high_5d=actual_high_5d,
                    actual_low_5d=actual_low_5d,
                    actual_close_5d=actual_close_5d,

                    target_achieved=target_achieved,
                    target_achieved_days=random.randint(1, 5) if target_achieved else None,
                    support_breached=support_breached,

                    # 자동 점수
                    target_accuracy_score=target_accuracy_score,
                    timing_score=timing_score,
                    risk_management_score=risk_management_score,
                    final_score=final_score,

                    evaluated_at=datetime.now()
                )

                db.add(evaluation)
                created_count += 1

                if created_count % 10 == 0:
                    db.commit()
                    logger.info(f"  진행 중... {created_count}건 생성")

            except Exception as e:
                logger.error(f"  오류: prediction {pred.id} - {e}")
                continue

        # 최종 커밋
        db.commit()

        logger.info(f"✅ 완료: {created_count}건의 Mock 평가 데이터 생성")

    except Exception as e:
        logger.error(f"❌ 오류: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("📊 Mock Evaluation Data Generator (Demo Only)")
    print("=" * 80)

    create_mock_evaluations(limit=200)  # 최근 200개 prediction에 대해 생성
