"""
LLM 기반 종합 투자 리포트 생성 모듈

종목별 AI 예측 결과를 종합하여 투자 전문가 수준의 리포트를 생성합니다.
"""
import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI

from backend.config import settings
from backend.db.models.prediction import Prediction
from backend.db.models.stock import StockPrice
from backend.utils.stock_mapping import get_stock_mapper
from backend.db.session import SessionLocal
from backend.db.models.market_data import (
    StockOrderbook,
    StockCurrentPrice,
    InvestorTrading,
    StockInfo,
)


logger = logging.getLogger(__name__)


class InvestmentReportGenerator:
    """LLM 기반 투자 리포트 생성기"""

    def __init__(self):
        """초기화"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # 비용 효율적인 모델
        self.stock_mapper = get_stock_mapper()

        # A/B 테스트를 위한 추가 클라이언트
        if settings.AB_TEST_ENABLED:
            # DB에서 A/B 테스트 설정 가져오기
            from backend.db.models.ab_test_config import ABTestConfig
            from backend.db.models.model import Model

            db = SessionLocal()
            try:
                ab_config = db.query(ABTestConfig).filter(
                    ABTestConfig.is_active == True
                ).first()

                if ab_config:
                    # Model A/B 정보 가져오기
                    model_a = db.query(Model).filter(Model.id == ab_config.model_a_id).first()
                    model_b = db.query(Model).filter(Model.id == ab_config.model_b_id).first()

                    if model_a and model_b:
                        self.client_a = self._create_client(model_a.provider)
                        self.model_a = model_a.model_identifier
                        self.client_b = self._create_client(model_b.provider)
                        self.model_b = model_b.model_identifier
                        logger.info(f"A/B 테스트 활성화 (종합 리포트): Model A={model_a.name} ({self.model_a}), Model B={model_b.name} ({self.model_b})")
                    else:
                        # Fallback to config
                        self.client_a = self._create_client(settings.MODEL_A_PROVIDER)
                        self.model_a = settings.MODEL_A_NAME
                        self.client_b = self._create_client(settings.MODEL_B_PROVIDER)
                        self.model_b = settings.MODEL_B_NAME
                        logger.warning(f"⚠️ DB 모델 정보 없음, config 사용: Model A={self.model_a}, Model B={self.model_b}")
                else:
                    # Fallback to config
                    self.client_a = self._create_client(settings.MODEL_A_PROVIDER)
                    self.model_a = settings.MODEL_A_NAME
                    self.client_b = self._create_client(settings.MODEL_B_PROVIDER)
                    self.model_b = settings.MODEL_B_NAME
                    logger.warning(f"⚠️ 활성 A/B 테스트 설정 없음, config 사용: Model A={self.model_a}, Model B={self.model_b}")
            finally:
                db.close()

    def _create_client(self, provider: str) -> OpenAI:
        """프로바이더별 OpenAI 클라이언트 생성"""
        if provider == "openrouter":
            return OpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://craveny.ai",
                    "X-Title": "Craveny Investment Report",
                }
            )
        else:  # openai
            return OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_report(
        self,
        stock_code: str,
        predictions: List[Prediction],
        current_price: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        종합 투자 리포트 생성

        Args:
            stock_code: 종목 코드
            predictions: 최근 예측 리스트 (최대 20건)
            current_price: 현재 주가 정보

        Returns:
            {
                "overall_summary": str,
                "short_term_scenario": str,
                "medium_term_scenario": str,
                "long_term_scenario": str,
                "risk_factors": List[str],
                "opportunity_factors": List[str],
                "recommendation": str,
            }
        """
        if not predictions:
            return self._empty_report()

        try:
            # 1. 데이터 준비
            report_data = self._prepare_report_data(
                stock_code, predictions, current_price
            )

            # 2. LLM 프롬프트 생성
            prompt = self._build_prompt(report_data)

            logger.info(f"투자 리포트 생성 시작: {stock_code} ({len(predictions)}건 분석)")

            # 3. LLM 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식 시장의 베테랑 애널리스트입니다. 데이터 기반으로 명확하고 실용적인 투자 리포트를 작성합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,  # 적당한 창의성
                max_tokens=1000,
                response_format={"type": "json_object"},  # JSON 응답 강제
            )

            # 4. 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info(
                f"투자 리포트 생성 완료: {stock_code} "
                f"(추천: {result.get('recommendation', 'N/A')[:30]}...)"
            )

            return result

        except Exception as e:
            logger.error(f"투자 리포트 생성 실패: {e}", exc_info=True)
            return self._empty_report()

    def _get_kis_market_data(self, stock_code: str) -> Dict[str, Any]:
        """한국투자증권 API 시장 데이터 조회"""
        db = SessionLocal()
        try:
            kis_data = {}

            # 1. 호가 데이터 (최신)
            orderbook = db.query(StockOrderbook).filter(
                StockOrderbook.stock_code == stock_code
            ).order_by(StockOrderbook.datetime.desc()).first()

            if orderbook:
                kis_data["orderbook"] = {
                    "ask_total": orderbook.total_askp_rsqn,  # 총 매도 잔량
                    "bid_total": orderbook.total_bidp_rsqn,  # 총 매수 잔량
                    "ask1": orderbook.askp1,  # 매도 1호가
                    "bid1": orderbook.bidp1,  # 매수 1호가
                    "ask1_qty": orderbook.askp_rsqn1,  # 매도 1호가 잔량
                    "bid1_qty": orderbook.bidp_rsqn1,  # 매수 1호가 잔량
                    "spread": orderbook.askp1 - orderbook.bidp1 if orderbook.askp1 and orderbook.bidp1 else 0,  # 호가 스프레드
                    "datetime": orderbook.datetime.strftime("%Y-%m-%d %H:%M:%S") if orderbook.datetime else None,
                }

            # 2. 현재가 데이터 (최신)
            current = db.query(StockCurrentPrice).filter(
                StockCurrentPrice.stock_code == stock_code
            ).order_by(StockCurrentPrice.datetime.desc()).first()

            if current:
                kis_data["current_price"] = {
                    "price": current.stck_prpr,
                    "change": current.prdy_vrss,
                    "change_rate": current.prdy_ctrt,
                    "volume": current.acml_vol,
                    "trade_value": current.acml_tr_pbmn,
                    "open": None,  # 현재가 API에서는 시가/고가/저가 없음
                    "high": None,
                    "low": None,
                    "market_cap": current.hts_avls,
                    "per": current.per,
                    "pbr": current.pbr,
                    "eps": current.eps,
                    "bps": current.bps,
                    "datetime": current.datetime.strftime("%Y-%m-%d %H:%M:%S") if current.datetime else None,
                }

            # 3. 투자자별 매매동향 (최근 5일)
            investor_data = db.query(InvestorTrading).filter(
                InvestorTrading.stock_code == stock_code
            ).order_by(InvestorTrading.date.desc()).limit(5).all()

            if investor_data:
                kis_data["investor_trading"] = []
                for inv in investor_data:
                    kis_data["investor_trading"].append({
                        "date": inv.date.strftime("%Y-%m-%d") if inv.date else None,
                        "foreign_net_buy": inv.frgn_ntby_qty,  # 외국인 순매수
                        "institution_net_buy": inv.orgn_ntby_qty,  # 기관 순매수
                        "individual_net_buy": inv.prsn_ntby_qty,  # 개인 순매수
                        "close_price": inv.stck_clpr,
                    })

            # 4. 종목 기본정보
            stock_info = db.query(StockInfo).filter(
                StockInfo.stock_code == stock_code
            ).order_by(StockInfo.updated_at.desc()).first()

            if stock_info:
                kis_data["stock_info"] = {
                    "industry": stock_info.std_idst_clsf_cd_name,  # 업종명
                    "market_cap": stock_info.hts_avls,  # 시가총액
                    "listed_shares": stock_info.lstn_stcn,  # 상장주식수
                    "capital": stock_info.cpfn,  # 자본금
                }

            return kis_data

        except Exception as e:
            logger.error(f"KIS 시장 데이터 조회 실패 ({stock_code}): {e}")
            return {}
        finally:
            db.close()

    def _prepare_report_data(
        self,
        stock_code: str,
        predictions: List[Prediction],
        current_price: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """리포트 생성을 위한 데이터 준비"""
        stock_name = self.stock_mapper.get_company_name(stock_code) or stock_code

        # 통계 계산 - 새로운 영향도 분석 필드 사용
        total = len(predictions)

        # 감성 방향 분포
        positive_count = sum(1 for p in predictions if p.sentiment_direction == "positive")
        negative_count = sum(1 for p in predictions if p.sentiment_direction == "negative")
        neutral_count = sum(1 for p in predictions if p.sentiment_direction == "neutral")

        # 영향도 레벨 분포
        high_impact = sum(1 for p in predictions if p.impact_level == "high" or p.impact_level == "critical")
        medium_impact = sum(1 for p in predictions if p.impact_level == "medium")
        low_impact = sum(1 for p in predictions if p.impact_level == "low")

        # 평균 감성 점수 및 관련성 점수
        sentiment_scores = [p.sentiment_score for p in predictions if p.sentiment_score is not None]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

        relevance_scores = [p.relevance_score for p in predictions if p.relevance_score is not None]
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0

        # 신뢰도 breakdown 평균
        breakdown_avg = {"similar_news_quality": None, "pattern_consistency": None, "disclosure_impact": None}
        breakdown_counts = {"similar_news_quality": 0, "pattern_consistency": 0, "disclosure_impact": 0}
        breakdown_sums = {"similar_news_quality": 0.0, "pattern_consistency": 0.0, "disclosure_impact": 0.0}

        for pred in predictions:
            if pred.confidence_breakdown:
                for key in ["similar_news_quality", "pattern_consistency", "disclosure_impact"]:
                    val = pred.confidence_breakdown.get(key)
                    if val is not None:
                        breakdown_sums[key] += val
                        breakdown_counts[key] += 1

        for key in ["similar_news_quality", "pattern_consistency", "disclosure_impact"]:
            if breakdown_counts[key] > 0:
                breakdown_avg[key] = round(breakdown_sums[key] / breakdown_counts[key], 1)

        # 패턴 분석 평균
        pattern_avg = {"avg_1d": None, "avg_3d": None, "avg_5d": None, "avg_10d": None, "avg_20d": None}
        pattern_counts = {"avg_1d": 0, "avg_3d": 0, "avg_5d": 0, "avg_10d": 0, "avg_20d": 0}
        pattern_sums = {"avg_1d": 0.0, "avg_3d": 0.0, "avg_5d": 0.0, "avg_10d": 0.0, "avg_20d": 0.0}

        for pred in predictions:
            if pred.pattern_analysis:
                for key in ["avg_1d", "avg_3d", "avg_5d", "avg_10d", "avg_20d"]:
                    val = pred.pattern_analysis.get(key)
                    if val is not None and val != 0.0:
                        pattern_sums[key] += val
                        pattern_counts[key] += 1

        for key in ["avg_1d", "avg_3d", "avg_5d", "avg_10d", "avg_20d"]:
            if pattern_counts[key] > 0:
                pattern_avg[key] = round(pattern_sums[key] / pattern_counts[key], 2)

        # 최근 뉴스 영향도 분석 (최대 5건)
        recent_news_analysis = []
        for pred in predictions[:5]:
            recent_news_analysis.append({
                "created_at": pred.created_at.strftime("%Y-%m-%d") if pred.created_at else "N/A",
                "sentiment_direction": pred.sentiment_direction or "neutral",
                "sentiment_score": round(pred.sentiment_score, 2) if pred.sentiment_score is not None else 0.0,
                "impact_level": pred.impact_level or "low",
                "relevance_score": round(pred.relevance_score, 2) if pred.relevance_score is not None else 0.0,
                "urgency_level": pred.urgency_level or "routine",
                "reasoning": pred.reasoning[:200] if pred.reasoning else "분석 내용 없음",
                "impact_analysis": pred.impact_analysis if pred.impact_analysis else {},
            })

        # 현재 기술적 지표 계산
        from backend.llm.predictor import StockPredictor
        predictor = StockPredictor()
        technical_indicators = predictor._get_technical_indicators(stock_code)

        # KIS API 시장 데이터 조회
        kis_market_data = self._get_kis_market_data(stock_code)

        return {
            "stock_info": {
                "code": stock_code,
                "name": stock_name,
                "current_price": current_price.get("close") if current_price else None,
                "change_rate": current_price.get("change_rate") if current_price else None,
            },
            "statistical_summary": {
                "total_predictions": total,
                "sentiment_distribution": {
                    "positive": positive_count,
                    "negative": negative_count,
                    "neutral": neutral_count,
                },
                "impact_distribution": {
                    "high": high_impact,
                    "medium": medium_impact,
                    "low": low_impact,
                },
                "avg_sentiment_score": round(avg_sentiment, 2),
                "avg_relevance_score": round(avg_relevance, 2),
                "confidence_breakdown_avg": breakdown_avg,  # 레거시 호환성 유지
                "pattern_analysis_avg": pattern_avg,
            },
            "recent_news_analysis": recent_news_analysis,
            "technical_indicators": technical_indicators,  # 현재 기술적 지표 추가
            "kis_market_data": kis_market_data,  # 한국투자증권 API 시장 데이터 추가
            "time_context": {
                "today": datetime.now().strftime("%Y-%m-%d"),
                "analysis_period": "최근 30일",
                "latest_analysis_date": predictions[0].created_at.strftime("%Y-%m-%d") if predictions[0].created_at else "N/A",
            },
        }

    def _format_kis_market_data(self, kis_data: Dict[str, Any]) -> str:
        """KIS 시장 데이터 포맷팅"""
        if not kis_data:
            return ""

        sections = []

        # 1. 호가 데이터
        orderbook = kis_data.get("orderbook")
        if orderbook:
            bid_pressure = orderbook.get("bid_total", 0) / (orderbook.get("bid_total", 0) + orderbook.get("ask_total", 1)) * 100 if (orderbook.get("bid_total", 0) + orderbook.get("ask_total", 1)) > 0 else 50
            sections.append(f"""### 실시간 호가 분석 ({orderbook.get("datetime", "N/A")})
- 매수 우위도: {bid_pressure:.1f}% (매수잔량 / 전체잔량)
- 총 매수 잔량: {orderbook.get("bid_total", 0):,}주
- 총 매도 잔량: {orderbook.get("ask_total", 0):,}주
- 매수 1호가: {orderbook.get("bid1", 0):,}원 ({orderbook.get("bid1_qty", 0):,}주)
- 매도 1호가: {orderbook.get("ask1", 0):,}원 ({orderbook.get("ask1_qty", 0):,}주)
- 호가 스프레드: {orderbook.get("spread", 0):,}원
- **해석**: {"매수세 우위 - 상승 압력" if bid_pressure > 55 else "매도세 우위 - 하락 압력" if bid_pressure < 45 else "중립 - 관망세"}""")

        # 2. 현재가 상세 정보
        current = kis_data.get("current_price")
        if current:
            price = current.get("price") or 0
            change_rate = current.get("change_rate") or 0
            volume = current.get("volume") or 0
            trade_value = current.get("trade_value") or 0
            market_cap = current.get("market_cap") or 0
            per = current.get("per") or 0
            pbr = current.get("pbr") or 0
            eps = current.get("eps") or 0
            bps = current.get("bps") or 0

            sections.append(f"""### 실시간 시세 ({current.get("datetime", "N/A")})
- 현재가: {price:,}원 ({change_rate:+.2f}%)
- 거래량: {volume:,}주 | 거래대금: {trade_value:,}원
- 시가총액: {market_cap:,}원
- PER: {per:.2f} | PBR: {pbr:.2f}
- EPS: {eps:,}원 | BPS: {bps:,}원""")

        # 3. 투자자별 매매동향
        investor_trading = kis_data.get("investor_trading")
        if investor_trading and len(investor_trading) > 0:
            # 최근 5일 순매수 합계
            foreign_total = sum(inv.get("foreign_net_buy", 0) or 0 for inv in investor_trading)
            institution_total = sum(inv.get("institution_net_buy", 0) or 0 for inv in investor_trading)
            individual_total = sum(inv.get("individual_net_buy", 0) or 0 for inv in investor_trading)

            trend_lines = [f"최근 5일 누적 순매수량:"]
            trend_lines.append(f"- 외국인: {foreign_total:+,}주 {'(매수)' if foreign_total > 0 else '(매도)' if foreign_total < 0 else '(중립)'}")
            trend_lines.append(f"- 기관: {institution_total:+,}주 {'(매수)' if institution_total > 0 else '(매도)' if institution_total < 0 else '(중립)'}")
            trend_lines.append(f"- 개인: {individual_total:+,}주 {'(매수)' if individual_total > 0 else '(매도)' if individual_total < 0 else '(중립)'}")

            trend_lines.append("\n일별 상세:")
            for inv in investor_trading[:3]:  # 최근 3일만 표시
                trend_lines.append(
                    f"- {inv.get('date', 'N/A')}: "
                    f"외국인 {inv.get('foreign_net_buy', 0):+,}주 | "
                    f"기관 {inv.get('institution_net_buy', 0):+,}주 | "
                    f"개인 {inv.get('individual_net_buy', 0):+,}주"
                )

            # 투자자 동향 해석
            main_buyer = "외국인" if abs(foreign_total) >= max(abs(institution_total), abs(individual_total)) else "기관" if abs(institution_total) >= abs(individual_total) else "개인"
            main_action = "매수" if max(foreign_total, institution_total, individual_total) > 0 else "매도"

            trend_lines.append(f"\n**해석**: {main_buyer}이 주도적으로 {main_action} 중")

            sections.append(f"""### 투자자별 매매동향 (최근 5일)\n{chr(10).join(trend_lines)}""")

        # 4. 종목 기본정보
        stock_info = kis_data.get("stock_info")
        if stock_info:
            market_cap = stock_info.get("market_cap") or 0
            listed_shares = stock_info.get("listed_shares") or 0
            capital = stock_info.get("capital") or 0

            sections.append(f"""### 종목 기본정보
- 업종: {stock_info.get("industry") or "N/A"}
- 시가총액: {market_cap:,}원
- 상장주식수: {listed_shares:,}주
- 자본금: {capital:,}원""")

        return "\n\n".join(sections)

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """LLM 프롬프트 생성"""
        stock_info = data["stock_info"]
        stats = data["statistical_summary"]
        recent_news = data["recent_news_analysis"]
        time_ctx = data["time_context"]
        technical = data.get("technical_indicators")
        kis_data = data.get("kis_market_data", {})

        prompt = f"""
당신은 {stock_info['name']}({stock_info['code']})에 대한 **데일리 투자 리포트**를 작성합니다.

## 현재 상황 ({time_ctx['today']})
- 현재가: {stock_info['current_price']:,}원 (전일 대비 {stock_info['change_rate']:+.2f}%) {f"" if stock_info['current_price'] else "현재가 정보 없음"}
- 분석 기간: {time_ctx['analysis_period']}
- 분석된 뉴스: 총 {stats['total_predictions']}건

## 📊 한국투자증권 실시간 시장 데이터
{self._format_kis_market_data(kis_data) if kis_data else "실시간 시장 데이터 없음"}

## 뉴스 영향도 분석 요약
- 감성 분포: 긍정 {stats['sentiment_distribution']['positive']}건, 부정 {stats['sentiment_distribution']['negative']}건, 중립 {stats['sentiment_distribution']['neutral']}건
- 영향도 분포: 높음 {stats['impact_distribution']['high']}건, 중간 {stats['impact_distribution']['medium']}건, 낮음 {stats['impact_distribution']['low']}건
- 평균 감성 점수: {stats['avg_sentiment_score']:.2f} (범위: -1.0 ~ 1.0, 양수=긍정)
- 평균 관련성: {stats['avg_relevance_score']:.2f} (범위: 0.0 ~ 1.0)

## 과거 패턴 분석 (유사 뉴스 기반 평균 변동률)
- T+1일: {f"{stats['pattern_analysis_avg']['avg_1d']:+.1f}%" if stats['pattern_analysis_avg']['avg_1d'] is not None else 'N/A'}
- T+3일: {f"{stats['pattern_analysis_avg']['avg_3d']:+.1f}%" if stats['pattern_analysis_avg']['avg_3d'] is not None else 'N/A'}
- T+5일: {f"{stats['pattern_analysis_avg']['avg_5d']:+.1f}%" if stats['pattern_analysis_avg']['avg_5d'] is not None else 'N/A'}
- T+10일: {f"{stats['pattern_analysis_avg']['avg_10d']:+.1f}%" if stats['pattern_analysis_avg']['avg_10d'] is not None else 'N/A'}
- T+20일: {f"{stats['pattern_analysis_avg']['avg_20d']:+.1f}%" if stats['pattern_analysis_avg']['avg_20d'] is not None else 'N/A'}

{self._format_technical_indicators(technical) if technical else ""}

## 최근 주요 AI 분석 ({len(recent_news)}건)
{self._format_recent_news(recent_news)}

---

위 정보를 바탕으로 **투자자 관점**에서 다음 형식의 JSON으로 응답하세요:

```json
{{
  "overall_summary": "현재 시점에서 이 종목에 대한 전체적인 판단 (2-3문장, 핵심만)",
  "short_term_scenario": "단기 투자자(1일~1주) 관점: 구체적 목표가와 손절가, 진입/청산 전략",
  "medium_term_scenario": "중기 투자자(1주~1개월) 관점: 구체적 목표가와 전략, 예상 수익률",
  "long_term_scenario": "장기 투자자(1개월 이상) 관점: 목표가와 보유 전략, 분할 매수/매도 계획",
  "risk_factors": ["리스크 요인 1 (구체적)", "리스크 요인 2", "리스크 요인 3"],
  "opportunity_factors": ["기회 요인 1 (구체적)", "기회 요인 2", "기회 요인 3"],
  "recommendation": "최종 추천: 명확한 액션(매수/관망/매도) + 간결한 이유 (1-2문장)",
  "price_targets": {{
    "base_price": {stock_info['current_price']},
    "short_term_target": 숫자만 (목표가),
    "short_term_support": 숫자만 (손절가),
    "medium_term_target": 숫자만 (목표가),
    "medium_term_support": 숫자만 (손절가),
    "long_term_target": 숫자만 (목표가)
  }}
}}
```

**중요 지침**:
1. **한국투자증권 실시간 데이터 우선 활용**: 호가, 투자자 매매동향, PER/PBR 등 실제 시장 데이터를 최우선으로 분석
2. **뉴스 영향도를 가격 예측에 반영**: 긍정 뉴스 많으면 상승, 부정 뉴스 많으면 하락 예상
3. **기술적 지표와 결합**: 단순히 뉴스만이 아닌, 기술적 분석도 함께 고려
4. **투자자 동향 반영**: 외국인/기관/개인의 매매 패턴을 투자 전략에 반영
5. **호가 압력 분석**: 매수/매도 잔량 비율로 단기 방향성 예측
6. 구체적인 **수치와 기간**을 명시 (목표가, 손절가, 예상 수익률)
7. 투자자가 **오늘 결정**을 내릴 수 있도록 작성
8. 리스크와 기회는 각각 **최대 3개**까지만
9. **간결하고 명확**하게 (불필요한 수식어 제거)
"""
        return prompt.strip()

    def _format_recent_news(self, recent_news: List[Dict[str, Any]]) -> str:
        """최근 뉴스 영향도 분석 포맷팅"""
        lines = []
        for i, news in enumerate(recent_news, 1):
            sentiment_kr = {"positive": "긍정", "negative": "부정", "neutral": "중립"}.get(news["sentiment_direction"], news["sentiment_direction"])
            impact_kr = {"high": "높음", "critical": "매우 높음", "medium": "중간", "low": "낮음"}.get(news["impact_level"], news["impact_level"])
            urgency_kr = {"urgent": "긴급", "breaking": "속보", "notable": "주목", "routine": "일반"}.get(news["urgency_level"], news["urgency_level"])

            # 영향도 분석 요약
            impact_summary = news.get("impact_analysis", {})
            business_impact = impact_summary.get("business_impact", "")[:100] if impact_summary else ""

            lines.append(
                f"### {i}. {news['created_at']} - {sentiment_kr} 감성 (영향도: {impact_kr}, 긴급도: {urgency_kr})\n"
                f"- 감성 점수: {news['sentiment_score']:.2f} (범위: -1.0 ~ 1.0)\n"
                f"- 관련성: {news['relevance_score']:.2f}\n"
                f"- AI 분석: {news['reasoning']}\n"
                f"{f'- 비즈니스 영향: {business_impact}...' if business_impact else ''}"
            )
        return "\n\n".join(lines)

    def _format_technical_indicators(self, technical: Dict[str, Any]) -> str:
        """기술적 지표 포맷팅"""
        if not technical:
            return ""

        sections = []

        # 이동평균선 분석
        ma = technical.get("moving_averages")
        if ma:
            ma_trend = ma.get("trend", "중립")
            # None-safe value extraction with defaults
            ma5 = ma.get('ma5') or 0
            ma20 = ma.get('ma20') or 0
            ma60 = ma.get('ma60') or 0
            vs_ma5 = ma.get('current_vs_ma5') or 0
            vs_ma20 = ma.get('current_vs_ma20') or 0
            vs_ma60 = ma.get('current_vs_ma60') or 0

            sections.append(f"""## 📈 현재 기술적 지표 분석

### 이동평균선 ({ma_trend})
- MA5: {ma5:,.0f}원 (현재가 대비 {vs_ma5:+.1f}%)
- MA20: {ma20:,.0f}원 (현재가 대비 {vs_ma20:+.1f}%)
- MA60: {ma60:,.0f}원 (현재가 대비 {vs_ma60:+.1f}%)""")

        # 거래량 분석
        vol = technical.get("volume_analysis")
        if vol:
            vol_trend = vol.get("trend", "중립")
            # None-safe value extraction with defaults
            current_vol = vol.get('current_volume') or 0
            avg_vol = vol.get('avg_volume_20d') or 0
            vol_ratio = vol.get('volume_ratio') or 0

            sections.append(f"""### 거래량 분석 ({vol_trend})
- 오늘 거래량: {current_vol:,}주
- 20일 평균: {avg_vol:,.0f}주
- 거래량 비율: {vol_ratio:+.1f}%""")

        # RSI 분석
        rsi = technical.get("rsi")
        if rsi and rsi.get("value") is not None:
            rsi_signal = rsi.get("signal", "중립")
            rsi_emoji = "🔥" if rsi_signal == "과매수" else "❄️" if rsi_signal == "과매도" else "➡️"
            rsi_value = rsi.get('value') or 50  # None-safe with default
            sections.append(f"""### RSI 분석 ({rsi_emoji} {rsi_signal})
- RSI (14일): {rsi_value:.1f}
- 해석: {self._get_rsi_interpretation(rsi_value)}""")

        # 볼린저 밴드 분석
        bb = technical.get("bollinger_bands")
        if bb:
            bb_signal = bb.get("signal", "중립")
            sections.append(f"""### 볼린저 밴드 ({bb_signal})
- 상단: {bb.get('upper', 0):,.0f}원
- 중간 (MA20): {bb.get('middle', 0):,.0f}원
- 하단: {bb.get('lower', 0):,.0f}원
- %B: {bb.get('percent_b', 0):.2f} (0=하단, 0.5=중간, 1=상단)""")

        # MACD 분석
        macd = technical.get("macd")
        if macd:
            macd_signal = macd.get("signal_type", "중립")
            macd_emoji = "📈" if macd_signal == "상승" else "📉" if macd_signal == "하락" else "➡️"
            sections.append(f"""### MACD 분석 ({macd_emoji} {macd_signal})
- MACD: {macd.get('macd_line', 0):.2f}
- Signal: {macd.get('signal_line', 0):.2f}
- Histogram: {macd.get('histogram', 0):.2f}""")

        # 가격 모멘텀
        momentum = technical.get("price_momentum")
        if momentum:
            momentum_trend = momentum.get("trend", "중립")
            sections.append(f"""### 가격 모멘텀 ({momentum_trend})
- 1일 수익률: {momentum.get('change_1d', 0):+.2f}%
- 5일 수익률: {momentum.get('change_5d', 0):+.2f}%
- 20일 수익률: {momentum.get('change_20d', 0):+.2f}%""")

        return "\n\n".join(sections)

    def _get_rsi_interpretation(self, rsi_value: float) -> str:
        """RSI 값 해석"""
        if rsi_value >= 70:
            return "과매수 구간 - 단기 조정 가능성"
        elif rsi_value <= 30:
            return "과매도 구간 - 반등 가능성"
        else:
            return "중립 구간"

    def dual_generate_report(
        self,
        stock_code: str,
        predictions: List[Prediction],
        current_price: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        A/B 테스트: 두 모델로 종합 투자 리포트 생성

        Args:
            stock_code: 종목 코드
            predictions: 최근 예측 리스트
            current_price: 현재 주가 정보

        Returns:
            {
                "ab_test_enabled": true,
                "model_a": {...},
                "model_b": {...},
                "comparison": {...}
            }
        """
        if not settings.AB_TEST_ENABLED:
            raise ValueError("A/B 테스트가 비활성화되어 있습니다")

        if not predictions:
            return {
                "ab_test_enabled": True,
                "model_a": self._empty_report(),
                "model_b": self._empty_report(),
                "comparison": {
                    "recommendation_match": False,
                    "risk_overlap": [],
                    "opportunity_overlap": [],
                }
            }

        try:
            # 공통 데이터 준비
            report_data = self._prepare_report_data(stock_code, predictions, current_price)
            prompt = self._build_prompt(report_data)

            logger.info(f"A/B 종합 리포트 생성: {stock_code} ({len(predictions)}건 분석)")

            # Model A (GPT-4o) 호출
            response_a = self.client_a.chat.completions.create(
                model=self.model_a,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식 시장의 베테랑 애널리스트입니다. 데이터 기반으로 명확하고 실용적인 투자 리포트를 작성합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"},
            )

            result_a = json.loads(response_a.choices[0].message.content)
            result_a["model"] = self.model_a
            result_a["provider"] = settings.MODEL_A_PROVIDER

            # Model B (DeepSeek) 호출
            response_b = self.client_b.chat.completions.create(
                model=self.model_b,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식 시장의 베테랑 애널리스트입니다. 데이터 기반으로 명확하고 실용적인 투자 리포트를 작성합니다. 반드시 유효한 JSON 형식으로만 응답하세요. 추가 설명이나 마크다운 없이 순수 JSON 객체만 반환하세요.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1000,
            )

            result_b_text = response_b.choices[0].message.content

            # OpenRouter JSON 추출 (더 강력한 로직)
            if settings.MODEL_B_PROVIDER == "openrouter":
                import re

                # 1. ```json ``` 마크다운 블록 찾기
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_b_text, re.DOTALL)
                if json_match:
                    result_b_text = json_match.group(1)
                # 2. ``` ``` 일반 코드 블록 찾기
                elif '```' in result_b_text:
                    json_match = re.search(r'```\s*(\{.*?\})\s*```', result_b_text, re.DOTALL)
                    if json_match:
                        result_b_text = json_match.group(1)
                # 3. JSON 객체만 추출 (마크다운 없이)
                else:
                    json_match = re.search(r'(\{[^{]*"overall_summary".*?\})\s*$', result_b_text, re.DOTALL)
                    if json_match:
                        result_b_text = json_match.group(1)

            # JSON 파싱 시도
            try:
                result_b = json.loads(result_b_text)
                result_b["model"] = self.model_b
                result_b["provider"] = settings.MODEL_B_PROVIDER
            except json.JSONDecodeError as e:
                logger.error(f"Model B JSON 파싱 실패: {e}")
                logger.error(f"응답 내용 (처음 500자): {result_b_text[:500]}")

                # 빈 리포트로 대체
                result_b = self._empty_report()
                result_b["model"] = self.model_b
                result_b["provider"] = settings.MODEL_B_PROVIDER
                result_b["parse_error"] = f"JSON 파싱 실패: {str(e)}"

            # 비교 분석
            comparison = self._compare_reports(result_a, result_b)

            logger.info(
                f"A/B 종합 리포트 완료: {stock_code} - "
                f"추천 일치: {comparison['recommendation_match']}"
            )

            return {
                "ab_test_enabled": True,
                "model_a": result_a,
                "model_b": result_b,
                "comparison": comparison,
            }

        except Exception as e:
            logger.error(f"A/B 종합 리포트 실패: {e}", exc_info=True)
            return {
                "ab_test_enabled": True,
                "model_a": self._empty_report(),
                "model_b": self._empty_report(),
                "comparison": {"error": str(e)},
            }

    def _compare_reports(self, report_a: Dict[str, Any], report_b: Dict[str, Any]) -> Dict[str, Any]:
        """두 리포트 비교"""
        # 추천 일치 여부
        rec_a = report_a.get("recommendation", "").lower()
        rec_b = report_b.get("recommendation", "").lower()

        recommendation_match = False
        if ("매수" in rec_a and "매수" in rec_b) or \
           ("매도" in rec_a and "매도" in rec_b) or \
           ("관망" in rec_a and "관망" in rec_b) or \
           ("보유" in rec_a and "보유" in rec_b):
            recommendation_match = True

        # 리스크 중복
        risks_a = set(report_a.get("risk_factors", []))
        risks_b = set(report_b.get("risk_factors", []))
        risk_overlap = list(risks_a & risks_b)

        # 기회 중복
        opps_a = set(report_a.get("opportunity_factors", []))
        opps_b = set(report_b.get("opportunity_factors", []))
        opportunity_overlap = list(opps_a & opps_b)

        return {
            "recommendation_match": recommendation_match,
            "risk_overlap": risk_overlap,
            "opportunity_overlap": opportunity_overlap,
        }

    def _empty_report(self) -> Dict[str, Any]:
        """빈 리포트 반환"""
        return {
            "overall_summary": "분석된 뉴스가 없습니다.",
            "short_term_scenario": None,
            "medium_term_scenario": None,
            "long_term_scenario": None,
            "risk_factors": [],
            "opportunity_factors": [],
            "recommendation": None,
        }


# 싱글톤 인스턴스
_generator: Optional[InvestmentReportGenerator] = None


def get_report_generator() -> InvestmentReportGenerator:
    """
    InvestmentReportGenerator 싱글톤 인스턴스 반환

    Returns:
        InvestmentReportGenerator 인스턴스
    """
    global _generator
    if _generator is None:
        _generator = InvestmentReportGenerator()
    return _generator
