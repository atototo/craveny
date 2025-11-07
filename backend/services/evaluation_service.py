"""
Model evaluation service for automated scoring.

이 서비스는 Investment Report의 예측 정확도를 자동으로 평가합니다.
매일 배치 작업으로 D-1일 예측을 평가하고 점수를 계산합니다.
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.stock import StockPrice
from backend.db.models.model_evaluation import ModelEvaluation
from backend.db.models.evaluation_history import EvaluationHistory


logger = logging.getLogger(__name__)


class EvaluationService:
    """
    모델 평가 서비스.

    Investment Report의 예측 정확도를 자동으로 평가합니다.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_evaluable_predictions(self, target_date: datetime) -> List[Prediction]:
        """
        평가 가능한 Investment Report 조회.

        Args:
            target_date: 평가 대상 날짜 (예: 어제)

        Returns:
            목표가/손절가가 있는 Investment Report 리스트
        """
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # 이미 평가된 prediction_id 조회
        evaluated_ids_query = self.db.query(ModelEvaluation.prediction_id).all()
        evaluated_ids = [e[0] for e in evaluated_ids_query]

        # Investment Report 조회
        # NOTE: 현재는 current_price가 있는 모든 prediction을 Investment Report로 간주
        # 추후 report_type 컬럼 추가 또는 별도 테이블 분리 권장
        query = self.db.query(Prediction).filter(
            Prediction.created_at >= start_of_day,
            Prediction.created_at <= end_of_day,
            Prediction.current_price.isnot(None),  # Investment Report 조건
        )

        # 중복 평가 방지
        if evaluated_ids:
            query = query.filter(Prediction.id.notin_(evaluated_ids))

        predictions = query.all()

        logger.info(f"📊 평가 대상 Investment Report: {len(predictions)}건")
        return predictions

    def get_evaluable_reports(self, target_date: datetime) -> List[StockAnalysisSummary]:
        """
        평가 가능한 Investment Report 조회 (StockAnalysisSummary).

        Args:
            target_date: 평가 대상 날짜 (예: 어제)

        Returns:
            목표가/손절가가 있는 Investment Report 리스트
        """
        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # 이미 평가된 report 조회 (stock_code + created_at 기준)
        evaluated_reports_query = self.db.query(
            ModelEvaluation.stock_code,
            ModelEvaluation.predicted_at
        ).filter(
            ModelEvaluation.predicted_at >= start_of_day,
            ModelEvaluation.predicted_at <= end_of_day
        ).all()
        evaluated_keys = [(r[0], r[1]) for r in evaluated_reports_query]

        # Investment Report 조회 (목표가/손절가가 있는 것만)
        reports = self.db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.last_updated >= start_of_day,
            StockAnalysisSummary.last_updated <= end_of_day,
            StockAnalysisSummary.base_price.isnot(None),
            StockAnalysisSummary.short_term_target_price.isnot(None),
            StockAnalysisSummary.short_term_support_price.isnot(None)
        ).all()

        # 중복 평가 방지 (stock_code + created_at 조합)
        reports = [
            r for r in reports
            if (r.stock_code, r.last_updated) not in evaluated_keys
        ]

        logger.info(f"📊 평가 대상 Investment Report (StockAnalysisSummary): {len(reports)}건")
        return reports

    def get_stock_prices(
        self,
        stock_code: str,
        base_date: datetime,
        days: int = 5
    ) -> Dict[int, Dict[str, any]]:
        """
        주가 데이터 조회 (T+1 ~ T+N일).

        Args:
            stock_code: 종목 코드
            base_date: 기준일 (예측 생성일)
            days: 조회할 일수 (기본 5일)

        Returns:
            {
                1: {"high": 50000, "low": 48000, "close": 49500, "date": "2025-11-06"},
                2: {"high": 51000, "low": 49000, "close": 50500, "date": "2025-11-07"},
                ...
            }
        """
        result = {}
        current_day = 1

        for offset in range(1, days * 2):  # 주말 고려하여 최대 2배
            target_date = base_date + timedelta(days=offset)

            # 주말 스킵 (토, 일)
            if target_date.weekday() >= 5:
                continue

            # 주가 데이터 조회
            stock_data = self.db.query(StockPrice).filter(
                StockPrice.stock_code == stock_code,
                StockPrice.date >= target_date.replace(hour=0, minute=0, second=0),
                StockPrice.date <= target_date.replace(hour=23, minute=59, second=59)
            ).first()

            if stock_data:
                result[current_day] = {
                    "high": stock_data.high,
                    "low": stock_data.low,
                    "close": stock_data.close,
                    "date": stock_data.date.strftime("%Y-%m-%d")
                }
                current_day += 1

                # 목표 일수 달성
                if current_day > days:
                    break
            else:
                logger.warning(f"⚠️ 주가 데이터 없음: {stock_code} on {target_date.date()}")

        return result

    def check_target_achievement(
        self,
        target_price: float,
        support_price: float,
        base_price: float,
        stock_prices: Dict[int, Dict[str, any]]
    ) -> Dict[str, any]:
        """
        목표가/손절가 달성 여부 판단.

        Args:
            target_price: 목표가
            support_price: 손절가
            base_price: 기준가
            stock_prices: get_stock_prices() 결과

        Returns:
            {
                "target_achieved": True/False,
                "target_achieved_days": 3,  # 3일 만에 달성
                "support_breached": False,
                "actual_high_1d": 50000,
                "actual_low_1d": 48000,
                "actual_close_1d": 49500,
                "actual_high_5d": 52000,
                "actual_low_5d": 47000,
                "actual_close_5d": 51000
            }
        """
        result = {
            "target_achieved": False,
            "target_achieved_days": None,
            "support_breached": False,
            "actual_high_1d": None,
            "actual_low_1d": None,
            "actual_close_1d": None,
            "actual_high_5d": None,
            "actual_low_5d": None,
            "actual_close_5d": None
        }

        if not stock_prices:
            return result

        # T+1일 데이터
        if 1 in stock_prices:
            result["actual_high_1d"] = stock_prices[1]["high"]
            result["actual_low_1d"] = stock_prices[1]["low"]
            result["actual_close_1d"] = stock_prices[1]["close"]

        # T+5일까지 추적
        max_day = max(stock_prices.keys()) if stock_prices else 0

        for day in range(1, max_day + 1):
            if day not in stock_prices:
                continue

            high = stock_prices[day]["high"]
            low = stock_prices[day]["low"]

            # 목표가 달성 확인 (최초 달성일만 기록)
            if not result["target_achieved"] and high >= target_price:
                result["target_achieved"] = True
                result["target_achieved_days"] = day
                logger.info(f"✅ 목표가 달성: {day}일 만에 {high:,}원")

            # 손절가 이탈 확인
            if low <= support_price:
                result["support_breached"] = True
                logger.warning(f"⚠️ 손절가 이탈: {day}일째 {low:,}원")

        # T+5일 최종 데이터
        if max_day >= 5 and 5 in stock_prices:
            result["actual_high_5d"] = stock_prices[5]["high"]
            result["actual_low_5d"] = stock_prices[5]["low"]
            result["actual_close_5d"] = stock_prices[5]["close"]

        return result

    def calculate_auto_score(
        self,
        target_price: float,
        support_price: float,
        base_price: float,
        achievement: Dict[str, any]
    ) -> Dict[str, float]:
        """
        자동 평가 점수 계산 (0-100점).

        Args:
            target_price: 목표가
            support_price: 손절가
            base_price: 기준가
            achievement: check_target_achievement() 결과

        Returns:
            {
                "target_accuracy_score": 85.5,
                "timing_score": 80.0,
                "risk_management_score": 100.0
            }
        """
        scores = {}

        # 1. 목표가 정확도 점수 (40%)
        if achievement["target_achieved"]:
            scores["target_accuracy_score"] = 100.0
        else:
            # 미달성 시: 실제 도달한 비율
            actual_high = achievement["actual_high_5d"] or achievement["actual_high_1d"] or base_price
            if actual_high > base_price and target_price > base_price:
                ratio = (actual_high - base_price) / (target_price - base_price)
                scores["target_accuracy_score"] = min(100.0, max(0.0, ratio * 100))
            else:
                scores["target_accuracy_score"] = 0.0

        # 2. 타이밍 점수 (30%)
        if achievement["target_achieved"]:
            days = achievement["target_achieved_days"]
            # 1일: 100, 2일: 90, 3일: 80, 4일: 70, 5일: 60
            scores["timing_score"] = max(60.0, 110 - (days * 10))
        else:
            scores["timing_score"] = 0.0

        # 3. 리스크 관리 점수 (30%)
        if not achievement["support_breached"]:
            scores["risk_management_score"] = 100.0
        else:
            # 손절가 대비 이탈 비율
            actual_low = achievement["actual_low_5d"] or achievement["actual_low_1d"] or base_price
            if support_price > 0:
                breach_ratio = abs((actual_low - support_price) / support_price) * 100
                scores["risk_management_score"] = max(0.0, 100 - breach_ratio)
            else:
                scores["risk_management_score"] = 0.0

        logger.info(
            f"📊 자동 점수: 정확도={scores['target_accuracy_score']:.1f}, "
            f"타이밍={scores['timing_score']:.1f}, "
            f"리스크={scores['risk_management_score']:.1f}"
        )

        return scores

    def save_evaluation(
        self,
        prediction: Prediction,
        achievement: Dict[str, any],
        scores: Dict[str, float],
        target_price: float,
        support_price: float
    ) -> ModelEvaluation:
        """
        평가 결과 저장.

        Args:
            prediction: 평가 대상 예측
            achievement: 달성 여부 결과
            scores: 자동 점수 결과
            target_price: 목표가
            support_price: 손절가

        Returns:
            생성된 ModelEvaluation 객체
        """
        evaluation = ModelEvaluation(
            prediction_id=prediction.id,
            model_id=prediction.model_id,
            stock_code=prediction.stock_code,

            # 예측 정보 스냅샷
            predicted_at=prediction.created_at,
            prediction_period=prediction.target_period or "1일~5일",
            predicted_target_price=target_price,
            predicted_support_price=support_price,
            predicted_base_price=prediction.current_price,
            predicted_confidence=prediction.confidence,

            # 실제 결과
            actual_high_1d=achievement["actual_high_1d"],
            actual_low_1d=achievement["actual_low_1d"],
            actual_close_1d=achievement["actual_close_1d"],
            actual_high_5d=achievement["actual_high_5d"],
            actual_low_5d=achievement["actual_low_5d"],
            actual_close_5d=achievement["actual_close_5d"],

            target_achieved=achievement["target_achieved"],
            target_achieved_days=achievement["target_achieved_days"],
            support_breached=achievement["support_breached"],

            # 자동 점수
            target_accuracy_score=scores["target_accuracy_score"],
            timing_score=scores["timing_score"],
            risk_management_score=scores["risk_management_score"],

            # 최종 점수 (사람 평가 없으므로 자동 점수만, 가중치 40:30:30)
            final_score=(
                scores["target_accuracy_score"] * 0.4 +
                scores["timing_score"] * 0.3 +
                scores["risk_management_score"] * 0.3
            ),

            evaluated_at=datetime.now()
        )

        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

        logger.info(f"✅ 평가 저장 완료: ID {evaluation.id}, 최종 점수 {evaluation.final_score:.1f}")
        return evaluation

    def evaluate_prediction(
        self,
        prediction: Prediction,
        target_price: Optional[float] = None,
        support_price: Optional[float] = None
    ) -> Optional[ModelEvaluation]:
        """
        단일 예측 평가 (헬퍼 메서드).

        Args:
            prediction: 평가 대상 예측
            target_price: 목표가 (None이면 current_price * 1.1 사용)
            support_price: 손절가 (None이면 current_price * 0.9 사용)

        Returns:
            생성된 ModelEvaluation 객체 또는 None (실패 시)
        """
        try:
            # 기본값 설정 (임시)
            if target_price is None:
                target_price = prediction.current_price * 1.1
            if support_price is None:
                support_price = prediction.current_price * 0.9

            base_price = prediction.current_price

            # 주가 데이터 조회
            stock_prices = self.get_stock_prices(
                stock_code=prediction.stock_code,
                base_date=prediction.created_at,
                days=5
            )

            if not stock_prices:
                logger.warning(f"⚠️ 주가 데이터 없음: {prediction.stock_code}")
                return None

            # 달성 여부 판단
            achievement = self.check_target_achievement(
                target_price=target_price,
                support_price=support_price,
                base_price=base_price,
                stock_prices=stock_prices
            )

            # 자동 점수 계산
            scores = self.calculate_auto_score(
                target_price=target_price,
                support_price=support_price,
                base_price=base_price,
                achievement=achievement
            )

            # 평가 결과 저장
            evaluation = self.save_evaluation(
                prediction=prediction,
                achievement=achievement,
                scores=scores,
                target_price=target_price,
                support_price=support_price
            )

            return evaluation

        except Exception as e:
            logger.error(f"❌ 평가 실패: {prediction.id}, {e}", exc_info=True)
            return None

    def evaluate_report(
        self,
        report: StockAnalysisSummary,
        model_id: int = 1  # Default to main model
    ) -> Optional[ModelEvaluation]:
        """
        단일 Investment Report 평가 (StockAnalysisSummary).

        Args:
            report: 평가 대상 Investment Report
            model_id: 모델 ID (1=Model A, 2=Model B)

        Returns:
            생성된 ModelEvaluation 객체 또는 None (실패 시)
        """
        try:
            # A/B 테스트 리포트인 경우 모델별 데이터 사용
            if report.custom_data and report.custom_data.get('ab_test_enabled'):
                # A/B 테스트 설정에서 모델 ID 확인
                from backend.db.models.ab_test_config import ABTestConfig
                ab_config = self.db.query(ABTestConfig).filter(
                    ABTestConfig.is_active == True
                ).first()

                # model_id가 Model A인지 Model B인지 판단
                if ab_config:
                    model_key = 'model_a' if model_id == ab_config.model_a_id else 'model_b'
                else:
                    # fallback: ID가 작은 쪽을 Model A로 간주
                    model_key = 'model_a' if model_id <= 2 else 'model_b'

                model_data = report.custom_data.get(model_key, {})
                price_targets = model_data.get('price_targets', {})

                target_price = price_targets.get('short_term_target')
                support_price = price_targets.get('short_term_support')
                base_price = price_targets.get('base_price')

                if not target_price or not support_price or not base_price:
                    logger.warning(f"⚠️ {model_key} 가격 정보 없음: {report.stock_code}")
                    return None
            else:
                # 일반 리포트는 테이블 레벨 데이터 사용
                target_price = report.short_term_target_price
                support_price = report.short_term_support_price
                base_price = report.base_price

                if not target_price or not support_price or not base_price:
                    logger.warning(f"⚠️ 필수 가격 정보 없음: {report.stock_code}")
                    return None

            # 주가 데이터 조회
            stock_prices = self.get_stock_prices(
                stock_code=report.stock_code,
                base_date=report.last_updated,
                days=5
            )

            if not stock_prices:
                logger.warning(f"⚠️ 주가 데이터 없음: {report.stock_code}")
                return None

            # 달성 여부 판단
            achievement = self.check_target_achievement(
                target_price=target_price,
                support_price=support_price,
                base_price=base_price,
                stock_prices=stock_prices
            )

            # 자동 점수 계산
            scores = self.calculate_auto_score(
                target_price=target_price,
                support_price=support_price,
                base_price=base_price,
                achievement=achievement
            )

            # 평가 결과 저장
            evaluation = ModelEvaluation(
                prediction_id=report.id,  # StockAnalysisSummary의 ID를 prediction_id로 사용
                model_id=model_id,
                stock_code=report.stock_code,

                # 예측 정보 스냅샷
                predicted_at=report.last_updated,
                prediction_period="1일~5일",
                predicted_target_price=target_price,
                predicted_support_price=support_price,
                predicted_base_price=base_price,
                predicted_confidence=report.avg_confidence,

                # 실제 결과
                actual_high_1d=achievement["actual_high_1d"],
                actual_low_1d=achievement["actual_low_1d"],
                actual_close_1d=achievement["actual_close_1d"],
                actual_high_5d=achievement["actual_high_5d"],
                actual_low_5d=achievement["actual_low_5d"],
                actual_close_5d=achievement["actual_close_5d"],

                target_achieved=achievement["target_achieved"],
                target_achieved_days=achievement["target_achieved_days"],
                support_breached=achievement["support_breached"],

                # 자동 점수
                target_accuracy_score=scores["target_accuracy_score"],
                timing_score=scores["timing_score"],
                risk_management_score=scores["risk_management_score"],

                # 최종 점수 (사람 평가 없으므로 자동 점수만, 가중치 40:30:30)
                final_score=(
                    scores["target_accuracy_score"] * 0.4 +
                    scores["timing_score"] * 0.3 +
                    scores["risk_management_score"] * 0.3
                ),

                evaluated_at=datetime.now()
            )

            self.db.add(evaluation)
            self.db.commit()
            self.db.refresh(evaluation)

            logger.info(f"✅ 평가 저장 완료: {report.stock_code}, 최종 점수 {evaluation.final_score:.1f}")
            return evaluation

        except Exception as e:
            logger.error(f"❌ 평가 실패: {report.stock_code}, {e}", exc_info=True)
            self.db.rollback()
            return None

    def update_human_rating(
        self,
        evaluation_id: int,
        quality: int,
        usefulness: int,
        overall: int,
        evaluated_by: str,
        reason: Optional[str] = None
    ) -> Optional[ModelEvaluation]:
        """
        사람 평가 업데이트 및 final_score 재계산.

        Args:
            evaluation_id: 평가 ID
            quality: 분석 품질 점수 (1-5)
            usefulness: 실용성 점수 (1-5)
            overall: 종합 만족도 점수 (1-5)
            evaluated_by: 평가자 이름
            reason: 평가 사유 (선택사항)

        Returns:
            업데이트된 ModelEvaluation 객체 또는 None (실패 시)
        """
        try:
            # 평가 조회
            evaluation = self.db.query(ModelEvaluation).filter(
                ModelEvaluation.id == evaluation_id
            ).first()

            if not evaluation:
                logger.error(f"❌ 평가 없음: evaluation_id={evaluation_id}")
                return None

            # 사람 평가 점수 검증 (1-5)
            if not all(1 <= score <= 5 for score in [quality, usefulness, overall]):
                logger.error(f"❌ 잘못된 점수 범위: {quality}, {usefulness}, {overall}")
                return None

            # 기존 값 저장 (히스토리용)
            old_quality = evaluation.human_rating_quality
            old_usefulness = evaluation.human_rating_usefulness
            old_overall = evaluation.human_rating_overall
            old_final_score = evaluation.final_score

            # 사람 평가 업데이트
            evaluation.human_rating_quality = quality
            evaluation.human_rating_usefulness = usefulness
            evaluation.human_rating_overall = overall
            evaluation.human_evaluated_by = evaluated_by
            evaluation.human_evaluated_at = datetime.now()

            # 자동 점수 (0-100)
            auto_score = (
                (evaluation.target_accuracy_score or 0) * 0.4 +
                (evaluation.timing_score or 0) * 0.3 +
                (evaluation.risk_management_score or 0) * 0.3
            )

            # 사람 평가 점수 (1-5 → 0-100 변환)
            avg_human_rating = (quality + usefulness + overall) / 3
            human_score = avg_human_rating * 20  # 1-5 → 20-100

            # final_score 재계산 (자동 70% + 사람 30%)
            evaluation.final_score = auto_score * 0.7 + human_score * 0.3

            # 평가 히스토리 기록 (수정인 경우에만)
            if old_quality is not None or old_usefulness is not None or old_overall is not None:
                history = EvaluationHistory(
                    evaluation_id=evaluation_id,
                    old_human_rating_quality=old_quality,
                    old_human_rating_usefulness=old_usefulness,
                    old_human_rating_overall=old_overall,
                    old_final_score=old_final_score,
                    new_human_rating_quality=quality,
                    new_human_rating_usefulness=usefulness,
                    new_human_rating_overall=overall,
                    new_final_score=evaluation.final_score,
                    modified_by=evaluated_by,
                    reason=reason
                )
                self.db.add(history)
                logger.info(f"📝 평가 히스토리 기록: evaluation_id={evaluation_id}")

            self.db.commit()
            self.db.refresh(evaluation)

            logger.info(
                f"✅ 사람 평가 업데이트: ID {evaluation_id}, "
                f"평가={quality}/{usefulness}/{overall}, "
                f"final_score={evaluation.final_score:.1f} "
                f"(auto={auto_score:.1f}, human={human_score:.1f})"
            )

            return evaluation

        except Exception as e:
            logger.error(f"❌ 사람 평가 업데이트 실패: {evaluation_id}, {e}", exc_info=True)
            self.db.rollback()
            return None
