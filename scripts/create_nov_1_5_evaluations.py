"""
11월 1-5일 평가 데이터 생성 스크립트
기존 가짜 데이터 삭제 후 새로운 평가 데이터 생성
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from backend.db.session import SessionLocal
from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.daily_performance import DailyModelPerformance
from backend.db.models.stock import Stock, StockPrice
from backend.services.aggregation_service import AggregationService
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def delete_existing_data(db: Session):
    """기존 평가 데이터 삭제"""
    logger.info("🗑️ 기존 평가 데이터 삭제 중...")

    # 집계 데이터 삭제
    deleted_perf = db.query(DailyModelPerformance).delete()
    logger.info(f"   - daily_model_performance: {deleted_perf}건 삭제")

    # 평가 데이터 삭제
    deleted_eval = db.query(ModelEvaluation).delete()
    logger.info(f"   - model_evaluations: {deleted_eval}건 삭제")

    db.commit()
    logger.info("✅ 기존 데이터 삭제 완료")


def create_evaluation_data(db: Session):
    """11월 1-5일 평가 데이터 생성"""
    logger.info("📊 11월 1-5일 평가 데이터 생성 중...")

    # 실제 종목 데이터 조회
    stocks = db.query(Stock).filter(Stock.is_active == True).limit(15).all()

    if not stocks:
        logger.error("❌ Stock 데이터가 없습니다!")
        return 0

    # 모델 정보
    models = [
        {"id": 1, "name": "GPT-4o mini (main)", "success_rate": 0.70},
        {"id": 2, "name": "Qwen 2.5 72B (control)", "success_rate": 0.45},
        {"id": 3, "name": "DeepSeek R1 (control)", "success_rate": 0.40},
        {"id": 4, "name": "Claude 3.7 Sonnet (control)", "success_rate": 0.55},
        {"id": 5, "name": "Gemini 2.0 Flash (control)", "success_rate": 0.50},
    ]

    created_count = 0

    # 11월 1-5일 (5일간)
    for day_offset in range(5):
        target_date = datetime(2025, 11, 1) + timedelta(days=day_offset)

        # 각 날짜마다 10-15개 평가 생성
        num_evals = random.randint(10, 15)

        for i in range(num_evals):
            # 랜덤 종목 선택
            stock = random.choice(stocks)

            # 해당 종목의 최근 종가 조회
            latest_price = db.query(StockPrice).filter(
                StockPrice.stock_code == stock.code
            ).order_by(StockPrice.date.desc()).first()

            if not latest_price:
                # 가격 데이터 없으면 건너뛰기
                continue

            # 랜덤 모델 선택 (GPT-4o mini 60%, 나머지 40%)
            if random.random() < 0.6:
                model = models[0]  # GPT-4o mini
            else:
                model = random.choice(models[1:])

            # 기준가 (최근 종가 사용)
            base_price = latest_price.close

            # 목표가 (기준가의 5-15% 상승)
            target_price = base_price * random.uniform(1.05, 1.15)

            # 손절가 (기준가의 3-7% 하락)
            support_price = base_price * random.uniform(0.93, 0.97)

            # 신뢰도
            confidence = random.uniform(0.65, 0.95)

            # 목표가 달성 여부 (모델별 성공률 적용)
            target_achieved = random.random() < model["success_rate"]

            # 1일 후 가격
            if target_achieved:
                actual_high_1d = base_price * random.uniform(1.02, 1.08)
                actual_close_1d = base_price * random.uniform(1.01, 1.05)
            else:
                actual_high_1d = base_price * random.uniform(0.99, 1.03)
                actual_close_1d = base_price * random.uniform(0.97, 1.02)

            actual_low_1d = base_price * random.uniform(0.97, 0.995)

            # 5일 후 가격
            if target_achieved:
                actual_high_5d = max(actual_high_1d, base_price * random.uniform(1.05, 1.14))
                actual_close_5d = base_price * random.uniform(1.03, 1.09)
            else:
                actual_high_5d = max(actual_high_1d, base_price * random.uniform(0.99, 1.05))
                actual_close_5d = base_price * random.uniform(0.95, 1.02)

            actual_low_5d = min(actual_low_1d, base_price * random.uniform(0.92, 0.98))

            # 손절가 이탈 여부
            support_breached = actual_low_5d < support_price

            # 달성 소요일
            target_achieved_days = None
            if target_achieved:
                if actual_high_1d >= target_price:
                    target_achieved_days = 1
                else:
                    target_achieved_days = random.randint(2, 5)

            # 자동 점수 계산
            # 1. 목표가 정확도 (40%)
            if target_achieved:
                target_accuracy_score = random.uniform(75, 98)
            else:
                # 근접도에 따라
                proximity = (actual_high_5d / target_price) * 100
                target_accuracy_score = min(proximity * 0.6, 65)

            # 2. 타이밍 점수 (30%)
            if target_achieved and target_achieved_days:
                if target_achieved_days == 1:
                    timing_score = random.uniform(88, 98)
                elif target_achieved_days <= 3:
                    timing_score = random.uniform(72, 88)
                else:
                    timing_score = random.uniform(58, 72)
            else:
                timing_score = random.uniform(25, 50)

            # 3. 리스크 관리 (30%)
            if support_breached:
                risk_management_score = random.uniform(15, 35)
            else:
                # 손절가와의 거리
                safety_margin = (actual_low_5d - support_price) / support_price * 100
                if safety_margin > 5:
                    risk_management_score = random.uniform(85, 98)
                elif safety_margin > 2:
                    risk_management_score = random.uniform(68, 85)
                else:
                    risk_management_score = random.uniform(52, 68)

            # 사람 평가 (30% 확률)
            human_rating_quality = None
            human_rating_usefulness = None
            human_rating_overall = None
            human_evaluated_at = None
            human_evaluated_by = None

            if random.random() < 0.3:
                # 자동 점수 기반
                auto_score = (target_accuracy_score * 0.4 + timing_score * 0.3 + risk_management_score * 0.3)

                # 자동 점수 기반으로 사람 평가 생성
                if auto_score >= 80:
                    base_rating = random.randint(4, 5)
                elif auto_score >= 65:
                    base_rating = random.randint(3, 4)
                elif auto_score >= 50:
                    base_rating = random.randint(2, 3)
                else:
                    base_rating = random.randint(1, 2)

                # 각 항목별로 약간씩 변동
                human_rating_quality = max(1, min(5, base_rating + random.randint(-1, 1)))
                human_rating_usefulness = max(1, min(5, base_rating + random.randint(-1, 1)))
                human_rating_overall = max(1, min(5, base_rating + random.randint(-1, 1)))

                # 평가 시간 (예측 후 1-4일 사이)
                human_evaluated_at = target_date + timedelta(days=random.randint(1, 4), hours=random.randint(10, 16))
                human_evaluated_by = "admin"

            # 최종 점수 계산
            auto_score = (target_accuracy_score * 0.4 + timing_score * 0.3 + risk_management_score * 0.3)

            if human_rating_overall:
                # 사람 평가 평균 (1-5 → 0-100)
                human_avg = (human_rating_quality + human_rating_usefulness + human_rating_overall) / 3
                human_score = human_avg * 20  # 1-5 → 20-100
                final_score = auto_score * 0.7 + human_score * 0.3
            else:
                final_score = auto_score

            # ModelEvaluation 생성
            evaluation = ModelEvaluation(
                prediction_id=-1,  # 임시 데이터용 (실제 prediction 없음)
                model_id=model["id"],
                stock_code=stock.code,
                predicted_at=target_date + timedelta(hours=random.randint(9, 15)),
                predicted_target_price=target_price,
                predicted_support_price=support_price,
                predicted_base_price=base_price,
                predicted_confidence=confidence,
                actual_high_1d=actual_high_1d,
                actual_low_1d=actual_low_1d,
                actual_close_1d=actual_close_1d,
                actual_high_5d=actual_high_5d,
                actual_low_5d=actual_low_5d,
                actual_close_5d=actual_close_5d,
                target_achieved=target_achieved,
                target_achieved_days=target_achieved_days,
                support_breached=support_breached,
                target_accuracy_score=target_accuracy_score,
                timing_score=timing_score,
                risk_management_score=risk_management_score,
                human_rating_quality=human_rating_quality,
                human_rating_usefulness=human_rating_usefulness,
                human_rating_overall=human_rating_overall,
                human_evaluated_at=human_evaluated_at,
                human_evaluated_by=human_evaluated_by,
                final_score=final_score,
                evaluated_at=target_date + timedelta(days=1),  # 다음날 평가
                created_at=datetime.now()
            )

            db.add(evaluation)
            created_count += 1

    db.commit()
    logger.info(f"✅ {created_count}건의 평가 데이터 생성 완료")

    return created_count


def run_aggregation(db: Session):
    """11월 1-5일 집계 실행"""
    logger.info("📊 11월 1-5일 집계 실행 중...")

    aggregation_service = AggregationService(db)

    for day_offset in range(5):
        target_date = date(2025, 11, 1) + timedelta(days=day_offset)

        try:
            result = aggregation_service.aggregate_daily_performance(target_date=target_date)
            logger.info(f"   - {target_date}: {len(result)}개 모델 집계 완료")
        except Exception as e:
            logger.error(f"   - {target_date} 집계 실패: {e}")

    logger.info("✅ 집계 완료")


def verify_data(db: Session):
    """생성된 데이터 검증"""
    logger.info("🔍 데이터 검증 중...")

    # 평가 데이터 확인
    total_evaluations = db.query(ModelEvaluation).count()
    logger.info(f"   - 총 평가 데이터: {total_evaluations}건")

    # 모델별 평가 건수
    from sqlalchemy import func
    model_counts = db.query(
        ModelEvaluation.model_id,
        func.count(ModelEvaluation.id)
    ).group_by(ModelEvaluation.model_id).all()

    for model_id, count in model_counts:
        logger.info(f"   - Model {model_id}: {count}건")

    # 사람 평가 건수
    human_evaluated = db.query(ModelEvaluation).filter(
        ModelEvaluation.human_rating_overall.isnot(None)
    ).count()
    if total_evaluations > 0:
        logger.info(f"   - 사람 평가: {human_evaluated}건 ({human_evaluated/total_evaluations*100:.1f}%)")

    # 집계 데이터 확인
    perf_records = db.query(DailyModelPerformance).count()
    logger.info(f"   - 집계 레코드: {perf_records}건")

    # 날짜별 집계
    daily_counts = db.query(
        DailyModelPerformance.date,
        func.count(DailyModelPerformance.id)
    ).group_by(DailyModelPerformance.date).order_by(DailyModelPerformance.date).all()

    for date_val, count in daily_counts:
        logger.info(f"   - {date_val}: {count}개 모델")

    logger.info("✅ 검증 완료")


def main():
    db = SessionLocal()
    try:
        # 1. 기존 데이터 삭제
        delete_existing_data(db)

        # 2. 11월 1-5일 평가 데이터 생성
        created_count = create_evaluation_data(db)

        if created_count == 0:
            logger.error("❌ 평가 데이터 생성 실패")
            return

        # 3. 집계 실행
        run_aggregation(db)

        # 4. 검증
        verify_data(db)

        logger.info("\n🎉 11월 1-5일 평가 데이터 생성 완료!")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
