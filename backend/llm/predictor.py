"""
주가 예측 모듈

유사 뉴스 기반 LLM 주가 예측 기능을 제공합니다.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from openai import OpenAI
from sqlalchemy.orm import Session

from backend.config import settings
from backend.llm.prediction_cache import get_prediction_cache
from backend.db.models.stock import StockPrice, Stock
from backend.db.models.news import NewsArticle
from backend.db.models.model import Model
from backend.db.models.ab_test_config import ABTestConfig
from backend.db.session import SessionLocal
from sqlalchemy import text


logger = logging.getLogger(__name__)


class StockPredictor:
    """LLM 기반 주가 예측 클래스"""

    def __init__(self):
        """예측 모델 초기화"""
        # 기존 호환성을 위한 기본 클라이언트
        if settings.LLM_PROVIDER == "openrouter":
            self.client = OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://craveny.ai",
                    "X-Title": "Craveny Stock Predictor",
                }
            )
            self.model = settings.OPENROUTER_MODEL
            logger.info(f"OpenRouter 모델 사용: {self.model}")
        else:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
            logger.info(f"OpenAI 모델 사용: {self.model}")

        self.cache = get_prediction_cache()

        # 멀티모델: DB에서 활성 모델 로드
        self.active_models = self._load_active_models()
        logger.info(f"✅ 활성 모델 {len(self.active_models)}개 로드 완료")

        # 레거시 A/B 테스트 (환경변수 기반) - 하위 호환성
        if settings.AB_TEST_ENABLED:
            self.client_a = self._create_client(settings.MODEL_A_PROVIDER)
            self.model_a = settings.MODEL_A_NAME
            self.client_b = self._create_client(settings.MODEL_B_PROVIDER)
            self.model_b = settings.MODEL_B_NAME
            logger.info(f"A/B 테스트 활성화 (레거시): Model A={self.model_a}, Model B={self.model_b}")

    def _create_client(self, provider: str) -> OpenAI:
        """프로바이더별 OpenAI 클라이언트 생성"""
        if provider == "openrouter":
            return OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://craveny.ai",
                    "X-Title": "Craveny Stock Predictor",
                }
            )
        else:  # openai
            return OpenAI(api_key=settings.OPENAI_API_KEY)

    def _load_active_models(self) -> Dict[int, Dict[str, Any]]:
        """
        DB에서 활성 모델 목록을 조회하고 클라이언트를 생성합니다.

        Returns:
            {model_id: {"name": "...", "provider": "...", "model_identifier": "...", "client": OpenAI(...)}}
        """
        db = SessionLocal()
        try:
            models = db.query(Model).filter(Model.is_active == True).all()
            result = {}

            for model in models:
                client = self._create_client(model.provider)
                result[model.id] = {
                    "name": model.name,
                    "provider": model.provider,
                    "model_identifier": model.model_identifier,
                    "client": client,
                    "description": model.description,
                }
                logger.info(f"  📊 Model loaded: {model.name} ({model.provider}/{model.model_identifier})")

            return result

        except Exception as e:
            logger.error(f"활성 모델 로드 실패: {e}")
            return {}
        finally:
            db.close()

    def _save_model_prediction(
        self,
        news_id: int,
        model_id: int,
        stock_code: str,
        prediction_data: Dict[str, Any]
    ) -> None:
        """
        모델 예측 결과를 predictions 테이블에 저장합니다.

        Args:
            news_id: 뉴스 ID
            model_id: 모델 ID
            stock_code: 종목 코드
            prediction_data: 예측 결과
        """
        db = SessionLocal()
        try:
            from backend.db.models.prediction import Prediction

            # 기존 예측이 있는지 확인
            existing = db.query(Prediction).filter(
                Prediction.news_id == news_id,
                Prediction.model_id == model_id
            ).first()

            # prediction_data에서 새 필드 추출
            sentiment_direction = prediction_data.get("sentiment_direction", "neutral")
            sentiment_score = prediction_data.get("sentiment_score", 0.0)
            impact_level = prediction_data.get("impact_level", "low")
            relevance_score = prediction_data.get("relevance_score", 0.0)
            urgency_level = prediction_data.get("urgency_level", "routine")
            impact_analysis = prediction_data.get("impact_analysis", {})
            reasoning = prediction_data.get("reasoning", "")
            current_price = prediction_data.get("current_price")
            pattern_analysis = prediction_data.get("pattern_analysis", {})

            # Deprecated 필드는 None으로 설정
            direction = None
            confidence = None
            short_term = None
            medium_term = None
            long_term = None
            confidence_breakdown = None

            if existing:
                # UPDATE
                existing.sentiment_direction = sentiment_direction
                existing.sentiment_score = sentiment_score
                existing.impact_level = impact_level
                existing.relevance_score = relevance_score
                existing.urgency_level = urgency_level
                existing.impact_analysis = impact_analysis
                existing.reasoning = reasoning
                existing.current_price = current_price
                existing.pattern_analysis = pattern_analysis
                # Deprecated 필드는 None으로
                existing.direction = None
                existing.confidence = None
                existing.short_term = None
                existing.medium_term = None
                existing.long_term = None
                existing.confidence_breakdown = None
                existing.created_at = datetime.now()
            else:
                # INSERT
                new_prediction = Prediction(
                    news_id=news_id,
                    model_id=model_id,
                    stock_code=stock_code,
                    # 새 필드
                    sentiment_direction=sentiment_direction,
                    sentiment_score=sentiment_score,
                    impact_level=impact_level,
                    relevance_score=relevance_score,
                    urgency_level=urgency_level,
                    impact_analysis=impact_analysis,
                    reasoning=reasoning,
                    current_price=current_price,
                    pattern_analysis=pattern_analysis,
                    # Deprecated 필드는 None
                    direction=None,
                    confidence=None,
                    short_term=None,
                    medium_term=None,
                    long_term=None,
                    confidence_breakdown=None,
                )
                db.add(new_prediction)

            db.commit()
            logger.debug(
                f"모델 {model_id} 영향도 분석 저장 완료: news_id={news_id}, "
                f"sentiment={sentiment_direction} ({sentiment_score:.2f}), "
                f"impact={impact_level}, relevance={relevance_score:.2f}"
            )

        except Exception as e:
            logger.error(f"모델 예측 저장 실패 (news_id={news_id}, model_id={model_id}): {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()

    def _get_prediction_from_db(
        self,
        news_id: int,
        model_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        predictions 테이블에서 특정 모델의 예측 결과를 조회합니다.

        Args:
            news_id: 뉴스 ID
            model_id: 모델 ID

        Returns:
            예측 결과 또는 None
        """
        db = SessionLocal()
        try:
            from backend.db.models.prediction import Prediction

            prediction = db.query(Prediction).filter(
                Prediction.news_id == news_id,
                Prediction.model_id == model_id
            ).first()

            if not prediction:
                return None

            # Prediction 객체를 딕셔너리로 변환
            return {
                "direction": prediction.direction,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
                "current_price": prediction.current_price,
                "short_term": prediction.short_term,
                "medium_term": prediction.medium_term,
                "long_term": prediction.long_term,
                "confidence_breakdown": prediction.confidence_breakdown,
                "pattern_analysis": prediction.pattern_analysis,
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None,
            }

        except Exception as e:
            logger.error(f"모델 예측 조회 실패: {e}")
            return None
        finally:
            db.close()

    def _get_active_ab_config(self) -> Optional[ABTestConfig]:
        """현재 활성화된 A/B 설정을 조회합니다."""
        db = SessionLocal()
        try:
            config = db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first()
            return config
        except Exception as e:
            logger.error(f"A/B 설정 조회 실패: {e}")
            return None
        finally:
            db.close()

    def _get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        종목 기본 정보를 조회합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            종목 정보 딕셔너리 또는 None
        """
        db = SessionLocal()
        try:
            stock = db.query(Stock).filter(Stock.code == stock_code).first()
            if not stock:
                return None

            return {
                "code": stock.code,
                "name": stock.name,
                "priority": stock.priority,
            }
        except Exception as e:
            logger.error(f"종목 정보 조회 실패 (종목코드: {stock_code}): {e}")
            return None
        finally:
            db.close()

    def _get_current_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        현재 주가 정보를 조회합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            주가 정보 딕셔너리 또는 None
            {
                "close": 종가,
                "open": 시가,
                "high": 고가,
                "low": 저가,
                "volume": 거래량,
                "change_rate": 전일 대비 변동률 (%),
                "date": 날짜
            }
        """
        db = SessionLocal()
        try:
            # 최근 2일 데이터 조회 (변동률 계산용)
            recent_prices = (
                db.query(StockPrice)
                .filter(StockPrice.stock_code == stock_code)
                .order_by(StockPrice.date.desc())
                .limit(2)
                .all()
            )

            if not recent_prices:
                return None

            current = recent_prices[0]

            # 변동률 계산
            change_rate = 0.0
            if len(recent_prices) >= 2:
                previous = recent_prices[1]
                if previous.close > 0:
                    change_rate = ((current.close - previous.close) / previous.close) * 100

            return {
                "close": current.close,
                "open": current.open,
                "high": current.high,
                "low": current.low,
                "volume": current.volume,
                "change_rate": round(change_rate, 2),
                "date": current.date.strftime("%Y-%m-%d %H:%M") if current.date else "N/A",
            }

        except Exception as e:
            logger.error(f"현재 주가 조회 실패 (종목코드: {stock_code}): {e}")
            return None
        finally:
            db.close()

    def _get_recent_disclosures(self, stock_code: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        최근 DART 공시 정보를 조회합니다.

        Args:
            stock_code: 종목 코드
            days: 조회할 기간 (일)

        Returns:
            공시 정보 리스트
        """
        db = SessionLocal()
        try:
            since_date = datetime.now() - timedelta(days=days)

            disclosures = (
                db.query(NewsArticle)
                .filter(
                    NewsArticle.stock_code == stock_code,
                    NewsArticle.source == "dart",
                    NewsArticle.published_at >= since_date
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(5)
                .all()
            )

            return [
                {
                    "title": disc.title,
                    "published_at": disc.published_at.strftime("%Y-%m-%d"),
                    "content": disc.content[:100] + "..." if len(disc.content) > 100 else disc.content,
                }
                for disc in disclosures
            ]

        except Exception as e:
            logger.error(f"DART 공시 조회 실패 (종목코드: {stock_code}): {e}")
            return []
        finally:
            db.close()

    def _get_market_context(self) -> Dict[str, Any]:
        """
        시장 지수 맥락 정보를 조회합니다.

        Returns:
            시장 지수 정보 딕셔너리
        """
        db = SessionLocal()
        try:
            from sqlalchemy import text

            # KOSPI 최신 데이터
            kospi_result = db.execute(
                text("""
                    SELECT close, change_pct, date
                    FROM market_indices
                    WHERE index_name = 'KOSPI'
                    ORDER BY date DESC
                    LIMIT 1
                """)
            )
            kospi_row = kospi_result.fetchone()

            # KOSDAQ 최신 데이터
            kosdaq_result = db.execute(
                text("""
                    SELECT close, change_pct, date
                    FROM market_indices
                    WHERE index_name = 'KOSDAQ'
                    ORDER BY date DESC
                    LIMIT 1
                """)
            )
            kosdaq_row = kosdaq_result.fetchone()

            return {
                "kospi": {
                    "close": round(kospi_row[0], 2) if kospi_row else None,
                    "change_pct": round(kospi_row[1], 2) if kospi_row else None,
                    "date": kospi_row[2].strftime("%Y-%m-%d") if kospi_row else None,
                } if kospi_row else None,
                "kosdaq": {
                    "close": round(kosdaq_row[0], 2) if kosdaq_row else None,
                    "change_pct": round(kosdaq_row[1], 2) if kosdaq_row else None,
                    "date": kosdaq_row[2].strftime("%Y-%m-%d") if kosdaq_row else None,
                } if kosdaq_row else None,
            }

        except Exception as e:
            logger.error(f"시장 지수 조회 실패: {e}")
            return {"kospi": None, "kosdaq": None}
        finally:
            db.close()

    def _get_sector_indices(self, top_n: int = 5) -> Dict[str, Any]:
        """
        섹터별 지수 정보 조회 (변동률 상위/하위)

        Args:
            top_n: 상위/하위 각각 조회할 섹터 수

        Returns:
            섹터 지수 정보 딕셔너리
        """
        db = SessionLocal()
        try:
            from sqlalchemy import text

            # 최신 날짜의 섹터 지수 조회 (변동률 기준 정렬)
            result = db.execute(
                text("""
                    WITH latest_date AS (
                        SELECT MAX(date) as max_date FROM sector_indices
                    )
                    SELECT
                        sector_name,
                        close,
                        change_pct
                    FROM sector_indices
                    WHERE date = (SELECT max_date FROM latest_date)
                    AND change_pct IS NOT NULL
                    ORDER BY change_pct DESC
                """)
            )
            all_sectors = result.fetchall()

            if not all_sectors or len(all_sectors) == 0:
                logger.warning("섹터 지수 데이터 없음")
                return {"top_sectors": [], "bottom_sectors": []}

            # 상위 N개
            top_sectors = [
                {
                    "name": row[0],
                    "close": round(row[1], 2),
                    "change_pct": round(row[2], 2)
                }
                for row in all_sectors[:top_n]
            ]

            # 하위 N개
            bottom_sectors = [
                {
                    "name": row[0],
                    "close": round(row[1], 2),
                    "change_pct": round(row[2], 2)
                }
                for row in all_sectors[-top_n:]
            ]

            return {
                "top_sectors": top_sectors,
                "bottom_sectors": bottom_sectors
            }

        except Exception as e:
            logger.error(f"섹터 지수 조회 실패: {e}")
            return {"top_sectors": [], "bottom_sectors": []}
        finally:
            db.close()

    def _get_technical_indicators(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        기술적 지표를 계산합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            기술적 지표 딕셔너리 또는 None
            {
                "moving_averages": {
                    "ma5": float,
                    "ma20": float,
                    "ma60": float,
                    "current_vs_ma5": float,  # 현재가 대비 %
                    "current_vs_ma20": float,
                    "current_vs_ma60": float,
                    "trend": str  # "강세", "중립", "약세"
                },
                "volume_analysis": {
                    "current_volume": int,
                    "avg_volume_20d": float,
                    "volume_ratio": float,  # 평균 대비 %
                    "trend": str  # "급증", "보통", "저조"
                },
                "price_momentum": {
                    "change_1d": float,  # %
                    "change_5d": float,
                    "change_20d": float,
                    "trend": str  # "상승세", "보합", "하락세"
                }
            }
        """
        db = SessionLocal()
        try:
            # 최근 60일치 데이터 조회 (MA60 계산용)
            recent_prices = (
                db.query(StockPrice)
                .filter(StockPrice.stock_code == stock_code)
                .order_by(StockPrice.date.desc())
                .limit(60)
                .all()
            )

            if len(recent_prices) < 5:
                logger.warning(f"기술적 지표 계산 불가: {stock_code} - 데이터 부족 ({len(recent_prices)}일)")
                return None

            # 최신 데이터가 먼저 오므로 역순 정렬
            recent_prices.reverse()

            current_price = recent_prices[-1].close
            current_volume = recent_prices[-1].volume or 0

            # 1. 이동평균선 계산
            ma5 = sum(p.close for p in recent_prices[-5:]) / 5 if len(recent_prices) >= 5 else None
            ma20 = sum(p.close for p in recent_prices[-20:]) / 20 if len(recent_prices) >= 20 else None
            ma60 = sum(p.close for p in recent_prices[-60:]) / 60 if len(recent_prices) >= 60 else None

            # 현재가 vs 이동평균 비율
            ma5_diff = ((current_price - ma5) / ma5 * 100) if ma5 else None
            ma20_diff = ((current_price - ma20) / ma20 * 100) if ma20 else None
            ma60_diff = ((current_price - ma60) / ma60 * 100) if ma60 else None

            # 추세 판단 (정배열: 강세, 역배열: 약세)
            ma_trend = "중립"
            if ma5 and ma20 and ma60:
                if ma5 > ma20 > ma60 and current_price > ma5:
                    ma_trend = "강세"
                elif ma5 < ma20 < ma60 and current_price < ma5:
                    ma_trend = "약세"

            # 2. 거래량 분석
            volumes = [p.volume for p in recent_prices[-20:] if p.volume]
            avg_volume_20d = sum(volumes) / len(volumes) if volumes else 0
            volume_ratio = ((current_volume - avg_volume_20d) / avg_volume_20d * 100) if avg_volume_20d > 0 else 0

            volume_trend = "보통"
            if volume_ratio > 50:
                volume_trend = "급증"
            elif volume_ratio < -30:
                volume_trend = "저조"

            # 3. 가격 모멘텀
            change_1d = 0.0
            change_5d = 0.0
            change_20d = 0.0

            if len(recent_prices) >= 2:
                change_1d = ((current_price - recent_prices[-2].close) / recent_prices[-2].close * 100)

            if len(recent_prices) >= 6:
                change_5d = ((current_price - recent_prices[-6].close) / recent_prices[-6].close * 100)

            if len(recent_prices) >= 21:
                change_20d = ((current_price - recent_prices[-21].close) / recent_prices[-21].close * 100)

            # 모멘텀 추세 판단
            momentum_trend = "보합"
            if change_1d > 0 and change_5d > 0 and change_20d > 0:
                momentum_trend = "상승세"
            elif change_1d < 0 and change_5d < 0 and change_20d < 0:
                momentum_trend = "하락세"

            # 4. RSI (14일 기준)
            rsi = None
            rsi_signal = "중립"
            if len(recent_prices) >= 15:
                # RSI 계산: 14일간의 상승/하락 평균
                gains = []
                losses = []
                for i in range(-14, 0):
                    change = recent_prices[i].close - recent_prices[i-1].close
                    if change > 0:
                        gains.append(change)
                        losses.append(0)
                    else:
                        gains.append(0)
                        losses.append(abs(change))

                avg_gain = sum(gains) / 14
                avg_loss = sum(losses) / 14

                if avg_loss == 0:
                    rsi = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                # RSI 신호 판단
                if rsi >= 70:
                    rsi_signal = "과매수"
                elif rsi <= 30:
                    rsi_signal = "과매도"

            # 5. 볼린저 밴드 (20일 기준, 2 표준편차)
            bb_upper = None
            bb_middle = None
            bb_lower = None
            bb_position = "중립"
            if len(recent_prices) >= 20 and ma20:
                # 표준편차 계산
                prices_20d = [p.close for p in recent_prices[-20:]]
                variance = sum((p - ma20) ** 2 for p in prices_20d) / 20
                std_dev = variance ** 0.5

                bb_upper = ma20 + (2 * std_dev)
                bb_middle = ma20
                bb_lower = ma20 - (2 * std_dev)

                # 현재가 위치 판단
                if current_price >= bb_upper:
                    bb_position = "상단돌파"
                elif current_price <= bb_lower:
                    bb_position = "하단돌파"
                elif current_price > bb_middle:
                    bb_position = "상단근접"
                else:
                    bb_position = "하단근접"

            # 6. MACD (12일, 26일, 9일 신호선)
            macd_line = None
            macd_signal = None
            macd_histogram = None
            macd_trend = "중립"
            if len(recent_prices) >= 26:
                # EMA 계산 헬퍼 함수
                def calculate_ema(prices, period):
                    multiplier = 2 / (period + 1)
                    ema = prices[0]
                    for price in prices[1:]:
                        ema = (price - ema) * multiplier + ema
                    return ema

                prices = [p.close for p in recent_prices]

                # 12일 EMA
                ema12 = calculate_ema(prices[-26:], 12)

                # 26일 EMA
                ema26 = calculate_ema(prices[-26:], 26)

                # MACD Line
                macd_line = ema12 - ema26

                # Signal Line (MACD의 9일 EMA)
                if len(recent_prices) >= 35:
                    macd_values = []
                    for i in range(-35, 0):
                        prices_segment = [p.close for p in recent_prices[max(0, i-25):i+1]]
                        if len(prices_segment) >= 26:
                            e12 = calculate_ema(prices_segment[-26:], 12)
                            e26 = calculate_ema(prices_segment[-26:], 26)
                            macd_values.append(e12 - e26)

                    if len(macd_values) >= 9:
                        macd_signal = calculate_ema(macd_values[-9:], 9)
                        macd_histogram = macd_line - macd_signal

                        # MACD 신호 판단
                        if macd_histogram > 0:
                            macd_trend = "매수신호"
                        elif macd_histogram < 0:
                            macd_trend = "매도신호"

            return {
                "moving_averages": {
                    "ma5": round(ma5, 2) if ma5 else None,
                    "ma20": round(ma20, 2) if ma20 else None,
                    "ma60": round(ma60, 2) if ma60 else None,
                    "current_vs_ma5": round(ma5_diff, 2) if ma5_diff else None,
                    "current_vs_ma20": round(ma20_diff, 2) if ma20_diff else None,
                    "current_vs_ma60": round(ma60_diff, 2) if ma60_diff else None,
                    "trend": ma_trend,
                },
                "volume_analysis": {
                    "current_volume": current_volume,
                    "avg_volume_20d": round(avg_volume_20d, 0) if avg_volume_20d else 0,
                    "volume_ratio": round(volume_ratio, 2),
                    "trend": volume_trend,
                },
                "price_momentum": {
                    "change_1d": round(change_1d, 2),
                    "change_5d": round(change_5d, 2),
                    "change_20d": round(change_20d, 2),
                    "trend": momentum_trend,
                },
                "rsi": {
                    "value": round(rsi, 2) if rsi else None,
                    "signal": rsi_signal,
                },
                "bollinger_bands": {
                    "upper": round(bb_upper, 2) if bb_upper else None,
                    "middle": round(bb_middle, 2) if bb_middle else None,
                    "lower": round(bb_lower, 2) if bb_lower else None,
                    "position": bb_position,
                },
                "macd": {
                    "macd_line": round(macd_line, 2) if macd_line else None,
                    "signal_line": round(macd_signal, 2) if macd_signal else None,
                    "histogram": round(macd_histogram, 2) if macd_histogram else None,
                    "trend": macd_trend,
                }
            }

        except Exception as e:
            logger.error(f"기술적 지표 계산 실패 (종목코드: {stock_code}): {e}")
            return None
        finally:
            db.close()

    def _calculate_similar_news_stats(self, similar_news: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        유사 뉴스 패턴 통계를 계산합니다.

        Args:
            similar_news: 유사 뉴스 리스트

        Returns:
            통계 정보 딕셔너리
        """
        if not similar_news:
            return {
                "count": 0,
                "avg_similarity": 0.0,
                "pattern_stats": {"1d": {}, "2d": {}, "3d": {}, "5d": {}, "10d": {}, "20d": {}},
            }

        # 유사도 평균 계산
        similarities = [news.get("similarity", 0) for news in similar_news]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # 각 기간별 변동률 통계 (T+1, T+2, T+3, T+5, T+10, T+20)
        pattern_stats = {}
        for period in ["1d", "2d", "3d", "5d", "10d", "20d"]:
            changes = []
            for news in similar_news:
                price_info = news.get("price_changes", {})
                change = price_info.get(period)
                if change is not None and change != "N/A":
                    try:
                        changes.append(float(change))
                    except (ValueError, TypeError):
                        pass

            if changes:
                pattern_stats[period] = {
                    "avg": round(sum(changes) / len(changes), 2),
                    "max": round(max(changes), 2),
                    "min": round(min(changes), 2),
                    "count": len(changes),
                }
            else:
                pattern_stats[period] = {"avg": None, "max": None, "min": None, "count": 0}

        return {
            "count": len(similar_news),
            "avg_similarity": round(avg_similarity, 4),
            "pattern_stats": pattern_stats,
        }

    def _build_prompt(
        self,
        current_news: Dict[str, Any],
        similar_news: List[Dict[str, Any]],
    ) -> str:
        """
        예측 프롬프트 생성 (개선 버전)

        Args:
            current_news: 현재 뉴스 정보 {title, content, stock_code}
            similar_news: 유사 뉴스 리스트 [{title, content, similarity, price_changes}]

        Returns:
            프롬프트 문자열
        """
        stock_code = current_news.get('stock_code')

        # 1. 종목 기본 정보 조회
        stock_basic = self._get_stock_info(stock_code) if stock_code else None
        stock_name = stock_basic['name'] if stock_basic else "알 수 없음"

        # 2. 유사 뉴스 통계 계산
        similar_stats = self._calculate_similar_news_stats(similar_news)

        # 3. 유사 뉴스 요약
        similar_cases = []
        for i, news in enumerate(similar_news, 1):
            price_info = news.get("price_changes", {})
            similar_cases.append(
                f"""
### 유사 사례 {i} (유사도: {news.get('similarity', 0):.2%})
**제목**: {news.get('news_title', 'N/A')}
**내용**: {news.get('news_content', 'N/A')[:150]}...
**발표일**: {news.get('published_at', 'N/A')}
**주가 변동률**:
- T+1일: {price_info.get('1d', 'N/A')}%, T+2일: {price_info.get('2d', 'N/A')}%
- T+3일: {price_info.get('3d', 'N/A')}%, T+5일: {price_info.get('5d', 'N/A')}%
- T+10일: {price_info.get('10d', 'N/A')}%, T+20일: {price_info.get('20d', 'N/A')}%
"""
            )

        similar_section = "\n".join(similar_cases) if similar_cases else "유사 뉴스 없음"

        # 4. 유사 패턴 통계 섹션
        pattern_stats = similar_stats['pattern_stats']
        stats_section = f"""
## 📊 유사 뉴스 패턴 통계 (총 {similar_stats['count']}건, 평균 유사도: {similar_stats['avg_similarity']:.1%})

"""
        for period, stats in pattern_stats.items():
            if stats.get('count', 0) > 0:
                stats_section += f"""**T+{period.replace('d', '')}일**: 평균 {stats['avg']:+.2f}%, 최대 {stats['max']:+.2f}%, 최소 {stats['min']:+.2f}% (데이터 {stats['count']}건)
"""
            else:
                stats_section += f"""**T+{period.replace('d', '')}일**: 데이터 없음
"""

        # 5. 현재 주가 정보 조회
        stock_price = self._get_current_stock_info(stock_code) if stock_code else None

        # 5-1. 기술적 지표 조회
        technical = self._get_technical_indicators(stock_code) if stock_code else None

        # 6. 현재 주가 정보 섹션
        if stock_price:
            change_indicator = "📈" if stock_price["change_rate"] > 0 else "📉" if stock_price["change_rate"] < 0 else "➡️"
            price_section = f"""
## 현재 주가 정보 ({stock_price['date']})
**현재가**: {stock_price['close']:,.0f}원 ({change_indicator} {stock_price['change_rate']:+.2f}%)
**당일 변동**: 시가 {stock_price['open']:,.0f}원 / 고가 {stock_price['high']:,.0f}원 / 저가 {stock_price['low']:,.0f}원
**거래량**: {stock_price['volume']:,}주

**⚠️ 중요**: 이 주가 정보를 고려하여 예측을 수행하세요.
- 최근 주가 흐름이 상승세라면 긍정적 뉴스의 영향이 더 클 수 있습니다
- 최근 주가가 하락세라면 부정적 뉴스의 영향을 더 신중히 평가하세요
"""
        else:
            price_section = "\n## 현재 주가 정보\n현재 주가 정보 없음\n"

        # 6-1. 기술적 지표 섹션
        if technical:
            ma = technical["moving_averages"]
            vol = technical["volume_analysis"]
            mom = technical["price_momentum"]

            ma_indicator = "📈" if ma["trend"] == "강세" else "📉" if ma["trend"] == "약세" else "➡️"
            vol_indicator = "🔥" if vol["trend"] == "급증" else "❄️" if vol["trend"] == "저조" else "➡️"
            mom_indicator = "🚀" if mom["trend"] == "상승세" else "📉" if mom["trend"] == "하락세" else "➡️"

            technical_section = f"""
## 📈 기술적 지표 분석

### 이동평균선 분석 ({ma_indicator} {ma['trend']})
"""
            if ma["ma5"]:
                technical_section += f"""**MA5 (5일 평균)**: {ma['ma5']:,.0f}원 (현재가 대비 {ma['current_vs_ma5']:+.2f}%)
"""
            if ma["ma20"]:
                technical_section += f"""**MA20 (20일 평균)**: {ma['ma20']:,.0f}원 (현재가 대비 {ma['current_vs_ma20']:+.2f}%)
"""
            if ma["ma60"]:
                technical_section += f"""**MA60 (60일 평균)**: {ma['ma60']:,.0f}원 (현재가 대비 {ma['current_vs_ma60']:+.2f}%)
"""

            # 이동평균 해석
            if ma["trend"] == "강세":
                technical_section += """
**해석**: 단기/중기/장기 이동평균선을 모두 상향 돌파한 강세 정배열 상태입니다.
→ 기술적으로 상승 추세가 견고하며, 긍정적 뉴스의 영향이 증폭될 수 있습니다.
"""
            elif ma["trend"] == "약세":
                technical_section += """
**해석**: 이동평균선 역배열 상태로 기술적 약세 구간입니다.
→ 부정적 뉴스의 영향이 더 클 수 있으며, 긍정적 뉴스도 단기 반등에 그칠 가능성이 있습니다.
"""
            else:
                technical_section += """
**해석**: 이동평균선이 혼재된 중립 구간입니다.
→ 뉴스의 내용에 따라 방향성이 결정될 가능성이 높습니다.
"""

            # 거래량 분석
            technical_section += f"""
### 거래량 분석 ({vol_indicator} {vol['trend']})
**오늘 거래량**: {vol['current_volume']:,}주
**20일 평균 거래량**: {vol['avg_volume_20d']:,.0f}주
**거래량 비율**: {vol['volume_ratio']:+.2f}% (평균 대비)

"""
            if vol["trend"] == "급증":
                technical_section += """**해석**: 거래량이 평균 대비 급증했습니다.
→ 시장 관심도가 높아진 상태로, 뉴스 영향이 증폭될 가능성이 큽니다.
"""
            elif vol["trend"] == "저조":
                technical_section += """**해석**: 거래량이 평균 이하로 저조합니다.
→ 시장 관심도가 낮은 상태로, 뉴스 영향이 제한적일 수 있습니다.
"""
            else:
                technical_section += """**해석**: 거래량이 평균 수준입니다.
→ 정상적인 시장 참여 수준입니다.
"""

            # 가격 모멘텀
            technical_section += f"""
### 가격 모멘텀 ({mom_indicator} {mom['trend']})
**1일 수익률**: {mom['change_1d']:+.2f}%
**5일 수익률**: {mom['change_5d']:+.2f}%
**20일 수익률**: {mom['change_20d']:+.2f}%

"""
            if mom["trend"] == "상승세":
                technical_section += """**해석**: 단기/중기 모두 상승세를 지속하고 있습니다.
→ 긍정적 모멘텀이 형성되어 있어, 호재성 뉴스의 영향이 더 클 것으로 예상됩니다.
"""
            elif mom["trend"] == "하락세":
                technical_section += """**해석**: 단기/중기 모두 하락세입니다.
→ 부정적 모멘텀 상태로, 악재성 뉴스의 타격이 더 클 수 있습니다.
"""
            else:
                technical_section += """**해석**: 단기/중기 방향이 혼재된 보합 상태입니다.
→ 뉴스 내용에 따라 방향이 결정될 것으로 예상됩니다.
"""

            # RSI 분석
            rsi = technical.get("rsi", {})
            if rsi and rsi.get("value") is not None:
                rsi_value = rsi["value"]
                rsi_signal = rsi["signal"]

                rsi_indicator = "🔥" if rsi_signal == "과매수" else "❄️" if rsi_signal == "과매도" else "➡️"

                technical_section += f"""
### RSI 분석 ({rsi_indicator} {rsi_signal})
**RSI (14일)**: {rsi_value:.2f}

"""
                if rsi_signal == "과매수":
                    technical_section += """**해석**: RSI가 70 이상으로 과매수 구간입니다.
→ 단기 조정 가능성이 있으며, 호재성 뉴스에도 상승 여력이 제한적일 수 있습니다.
→ 차익 실현 압력이 높아질 수 있으므로 신중한 접근이 필요합니다.
"""
                elif rsi_signal == "과매도":
                    technical_section += """**해석**: RSI가 30 이하로 과매도 구간입니다.
→ 기술적 반등 가능성이 있으며, 긍정적 뉴스 시 강한 반등이 기대됩니다.
→ 저가 매수 기회로 해석될 수 있어 호재 뉴스의 영향이 증폭될 수 있습니다.
"""
                else:
                    technical_section += """**해석**: RSI가 30~70 사이의 정상 구간입니다.
→ 과매수/과매도 신호가 없어 뉴스 내용에 따라 자연스러운 주가 반응이 예상됩니다.
"""

            # 볼린저 밴드 분석
            bb = technical.get("bollinger_bands", {})
            if bb and bb.get("upper") is not None:
                bb_upper = bb["upper"]
                bb_middle = bb["middle"]
                bb_lower = bb["lower"]
                bb_position = bb["position"]

                bb_indicator = "🔥" if bb_position == "상단 근접" else "❄️" if bb_position == "하단 근접" else "➡️"

                technical_section += f"""
### 볼린저 밴드 분석 ({bb_indicator} {bb_position})
**상단 밴드**: {bb_upper:,.0f}원
**중심선 (MA20)**: {bb_middle:,.0f}원
**하단 밴드**: {bb_lower:,.0f}원

"""
                if bb_position == "상단 근접":
                    technical_section += """**해석**: 주가가 볼린저 밴드 상단에 근접했습니다.
→ 변동성이 커진 상태로 과열 가능성이 있습니다.
→ 긍정적 뉴스에도 상승 제한이 있을 수 있으며, 조정 가능성을 염두에 두세요.
"""
                elif bb_position == "하단 근접":
                    technical_section += """**해석**: 주가가 볼린저 밴드 하단에 근접했습니다.
→ 과도한 하락으로 기술적 반등 가능성이 높습니다.
→ 긍정적 뉴스 시 강한 반등 모멘텀이 형성될 수 있습니다.
"""
                else:
                    technical_section += """**해석**: 주가가 볼린저 밴드 중심 부근에 위치합니다.
→ 정상적인 변동성 범위 내에서 움직이고 있습니다.
→ 뉴스 내용에 따라 밴드 상단 또는 하단으로의 이동이 예상됩니다.
"""

            # MACD 분석
            macd = technical.get("macd", {})
            if macd and macd.get("macd_line") is not None:
                macd_line = macd["macd_line"]
                macd_signal = macd["signal_line"]
                macd_histogram = macd["histogram"]
                macd_trend = macd["trend"]

                macd_indicator = "📈" if macd_trend == "매수" else "📉" if macd_trend == "매도" else "➡️"

                technical_section += f"""
### MACD 분석 ({macd_indicator} {macd_trend} 신호)
**MACD Line**: {macd_line:.2f}
**Signal Line**: {macd_signal:.2f}
**Histogram**: {macd_histogram:.2f}

"""
                if macd_trend == "매수":
                    technical_section += """**해석**: MACD가 시그널선을 상향 돌파한 매수 신호입니다.
→ 상승 모멘텀이 강화되는 구간으로 긍정적 뉴스의 영향이 증폭될 것입니다.
→ 히스토그램이 양수로 전환되며 추세 전환 가능성이 높습니다.
"""
                elif macd_trend == "매도":
                    technical_section += """**해석**: MACD가 시그널선을 하향 돌파한 매도 신호입니다.
→ 하락 모멘텀이 강화되는 구간으로 부정적 뉴스의 타격이 클 것입니다.
→ 히스토그램이 음수로 전환되며 약세 추세가 지속될 가능성이 있습니다.
"""
                else:
                    technical_section += """**해석**: MACD가 시그널선과 근접한 중립 구간입니다.
→ 뚜렷한 방향성이 없는 보합 상태로, 뉴스 내용에 따라 추세가 결정될 것입니다.
"""

            technical_section += """
**⚠️ 고급 기술적 지표 종합 활용 지침**:
- RSI 과매도 + 볼린저 하단 + MACD 매수 신호 → 강력한 반등 가능성, 호재 뉴스 영향 극대화
- RSI 과매수 + 볼린저 상단 + MACD 매도 신호 → 조정 가능성, 악재 뉴스 타격 심화
- 이동평균 정배열 + 거래량 급증 + 상승 모멘텀 + MACD 매수 → 강세장, 긍정 뉴스 최대 효과
- 이동평균 역배열 + 거래량 저조 + 하락 모멘텀 + MACD 매도 → 약세장, 부정 뉴스 최대 타격
- 모든 지표가 중립이면 뉴스 내용 자체의 펀더멘털 분석에 집중하세요
"""
        else:
            technical_section = "\n## 📈 기술적 지표 분석\n기술적 지표 데이터 없음\n"

        # 7. 최근 DART 공시 정보 조회
        disclosures = self._get_recent_disclosures(stock_code, days=7) if stock_code else []

        if disclosures:
            disclosure_section = f"""
## 📢 최근 7일 공시 정보 ({len(disclosures)}건)
"""
            for i, disc in enumerate(disclosures, 1):
                disclosure_section += f"""**{i}. [{disc['published_at']}] {disc['title']}**
내용: {disc['content']}

"""
        else:
            disclosure_section = "\n## 📢 최근 공시 정보\n최근 7일 내 공시 없음\n"

        # 8. 시장 지수 맥락 정보 조회
        market_context = self._get_market_context()
        sector_context = self._get_sector_indices(top_n=3)

        market_section = "\n## 📈 시장 지수 현황\n"
        if market_context.get("kospi"):
            kospi = market_context["kospi"]
            indicator = "📈" if kospi["change_pct"] > 0 else "📉" if kospi["change_pct"] < 0 else "➡️"
            market_section += f"""**KOSPI**: {kospi['close']:,.2f} ({indicator} {kospi['change_pct']:+.2f}%) - {kospi['date']}
"""
        if market_context.get("kosdaq"):
            kosdaq = market_context["kosdaq"]
            indicator = "📈" if kosdaq["change_pct"] > 0 else "📉" if kosdaq["change_pct"] < 0 else "➡️"
            market_section += f"""**KOSDAQ**: {kosdaq['close']:,.2f} ({indicator} {kosdaq['change_pct']:+.2f}%) - {kosdaq['date']}
"""
        if not market_context.get("kospi") and not market_context.get("kosdaq"):
            market_section += "시장 지수 정보 없음\n"

        # 섹터 지수 정보 추가
        if sector_context.get("top_sectors") and len(sector_context["top_sectors"]) > 0:
            market_section += "\n**🔥 강세 섹터** (변동률 상위):\n"
            for sector in sector_context["top_sectors"]:
                indicator = "📈" if sector["change_pct"] > 0 else "📉"
                market_section += f"- {sector['name']}: {indicator} {sector['change_pct']:+.2f}%\n"

        if sector_context.get("bottom_sectors") and len(sector_context["bottom_sectors"]) > 0:
            market_section += "\n**❄️ 약세 섹터** (변동률 하위):\n"
            for sector in sector_context["bottom_sectors"]:
                indicator = "📉" if sector["change_pct"] < 0 else "📈"
                market_section += f"- {sector['name']}: {indicator} {sector['change_pct']:+.2f}%\n"

        market_section += """
**⚠️ 시장 맥락 고려사항**:
- 시장 전체가 상승세라면 개별 종목의 긍정적 뉴스 영향이 증폭될 수 있습니다
- 시장이 하락세라면 부정적 뉴스의 영향이 더 클 수 있습니다
- 해당 종목이 속한 섹터의 흐름도 뉴스 영향력에 영향을 줍니다
"""

        # 9. 최종 프롬프트 생성
        prompt = f"""
당신은 한국 주식 시장의 **뉴스 영향도 분석가**입니다.
뉴스, 공시, 과거 패턴, 현재 주가를 종합적으로 분석하여 뉴스가 기업과 주가에 미치는 영향을 평가하세요.
가격을 예측하는 것이 아니라, 뉴스의 영향력을 분석하는 것이 당신의 역할입니다.

---

## 현재 뉴스
**종목**: {stock_name} ({stock_code})
**제목**: {current_news.get('title', 'N/A')}
**내용**: {current_news.get('content', 'N/A')[:300]}...

---
{price_section}
---
{technical_section}
---
{market_section}
---
{disclosure_section}
---
{stats_section}
---

## 유사한 과거 뉴스와 실제 주가 변동
{similar_section}

---

## 분석 요청사항

당신의 역할은 **뉴스가 기업과 주가에 미치는 영향도를 분석**하는 것입니다.
가격을 직접 예측하지 말고, 뉴스의 영향력을 다각도로 평가하세요.

1. **감성 방향 및 점수**: 뉴스의 전반적인 감성을 평가하세요
   - positive (긍정적 영향), negative (부정적 영향), neutral (중립적)
   - sentiment_score: -1.0 (매우 부정적) ~ +1.0 (매우 긍정적)

2. **영향 수준**: 이 뉴스가 주가에 미칠 영향의 크기를 평가하세요
   - low: 경미한 영향 (일상적 뉴스, 작은 변화)
   - medium: 중간 영향 (사업 일부에 영향)
   - high: 큰 영향 (핵심 사업에 영향, 시장 주목)
   - critical: 매우 큰 영향 (기업 전체에 영향, 게임 체인저)

3. **관련성 점수**: 이 뉴스가 해당 기업의 핵심 사업과 얼마나 관련 있는지 평가하세요
   - relevance_score: 0.0 (무관) ~ 1.0 (핵심 사업 직접 관련)

4. **긴급도**: 시장이 이 뉴스에 얼마나 빠르게 반응할지 평가하세요
   - routine: 일상적 (시장 반응 미미)
   - notable: 주목할 만한 (점진적 반응)
   - urgent: 긴급 (빠른 반응 예상)
   - breaking: 속보 (즉각적 반응 예상)

5. **영향 분석**: 다음 4가지 측면에서 구체적으로 분석하세요
   - business_impact: 사업에 미치는 영향 (매출, 이익, 시장 점유율 등)
   - market_sentiment_impact: 시장 심리에 미치는 영향
   - competitive_impact: 경쟁 구도 변화
   - regulatory_impact: 규제나 정책 환경 변화

**응답 형식** (JSON):
```json
{{
  "sentiment_direction": "positive",
  "sentiment_score": 0.7,
  "impact_level": "high",
  "relevance_score": 0.85,
  "urgency_level": "urgent",
  "reasoning": "영향도 분석 근거 설명 (구체적 수치 포함)",
  "impact_analysis": {{
    "business_impact": "신제품 출시로 향후 6개월 매출 15% 증가 예상. 주력 사업 부문 강화.",
    "market_sentiment_impact": "투자자들의 긍정적 반응 예상. 기관 매수 가능성.",
    "competitive_impact": "경쟁사 대비 기술 우위 확보. 시장 점유율 2-3%p 상승 기대.",
    "regulatory_impact": "규제 변화 없음. 정책적 리스크 낮음."
  }},
  "pattern_analysis": {{
    "avg_1d": 2.5,
    "avg_3d": 5.3,
    "avg_5d": 7.8,
    "max_1d": 4.2,
    "min_1d": 0.8
  }}
}}
```

**중요 지침**:
- **sentiment_score**: 뉴스 내용의 긍정/부정 정도를 -1.0 ~ +1.0 범위로 평가하세요
- **impact_level**: 뉴스가 주가에 미칠 영향의 절대적 크기를 평가하세요
- **relevance_score**: 기업의 핵심 사업과의 관련도를 0.0 ~ 1.0 범위로 평가하세요
- **urgency_level**: 시장의 반응 속도를 평가하세요 (routine < notable < urgent < breaking)
- **impact_analysis**: 각 측면에서 구체적이고 정량적인 분석을 제공하세요
- **pattern_analysis**: 유사 뉴스 통계를 참고용으로 포함하되, 직접적인 가격 예측은 하지 마세요
- **reasoning**: 왜 이러한 영향도 평가를 내렸는지 구체적으로 설명하세요
"""
        return prompt.strip()

    def predict(
        self,
        current_news: Dict[str, Any],
        similar_news: List[Dict[str, Any]],
        news_id: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        뉴스 기반 영향도 분석

        Args:
            current_news: 현재 뉴스 정보
            similar_news: 유사 뉴스 리스트
            news_id: 뉴스 ID (캐싱용, 선택사항)
            use_cache: 캐시 사용 여부 (기본값: True)

        Returns:
            영향도 분석 결과 {
                "sentiment_direction": str,     # positive/negative/neutral
                "sentiment_score": float,       # -1.0 ~ 1.0
                "impact_level": str,            # low/medium/high/critical
                "relevance_score": float,       # 0.0 ~ 1.0
                "urgency_level": str,           # routine/notable/urgent/breaking
                "reasoning": str,               # 분석 근거
                "impact_analysis": dict,        # 영향도 상세 분석
                "pattern_analysis": dict,       # 과거 패턴 분석
                "similar_count": int,           # 참고한 유사 뉴스 개수
                "model": str,                   # 사용 모델
                "timestamp": str,               # 분석 시각
                "cached": bool                  # 캐시에서 조회했는지 여부
            }
        """
        stock_code = current_news.get("stock_code")

        # 1. 캐시 확인
        if use_cache and news_id and stock_code:
            cached_result = self.cache.get(news_id, stock_code)
            if cached_result:
                logger.info(f"캐시된 예측 반환: news_id={news_id}")
                cached_result["cached"] = True
                return cached_result

        # 2. 캐시 미스 → LLM 예측 수행
        try:
            # 1. 프롬프트 생성
            prompt = self._build_prompt(current_news, similar_news)

            logger.info(f"주가 예측 시작: {current_news.get('title', 'N/A')[:50]}...")

            # 2. LLM 호출 (OpenRouter는 JSON mode 미지원)
            if settings.LLM_PROVIDER == "openrouter":
                # OpenRouter: JSON mode 없이 호출, 응답에서 JSON 추출
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다. 반드시 JSON 형식으로만 응답하세요.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
            else:
                # OpenAI: JSON mode 사용
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                    response_format={"type": "json_object"},
                )

            # 3. 응답 파싱
            result_text = response.choices[0].message.content

            # OpenRouter 응답에서 JSON 추출 (```json ... ``` 형식일 수 있음)
            if settings.LLM_PROVIDER == "openrouter" and "```json" in result_text:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)

            result = json.loads(result_text)

            # 4. 결과 보강
            result["similar_count"] = len(similar_news)
            result["model"] = self.model
            result["timestamp"] = datetime.now().isoformat()
            result["cached"] = False

            # 5. 새 필드 검증 및 기본값 설정
            # sentiment_direction 검증
            if "sentiment_direction" in result:
                valid_directions = ["positive", "negative", "neutral"]
                if result["sentiment_direction"] not in valid_directions:
                    logger.warning(f"Invalid sentiment_direction: {result['sentiment_direction']}, defaulting to 'neutral'")
                    result["sentiment_direction"] = "neutral"

            # sentiment_score 검증 (-1.0 ~ 1.0)
            if "sentiment_score" in result:
                score = result["sentiment_score"]
                if not isinstance(score, (int, float)) or score < -1.0 or score > 1.0:
                    logger.warning(f"Invalid sentiment_score: {score}, defaulting to 0.0")
                    result["sentiment_score"] = 0.0

            # impact_level 검증
            if "impact_level" in result:
                valid_levels = ["low", "medium", "high", "critical"]
                if result["impact_level"] not in valid_levels:
                    logger.warning(f"Invalid impact_level: {result['impact_level']}, defaulting to 'medium'")
                    result["impact_level"] = "medium"

            # relevance_score 검증 (0.0 ~ 1.0)
            if "relevance_score" in result:
                score = result["relevance_score"]
                if not isinstance(score, (int, float)) or score < 0.0 or score > 1.0:
                    logger.warning(f"Invalid relevance_score: {score}, defaulting to 0.5")
                    result["relevance_score"] = 0.5

            # urgency_level 검증
            if "urgency_level" in result:
                valid_urgencies = ["routine", "notable", "urgent", "breaking"]
                if result["urgency_level"] not in valid_urgencies:
                    logger.warning(f"Invalid urgency_level: {result['urgency_level']}, defaulting to 'notable'")
                    result["urgency_level"] = "notable"

            # impact_analysis 검증
            if "impact_analysis" not in result or not isinstance(result["impact_analysis"], dict):
                logger.warning("Missing or invalid impact_analysis, setting defaults")
                result["impact_analysis"] = {
                    "business_impact": "분석 필요",
                    "market_sentiment_impact": "분석 필요",
                    "competitive_impact": "분석 필요",
                    "regulatory_impact": "분석 필요"
                }

            # 6. pattern_analysis가 없으면 기본값 추가 (하위 호환성)
            if "pattern_analysis" not in result:
                result["pattern_analysis"] = {
                    "avg_1d": None,
                    "avg_3d": None,
                    "avg_5d": None,
                }

            # 7. 검증 - 새 필드 검증으로 변경
            required_fields = ["sentiment_direction", "sentiment_score", "impact_level",
                             "relevance_score", "urgency_level", "impact_analysis"]
            missing_fields = [f for f in required_fields if f not in result]
            if missing_fields:
                raise ValueError(f"필수 필드 누락: {', '.join(missing_fields)}")

            # 영향도 분석 로깅
            logger.info(
                f"영향도 분석 완료: {result['sentiment_direction']} (점수: {result['sentiment_score']:.2f}) - "
                f"영향도: {result['impact_level']}, 관련성: {result['relevance_score']:.2f}, "
                f"긴급도: {result['urgency_level']}"
            )

            # 6. 캐시 저장
            if use_cache and news_id and stock_code:
                self.cache.set(news_id, stock_code, result)
                logger.info(f"예측 결과 캐시 저장: news_id={news_id}")

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}", exc_info=True)
            return self._get_fallback_prediction("JSON 파싱 오류")

        except Exception as e:
            logger.error(f"주가 예측 실패: {e}", exc_info=True)
            return self._get_fallback_prediction(str(e))

    def _get_fallback_prediction(self, error_msg: str) -> Dict[str, Any]:
        """
        분석 실패 시 폴백 응답

        Args:
            error_msg: 오류 메시지

        Returns:
            기본 분석 결과
        """
        return {
            "sentiment_direction": "neutral",
            "sentiment_score": 0.0,
            "impact_level": "low",
            "relevance_score": 0.0,
            "urgency_level": "routine",
            "reasoning": f"분석 실패: {error_msg}",
            "impact_analysis": {
                "business_impact": "분석 불가",
                "market_sentiment_impact": "분석 불가",
                "competitive_impact": "분석 불가",
                "regulatory_impact": "분석 불가"
            },
            "pattern_analysis": {
                "avg_1d": None,
                "avg_3d": None,
                "avg_5d": None
            },
            "similar_count": 0,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
        }

    def _predict_with_model(
        self,
        client: OpenAI,
        model_name: str,
        provider: str,
        prompt: str,
        similar_count: int,
    ) -> Dict[str, Any]:
        """
        특정 모델로 예측 수행 (내부 헬퍼 메서드)

        Args:
            client: OpenAI 클라이언트
            model_name: 모델 이름
            provider: 프로바이더 (openai/openrouter)
            prompt: 예측 프롬프트
            similar_count: 유사 뉴스 개수

        Returns:
            예측 결과
        """
        try:
            # LLM 호출
            if provider == "openrouter":
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다. 반드시 JSON 형식으로만 응답하세요.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                )
            else:  # openai
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                    response_format={"type": "json_object"},
                )

            # 응답 파싱
            result_text = response.choices[0].message.content

            # OpenRouter 응답에서 JSON 추출
            if provider == "openrouter" and "```json" in result_text:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_text, re.DOTALL)
                if json_match:
                    result_text = json_match.group(1)

            result = json.loads(result_text)

            # 결과 보강
            result["similar_count"] = similar_count
            result["model"] = model_name
            result["provider"] = provider
            result["timestamp"] = datetime.now().isoformat()

            # 하위 호환성 처리
            if "confidence_breakdown" not in result:
                result["confidence_breakdown"] = {
                    "similar_news_quality": result.get("confidence", 0),
                    "pattern_consistency": 0,
                    "disclosure_impact": 0,
                    "explanation": "구 버전 응답"
                }
            if "pattern_analysis" not in result:
                result["pattern_analysis"] = {
                    "avg_1d": None,
                    "avg_3d": None,
                    "avg_5d": None,
                }

            return result

        except Exception as e:
            logger.error(f"모델 {model_name} 예측 실패: {e}")
            return {
                "prediction": "유지",
                "confidence": 0,
                "reasoning": f"예측 실패: {str(e)}",
                "short_term": "예측 불가",
                "medium_term": "예측 불가",
                "long_term": "예측 불가",
                "similar_count": similar_count,
                "model": model_name,
                "provider": provider,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    def dual_predict(
        self,
        current_news: Dict[str, Any],
        similar_news: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        A/B 테스트: 두 모델로 동시 예측

        Args:
            current_news: 현재 뉴스 정보
            similar_news: 유사 뉴스 리스트

        Returns:
            A/B 비교 결과
            {
                "ab_test_enabled": true,
                "model_a": {...},
                "model_b": {...},
                "comparison": {
                    "agreement": bool,
                    "confidence_diff": int,
                    "stronger_model": str
                }
            }
        """
        if not settings.AB_TEST_ENABLED:
            raise ValueError("A/B 테스트가 비활성화되어 있습니다")

        logger.info("🔬 A/B 테스트 예측 시작")

        # 프롬프트 생성 (공통)
        prompt = self._build_prompt(current_news, similar_news)
        similar_count = len(similar_news)

        # Model A 예측
        logger.info(f"  📊 Model A ({self.model_a}) 예측 중...")
        result_a = self._predict_with_model(
            self.client_a,
            self.model_a,
            settings.MODEL_A_PROVIDER,
            prompt,
            similar_count
        )

        # Model B 예측
        logger.info(f"  📊 Model B ({self.model_b}) 예측 중...")
        result_b = self._predict_with_model(
            self.client_b,
            self.model_b,
            settings.MODEL_B_PROVIDER,
            prompt,
            similar_count
        )

        # 비교 분석
        pred_a = result_a.get("prediction", "유지")
        pred_b = result_b.get("prediction", "유지")
        conf_a = result_a.get("confidence", 0)
        conf_b = result_b.get("confidence", 0)

        comparison = {
            "agreement": pred_a == pred_b,
            "confidence_diff": abs(conf_a - conf_b),
            "stronger_model": "model_a" if conf_a > conf_b else "model_b" if conf_b > conf_a else "tie",
            "prediction_match": pred_a == pred_b,
        }

        logger.info(f"  ✅ A/B 테스트 완료 - 일치: {comparison['agreement']}, 신뢰도 차이: {comparison['confidence_diff']}%")

        return {
            "ab_test_enabled": True,
            "model_a": result_a,
            "model_b": result_b,
            "comparison": comparison,
            "timestamp": datetime.now().isoformat(),
        }

    def predict_all_models(
        self,
        current_news: Dict[str, Any],
        similar_news: List[Dict[str, Any]],
        news_id: int,
    ) -> Dict[int, Dict[str, Any]]:
        """
        모든 활성 모델로 예측을 생성하고 DB에 저장합니다.

        Args:
            current_news: 현재 뉴스 정보
            similar_news: 유사 뉴스 리스트
            news_id: 뉴스 ID

        Returns:
            {model_id: prediction_result, ...}
        """
        stock_code = current_news.get("stock_code")
        similar_count = len(similar_news)
        results = {}

        # 프롬프트 생성 (공통)
        prompt = self._build_prompt(current_news, similar_news)

        logger.info(f"🔬 모든 활성 모델로 예측 시작: news_id={news_id}, models={len(self.active_models)}")

        for model_id, model_info in self.active_models.items():
            logger.info(f"  📊 {model_info['name']} 예측 중...")

            # 예측 실행
            prediction = self._predict_with_model(
                model_info["client"],
                model_info["model_identifier"],
                model_info["provider"],
                prompt,
                similar_count
            )

            # 결과에 model_id 추가
            prediction["model_id"] = model_id
            prediction["model"] = model_info["name"]

            # DB 저장
            self._save_model_prediction(news_id, model_id, stock_code, prediction)

            results[model_id] = prediction

        logger.info(f"✅ 모든 모델 예측 완료: {len(results)}개")
        return results

    def get_ab_predictions(self, news_id: int) -> Dict[str, Any]:
        """
        현재 A/B 설정에 따라 두 모델의 예측을 조회합니다.

        Args:
            news_id: 뉴스 ID

        Returns:
            {
                "model_a": {...},
                "model_b": {...},
                "comparison": {...}
            }
        """
        # 활성 A/B 설정 조회
        ab_config = self._get_active_ab_config()
        if not ab_config:
            logger.warning("활성 A/B 설정 없음")
            return {
                "error": "활성 A/B 설정이 없습니다",
                "model_a": None,
                "model_b": None,
            }

        # 두 모델의 예측 조회
        pred_a = self._get_prediction_from_db(news_id, ab_config.model_a_id)
        pred_b = self._get_prediction_from_db(news_id, ab_config.model_b_id)

        if not pred_a or not pred_b:
            logger.warning(f"예측 결과 없음: model_a={pred_a is not None}, model_b={pred_b is not None}")
            return {
                "error": "예측 결과가 없습니다. 먼저 predict_all_models()를 실행하세요.",
                "model_a": pred_a,
                "model_b": pred_b,
            }

        # 비교 분석
        comparison = {
            "agreement": pred_a.get("prediction") == pred_b.get("prediction"),
            "confidence_diff": abs(pred_a.get("confidence", 0) - pred_b.get("confidence", 0)),
            "stronger_model": "model_a" if pred_a.get("confidence", 0) > pred_b.get("confidence", 0) else "model_b",
            "prediction_match": pred_a.get("prediction") == pred_b.get("prediction"),
        }

        return {
            "ab_test_enabled": True,  # 텔레그램 알림 호환성
            "model_a": pred_a,
            "model_b": pred_b,
            "comparison": comparison,
            "timestamp": datetime.now().isoformat(),
        }


# 싱글톤 인스턴스
_predictor: Optional[StockPredictor] = None


def get_predictor() -> StockPredictor:
    """
    StockPredictor 싱글톤 인스턴스를 반환합니다.

    Returns:
        StockPredictor 인스턴스
    """
    global _predictor
    if _predictor is None:
        _predictor = StockPredictor()
    return _predictor
