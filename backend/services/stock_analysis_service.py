"""
Stock Analysis Service

예측 생성 시 자동으로 종합 투자 리포트를 업데이트하는 서비스
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.stock import StockPrice
from backend.llm.investment_report import get_report_generator
from backend.utils.stock_mapping import get_stock_mapper


logger = logging.getLogger(__name__)


async def update_stock_analysis_summary(
    stock_code: str,
    db: Session,
    force_update: bool = False
) -> Optional[StockAnalysisSummary]:
    """
    종목 투자 분석 요약 업데이트 (LLM 기반)

    Args:
        stock_code: 종목 코드
        db: Database session
        force_update: 강제 업데이트 여부 (기본값: False)

    Returns:
        StockAnalysisSummary 인스턴스 또는 None (실패 시)
    """
    try:
        # 1. 최근 30일 예측 데이터 조회 (최대 20건)
        predictions = (
            db.query(Prediction)
            .filter(Prediction.stock_code == stock_code)
            .order_by(Prediction.created_at.desc())
            .limit(20)
            .all()
        )

        if not predictions:
            logger.warning(f"종목 {stock_code}에 대한 예측 데이터가 없습니다.")
            return None

        # 2. 현재가 정보 조회
        current_price_obj = (
            db.query(StockPrice)
            .filter(StockPrice.stock_code == stock_code)
            .order_by(StockPrice.date.desc())
            .first()
        )

        current_price = None
        if current_price_obj:
            # 전일 대비 변동률 계산
            previous_price_obj = (
                db.query(StockPrice)
                .filter(
                    StockPrice.stock_code == stock_code,
                    StockPrice.date < current_price_obj.date
                )
                .order_by(StockPrice.date.desc())
                .first()
            )

            change_rate = 0.0
            if previous_price_obj and previous_price_obj.close > 0:
                change_rate = ((current_price_obj.close - previous_price_obj.close) / previous_price_obj.close) * 100

            current_price = {
                "close": current_price_obj.close,
                "change_rate": round(change_rate, 2),
            }

        # 3. 기존 요약 조회
        existing_summary = (
            db.query(StockAnalysisSummary)
            .filter(StockAnalysisSummary.stock_code == stock_code)
            .first()
        )

        # 4. 업데이트 필요 여부 확인
        if not force_update and existing_summary:
            # 총 예측 개수 조회 (limit 없이)
            total_prediction_count = (
                db.query(func.count(Prediction.id))
                .filter(Prediction.stock_code == stock_code)
                .scalar()
            )

            # 예측 개수 증가 또는 24시간 경과 시 업데이트
            staleness_hours = (datetime.now() - existing_summary.last_updated).total_seconds() / 3600

            if (existing_summary.based_on_prediction_count >= total_prediction_count
                and staleness_hours < 24):
                logger.info(
                    f"종목 {stock_code}의 분석 요약이 최신 상태입니다. "
                    f"(예측 건수: {total_prediction_count}, 경과 시간: {staleness_hours:.1f}시간)"
                )
                return existing_summary

            logger.info(
                f"종목 {stock_code} 업데이트 필요: "
                f"예측 개수 변화 ({existing_summary.based_on_prediction_count} → {total_prediction_count}) "
                f"또는 24시간 경과 ({staleness_hours:.1f}시간)"
            )

        # 5. LLM 리포트 생성
        logger.info(f"종목 {stock_code}에 대한 투자 리포트 생성 시작...")
        generator = get_report_generator()

        # A/B 테스트 활성화 시 dual_generate_report 사용
        from backend.config import settings
        if settings.AB_TEST_ENABLED:
            report = generator.dual_generate_report(stock_code, predictions, current_price)
        else:
            report = generator.generate_report(stock_code, predictions, current_price)

        if not report or (not settings.AB_TEST_ENABLED and not report.get("overall_summary")):
            logger.error(f"종목 {stock_code}의 리포트 생성 실패")
            return None

        # 6. 통계 계산
        total_predictions = len(predictions)
        up_count = sum(1 for p in predictions if p.direction == "up")
        down_count = sum(1 for p in predictions if p.direction == "down")
        hold_count = sum(1 for p in predictions if p.direction == "hold")

        confidences = [p.confidence for p in predictions if p.confidence]
        avg_confidence = sum(confidences) / len(confidences) if confidences else None

        # 7. A/B 테스트 활성화 시 전체 report를 JSON으로 저장
        if settings.AB_TEST_ENABLED:
            # A/B 리포트 전체를 JSON 필드에 저장 (analysis_summary_a, analysis_summary_b)
            if existing_summary:
                # custom_data 필드에 A/B 리포트 저장
                existing_summary.custom_data = report
                existing_summary.overall_summary = "A/B 테스트 활성화 (Model A/B 비교 리포트)"
                existing_summary.total_predictions = total_predictions
                existing_summary.up_count = up_count
                existing_summary.down_count = down_count
                existing_summary.hold_count = hold_count
                existing_summary.avg_confidence = avg_confidence
                existing_summary.last_updated = datetime.now()
                existing_summary.based_on_prediction_count = total_predictions
                summary = existing_summary
                logger.info(f"종목 {stock_code}의 A/B 분석 요약 업데이트 완료")
            else:
                summary = StockAnalysisSummary(
                    stock_code=stock_code,
                    overall_summary="A/B 테스트 활성화 (Model A/B 비교 리포트)",
                    custom_data=report,
                    total_predictions=total_predictions,
                    up_count=up_count,
                    down_count=down_count,
                    hold_count=hold_count,
                    avg_confidence=avg_confidence,
                    last_updated=datetime.now(),
                    based_on_prediction_count=total_predictions
                )
                db.add(summary)
                logger.info(f"종목 {stock_code}의 A/B 분석 요약 생성 완료")
        else:
            # 단일 모델 리포트 저장
            if existing_summary:
                # 업데이트
                existing_summary.overall_summary = report.get("overall_summary")
                existing_summary.short_term_scenario = report.get("short_term_scenario")
                existing_summary.medium_term_scenario = report.get("medium_term_scenario")
                existing_summary.long_term_scenario = report.get("long_term_scenario")
                existing_summary.risk_factors = report.get("risk_factors", [])
                existing_summary.opportunity_factors = report.get("opportunity_factors", [])
                existing_summary.recommendation = report.get("recommendation")

                existing_summary.total_predictions = total_predictions
                existing_summary.up_count = up_count
                existing_summary.down_count = down_count
                existing_summary.hold_count = hold_count
                existing_summary.avg_confidence = avg_confidence

                existing_summary.last_updated = datetime.now()
                existing_summary.based_on_prediction_count = total_predictions

                summary = existing_summary
                logger.info(f"종목 {stock_code}의 분석 요약 업데이트 완료")
            else:
                # 신규 생성
                summary = StockAnalysisSummary(
                    stock_code=stock_code,
                    overall_summary=report.get("overall_summary"),
                    short_term_scenario=report.get("short_term_scenario"),
                    medium_term_scenario=report.get("medium_term_scenario"),
                    long_term_scenario=report.get("long_term_scenario"),
                    risk_factors=report.get("risk_factors", []),
                    opportunity_factors=report.get("opportunity_factors", []),
                    recommendation=report.get("recommendation"),

                total_predictions=total_predictions,
                up_count=up_count,
                down_count=down_count,
                hold_count=hold_count,
                avg_confidence=avg_confidence,

                last_updated=datetime.now(),
                based_on_prediction_count=total_predictions,
            )
            db.add(summary)
            logger.info(f"종목 {stock_code}의 분석 요약 신규 생성 완료")

        db.commit()
        db.refresh(summary)

        return summary

    except Exception as e:
        logger.error(f"종목 {stock_code}의 분석 요약 업데이트 실패: {e}", exc_info=True)
        db.rollback()
        return None


def get_stock_analysis_summary(
    stock_code: str,
    db: Session
) -> Optional[Dict[str, Any]]:
    """
    종목 투자 분석 요약 조회

    Args:
        stock_code: 종목 코드
        db: Database session

    Returns:
        분석 요약 딕셔너리 또는 None
    """
    try:
        summary = (
            db.query(StockAnalysisSummary)
            .filter(StockAnalysisSummary.stock_code == stock_code)
            .first()
        )

        if not summary:
            return None

        # A/B 테스트 활성화 시 custom_data에서 A/B 리포트 반환
        from backend.config import settings
        if settings.AB_TEST_ENABLED and summary.custom_data:
            # custom_data에 A/B 리포트가 저장되어 있음
            return summary.custom_data
        else:
            # 단일 모델 리포트 반환
            return {
                "overall_summary": summary.overall_summary,
                "short_term_scenario": summary.short_term_scenario,
                "medium_term_scenario": summary.medium_term_scenario,
                "long_term_scenario": summary.long_term_scenario,
                "risk_factors": summary.risk_factors or [],
                "opportunity_factors": summary.opportunity_factors or [],
                "recommendation": summary.recommendation,

                "statistics": {
                    "total_predictions": summary.total_predictions,
                    "up_count": summary.up_count,
                    "down_count": summary.down_count,
                    "hold_count": summary.hold_count,
                    "avg_confidence": round(summary.avg_confidence * 100, 1) if summary.avg_confidence else None,
                },

                "meta": {
                    "last_updated": summary.last_updated.isoformat() if summary.last_updated else None,
                    "based_on_prediction_count": summary.based_on_prediction_count,
                }
            }

    except Exception as e:
        logger.error(f"종목 {stock_code}의 분석 요약 조회 실패: {e}", exc_info=True)
        return None
