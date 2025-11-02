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
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class StockPredictor:
    """LLM 기반 주가 예측 클래스"""

    def __init__(self):
        """예측 모델 초기화"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"  # GPT-4 Omni 모델 사용
        self.cache = get_prediction_cache()

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

        market_section += """
**⚠️ 시장 맥락 고려사항**:
- 시장 전체가 상승세라면 개별 종목의 긍정적 뉴스 영향이 증폭될 수 있습니다
- 시장이 하락세라면 부정적 뉴스의 영향이 더 클 수 있습니다
"""

        # 9. 최종 프롬프트 생성
        prompt = f"""
당신은 한국 주식 시장의 **종합 투자 어드바이저**입니다.
뉴스, 공시, 과거 패턴, 현재 주가를 종합적으로 분석하여 신뢰할 수 있는 예측을 제공하세요.

---

## 현재 뉴스
**종목**: {stock_name} ({stock_code})
**제목**: {current_news.get('title', 'N/A')}
**내용**: {current_news.get('content', 'N/A')[:300]}...

---
{price_section}
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

1. **패턴 분석**: 위 통계를 참고하여 유사 뉴스들의 주가 변동 패턴을 분석하세요
2. **예측**: 현재 뉴스가 주가에 미칠 영향을 예측하세요 (상승/하락/유지)
3. **신뢰도 계산**: 다음 요소를 고려하여 신뢰도를 계산하고, 각 요소의 점수를 제시하세요
   - 유사 뉴스 개수 및 유사도 (높을수록 신뢰도 상승)
   - 과거 패턴의 일관성 (변동폭이 일정할수록 신뢰도 상승)
   - 공시 정보 유무 (공시가 있으면 신뢰도 상승)
4. **근거**: 예측 근거를 **구체적 수치**와 함께 명확히 설명하세요

**응답 형식** (JSON):
```json
{{
  "prediction": "상승" | "하락" | "유지",
  "confidence": 75,
  "confidence_breakdown": {{
    "similar_news_quality": 85,
    "pattern_consistency": 70,
    "disclosure_impact": 60,
    "explanation": "신뢰도 계산 근거 설명"
  }},
  "reasoning": "예측 근거 설명 (구체적 수치 포함)",
  "pattern_analysis": {{
    "avg_1d": 2.5,
    "avg_3d": 5.3,
    "avg_5d": 7.8,
    "max_1d": 4.2,
    "min_1d": 0.8
  }},
  "short_term": "단기적으로 2.5% 상승 예상",
  "medium_term": "중기적으로 5.3% 상승 예상",
  "long_term": "장기적으로 7.8% 상승 예상"
}}
```

**중요 지침**:
- **confidence_breakdown**: 각 요소(similar_news_quality, pattern_consistency, disclosure_impact)를 0-100 점수로 평가하고, 계산 근거를 explanation에 설명하세요
- **pattern_analysis**: 유사 뉴스 통계를 그대로 반영하여 avg_1d, avg_3d, avg_5d 등을 제시하세요
- **reasoning**: "과거 15건 중 12건 상승, 평균 +7.2%" 같은 구체적 수치를 포함하세요
- short_term, medium_term, long_term에는 **반드시 구체적인 퍼센트(%)를 포함**하세요
- 유사 뉴스가 없으면 신뢰도를 낮게 설정하고, 뉴스 내용만으로 합리적인 수치를 제시하세요
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
        뉴스 기반 주가 예측

        Args:
            current_news: 현재 뉴스 정보
            similar_news: 유사 뉴스 리스트
            news_id: 뉴스 ID (캐싱용, 선택사항)
            use_cache: 캐시 사용 여부 (기본값: True)

        Returns:
            예측 결과 {
                "prediction": str,      # 상승/하락/유지
                "confidence": int,      # 0-100
                "reasoning": str,       # 예측 근거
                "short_term": str,      # 1일 예측
                "medium_term": str,     # 3일 예측
                "long_term": str,       # 5일 예측
                "similar_count": int,   # 참고한 유사 뉴스 개수
                "model": str,           # 사용 모델
                "timestamp": str,       # 예측 시각
                "cached": bool          # 캐시에서 조회했는지 여부
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

            # 2. GPT-4 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 한국 주식 시장 분석 전문가입니다. 뉴스 분석을 통해 주가 예측을 수행합니다.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # 낮은 temperature로 일관성 확보
                max_tokens=1000,
                response_format={"type": "json_object"},  # JSON 응답 강제
            )

            # 3. 응답 파싱
            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            # 4. 결과 보강
            result["similar_count"] = len(similar_news)
            result["model"] = self.model
            result["timestamp"] = datetime.now().isoformat()
            result["cached"] = False

            # 5. 신뢰도 breakdown이 없으면 기본값 추가 (하위 호환성)
            if "confidence_breakdown" not in result:
                result["confidence_breakdown"] = {
                    "similar_news_quality": result.get("confidence", 0),
                    "pattern_consistency": 0,
                    "disclosure_impact": 0,
                    "explanation": "구 버전 응답 (breakdown 없음)"
                }

            # 6. pattern_analysis가 없으면 기본값 추가 (하위 호환성)
            if "pattern_analysis" not in result:
                result["pattern_analysis"] = {
                    "avg_1d": None,
                    "avg_3d": None,
                    "avg_5d": None,
                }

            # 7. 검증
            if "prediction" not in result or "confidence" not in result:
                raise ValueError("예측 결과 형식 오류")

            # 신뢰도 breakdown 로깅
            breakdown = result.get("confidence_breakdown", {})
            logger.info(
                f"예측 완료: {result['prediction']} (신뢰도: {result['confidence']}%) - "
                f"유사도품질: {breakdown.get('similar_news_quality', 'N/A')}, "
                f"패턴일관성: {breakdown.get('pattern_consistency', 'N/A')}, "
                f"공시영향: {breakdown.get('disclosure_impact', 'N/A')}"
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
        예측 실패 시 폴백 응답

        Args:
            error_msg: 오류 메시지

        Returns:
            기본 예측 결과
        """
        return {
            "prediction": "유지",
            "confidence": 0,
            "reasoning": f"예측 실패: {error_msg}",
            "short_term": "예측 불가",
            "medium_term": "예측 불가",
            "long_term": "예측 불가",
            "similar_count": 0,
            "model": self.model,
            "timestamp": datetime.now().isoformat(),
            "error": error_msg,
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
