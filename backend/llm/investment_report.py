"""
LLM 기반 종합 투자 리포트 생성 모듈

종목별 AI 예측 결과를 종합하여 투자 전문가 수준의 리포트를 생성합니다.
"""
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from openai import OpenAI

from backend.config import settings
from backend.db.models.prediction import Prediction
from backend.db.models.stock import StockPrice
from backend.utils.stock_mapping import get_stock_mapper


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
            self.client_a = self._create_client(settings.MODEL_A_PROVIDER)
            self.model_a = settings.MODEL_A_NAME
            self.client_b = self._create_client(settings.MODEL_B_PROVIDER)
            self.model_b = settings.MODEL_B_NAME
            logger.info(f"A/B 테스트 활성화 (종합 리포트): Model A={self.model_a}, Model B={self.model_b}")

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

    def _prepare_report_data(
        self,
        stock_code: str,
        predictions: List[Prediction],
        current_price: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """리포트 생성을 위한 데이터 준비"""
        stock_name = self.stock_mapper.get_company_name(stock_code) or stock_code

        # 통계 계산
        total = len(predictions)
        up_count = sum(1 for p in predictions if p.direction == "up")
        down_count = sum(1 for p in predictions if p.direction == "down")
        hold_count = sum(1 for p in predictions if p.direction == "hold")

        confidences = [p.confidence for p in predictions if p.confidence]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

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

        # 최근 뉴스 분석 (최대 5건)
        recent_news_analysis = []
        for pred in predictions[:5]:
            recent_news_analysis.append({
                "created_at": pred.created_at.strftime("%Y-%m-%d") if pred.created_at else "N/A",
                "direction": pred.direction,
                "confidence": round(pred.confidence * 100) if pred.confidence else 0,
                "reasoning": pred.reasoning[:200] if pred.reasoning else "분석 내용 없음",
                "short_term": pred.short_term,
                "medium_term": pred.medium_term,
                "long_term": pred.long_term,
            })

        return {
            "stock_info": {
                "code": stock_code,
                "name": stock_name,
                "current_price": current_price.get("close") if current_price else None,
                "change_rate": current_price.get("change_rate") if current_price else None,
            },
            "statistical_summary": {
                "total_predictions": total,
                "direction_distribution": {
                    "up": up_count,
                    "down": down_count,
                    "hold": hold_count,
                },
                "avg_confidence": round(avg_confidence * 100, 1) if avg_confidence else 0,
                "confidence_breakdown_avg": breakdown_avg,
                "pattern_analysis_avg": pattern_avg,
            },
            "recent_news_analysis": recent_news_analysis,
            "time_context": {
                "today": datetime.now().strftime("%Y-%m-%d"),
                "analysis_period": "최근 30일",
                "latest_analysis_date": predictions[0].created_at.strftime("%Y-%m-%d") if predictions[0].created_at else "N/A",
            },
        }

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        """LLM 프롬프트 생성"""
        stock_info = data["stock_info"]
        stats = data["statistical_summary"]
        recent_news = data["recent_news_analysis"]
        time_ctx = data["time_context"]

        prompt = f"""
당신은 {stock_info['name']}({stock_info['code']})에 대한 **데일리 투자 리포트**를 작성합니다.

## 현재 상황 ({time_ctx['today']})
- 현재가: {stock_info['current_price']:,}원 (전일 대비 {stock_info['change_rate']:+.2f}%) {f"" if stock_info['current_price'] else "현재가 정보 없음"}
- 분석 기간: {time_ctx['analysis_period']}
- 분석된 뉴스: 총 {stats['total_predictions']}건

## AI 분석 결과 요약
- 예측 방향: 상승 {stats['direction_distribution']['up']}건, 하락 {stats['direction_distribution']['down']}건, 보합 {stats['direction_distribution']['hold']}건
- 평균 신뢰도: {stats['avg_confidence']}%

### 신뢰도 구성 (평균)
- 유사 뉴스 품질: {stats['confidence_breakdown_avg']['similar_news_quality'] or 'N/A'}점
- 패턴 일관성: {stats['confidence_breakdown_avg']['pattern_consistency'] or 'N/A'}점
- 공시 영향: {stats['confidence_breakdown_avg']['disclosure_impact'] or 'N/A'}점

## 과거 패턴 분석 (유사 뉴스 기반 평균 변동률)
- T+1일: {f"{stats['pattern_analysis_avg']['avg_1d']:+.1f}%" if stats['pattern_analysis_avg']['avg_1d'] is not None else 'N/A'}
- T+3일: {f"{stats['pattern_analysis_avg']['avg_3d']:+.1f}%" if stats['pattern_analysis_avg']['avg_3d'] is not None else 'N/A'}
- T+5일: {f"{stats['pattern_analysis_avg']['avg_5d']:+.1f}%" if stats['pattern_analysis_avg']['avg_5d'] is not None else 'N/A'}
- T+10일: {f"{stats['pattern_analysis_avg']['avg_10d']:+.1f}%" if stats['pattern_analysis_avg']['avg_10d'] is not None else 'N/A'}
- T+20일: {f"{stats['pattern_analysis_avg']['avg_20d']:+.1f}%" if stats['pattern_analysis_avg']['avg_20d'] is not None else 'N/A'}

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
  "recommendation": "최종 추천: 명확한 액션(매수/관망/매도) + 간결한 이유 (1-2문장)"
}}
```

**중요 지침**:
1. 과거가 아닌 **미래 전망**에 집중
2. 구체적인 **수치와 기간**을 명시
3. 투자자가 **오늘 결정**을 내릴 수 있도록 작성
4. 리스크와 기회는 각각 **최대 3개**까지만
5. **간결하고 명확**하게 (불필요한 수식어 제거)
"""
        return prompt.strip()

    def _format_recent_news(self, recent_news: List[Dict[str, Any]]) -> str:
        """최근 뉴스 분석 포맷팅"""
        lines = []
        for i, news in enumerate(recent_news, 1):
            direction_kr = {"up": "상승", "down": "하락", "hold": "보합"}.get(news["direction"], news["direction"])
            lines.append(
                f"### {i}. {news['created_at']} - {direction_kr} 예측 (신뢰도 {news['confidence']}%)\n"
                f"- AI 분석: {news['reasoning']}\n"
                f"- 기간별 예측: {news.get('short_term') or 'N/A'} / {news.get('medium_term') or 'N/A'} / {news.get('long_term') or 'N/A'}"
            )
        return "\n\n".join(lines)

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
                        "content": "당신은 한국 주식 시장의 베테랑 애널리스트입니다. 데이터 기반으로 명확하고 실용적인 투자 리포트를 작성합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
                max_tokens=1000,
            )

            result_b_text = response_b.choices[0].message.content

            # OpenRouter JSON 추출
            if settings.MODEL_B_PROVIDER == "openrouter" and "```json" in result_b_text:
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', result_b_text, re.DOTALL)
                if json_match:
                    result_b_text = json_match.group(1)

            result_b = json.loads(result_b_text)
            result_b["model"] = self.model_b
            result_b["provider"] = settings.MODEL_B_PROVIDER

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
