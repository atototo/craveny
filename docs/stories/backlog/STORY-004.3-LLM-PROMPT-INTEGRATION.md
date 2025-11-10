# Story 004.3: LLM 프롬프트 통합 및 분석 로직 강화

**Epic**: Epic 004 | **Priority**: ⭐⭐⭐⭐⭐ | **Effort**: 4-6일 | **Dependencies**: Story 004.1, 004.2

---

## 📋 Overview

투자자 매매 + 재무제표 데이터를 LLM 프롬프트에 통합하여 다차원 분석을 수행합니다.

---

## 🎯 Acceptance Criteria

1. ✅ 프롬프트 템플릿에 투자자 매매/재무 데이터 추가
2. ✅ 데이터 조회 헬퍼 함수 구현
3. ✅ LLM 분석 서비스 업데이트
4. ✅ 프롬프트 토큰 길이 ≤4,000
5. ✅ 분석 시간 평균 5초 이내

---

## 🔧 Implementation

### 프롬프트 템플릿

```python
# backend/llm/prompts.py

NEWS_ANALYSIS_PROMPT_V2 = """
[뉴스 정보]
- 제목: {news_title}
- 내용: {news_content}
- 발표 시각: {published_at}

[주가 정보]
- 현재가: {current_price:,}원
- 1일 변동: {price_change_1d}%
- 거래량: {volume:,}주

[투자자 매매 동향] ⭐ NEW
- 외국인 순매수: {foreign_net:,}주 ({foreign_signal})
- 기관 순매수: {institution_net:,}주 ({institution_signal})
- 개인 순매수: {individual_net:,}주

[재무 현황] ⭐ NEW
- 최근 분기({latest_quarter}):
  - 매출: {revenue:,}억원
  - 영업이익률: {operating_margin:.1f}%
  - PER: {per:.1f}, PBR: {pbr:.2f}
  - ROE: {roe:.1f}%, 부채비율: {debt_ratio:.1f}%

[질문]
이 뉴스가 주가에 미칠 영향을 다음 관점에서 분석하세요:
1. 뉴스의 펀더멘털 영향 (재무제표 기반 실체 검증)
2. 스마트 머니 흐름 (외국인/기관 매매 분석)
3. 종합 판단 및 1일/3일/5일 예상 변동률

응답 형식 (JSON):
{{
  "fundamental_impact": "긍정/부정/중립",
  "smart_money_signal": "매수/매도/중립",
  "predicted_change_1d": 0.0,
  "predicted_change_3d": 0.0,
  "predicted_change_5d": 0.0,
  "confidence": 0.0,
  "reasoning": "..."
}}
"""
```

### 데이터 통합 서비스

```python
# backend/services/data_aggregator.py

class DataAggregator:
    """뉴스-주가-투자자-재무 데이터 통합"""

    def get_comprehensive_stock_data(
        self,
        stock_code: str,
        date: datetime
    ) -> dict:
        """종합 데이터 조회"""

        # 주가 데이터
        stock_price = self.db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code,
            StockPrice.date == date.date()
        ).first()

        # 투자자 매매
        investor_data = self.db.query(InvestorTrading).filter(
            InvestorTrading.stock_code == stock_code,
            InvestorTrading.date == date.date()
        ).first()

        # 재무제표 (최근 분기)
        latest_quarter = self.db.query(FinancialStatement).filter(
            FinancialStatement.stock_code == stock_code
        ).order_by(FinancialStatement.quarter.desc()).first()

        # 통합
        return {
            "stock_info": {"code": stock_code, ...},
            "price_data": {
                "current_price": stock_price.close if stock_price else None,
                "volume": stock_price.volume if stock_price else None,
                ...
            },
            "investor_trading": {
                "foreign_net": investor_data.foreign_net if investor_data else 0,
                "foreign_signal": self._get_signal(investor_data.foreign_net) if investor_data else "중립",
                "institution_net": investor_data.institution_net if investor_data else 0,
                ...
            } if investor_data else None,
            "financial_statements": {
                "latest_quarter": latest_quarter.quarter if latest_quarter else None,
                "revenue": latest_quarter.revenue // 100000000 if latest_quarter else None,  # 억원
                "operating_margin": (latest_quarter.operating_profit / latest_quarter.revenue * 100) if latest_quarter and latest_quarter.revenue else 0,
                ...
            } if latest_quarter else None
        }

    def _get_signal(self, net_value: int) -> str:
        """순매수 신호 변환"""
        if net_value > 100000:
            return "강한 매수"
        elif net_value > 0:
            return "매수"
        elif net_value < -100000:
            return "강한 매도"
        elif net_value < 0:
            return "매도"
        else:
            return "중립"
```

### LLM 분석 서비스 업데이트

```python
# backend/services/stock_analysis_service.py

class StockAnalysisService:
    async def analyze_news_impact(self, news_id: int) -> dict:
        """뉴스 영향 분석 (강화 버전)"""

        # 뉴스 조회
        news = self.db.query(News).get(news_id)

        # 종합 데이터 조회 ⭐ NEW
        aggregator = DataAggregator(self.db)
        stock_data = aggregator.get_comprehensive_stock_data(
            stock_code=news.stock_code,
            date=news.published_at
        )

        # 프롬프트 생성 ⭐ UPDATED
        prompt = NEWS_ANALYSIS_PROMPT_V2.format(
            news_title=news.title,
            news_content=news.content[:500],  # 토큰 절약
            published_at=news.published_at.isoformat(),
            **stock_data["price_data"],
            **stock_data["investor_trading"] if stock_data["investor_trading"] else {},
            **stock_data["financial_statements"] if stock_data["financial_statements"] else {}
        )

        # 토큰 길이 체크
        token_count = self._count_tokens(prompt)
        if token_count > 4000:
            logger.warning(f"Prompt too long: {token_count} tokens")

        # LLM 호출
        response = await self.openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        # 결과 파싱
        result = json.loads(response.choices[0].message.content)

        # DB 저장
        self._save_analysis_result(news_id, result)

        return result
```

---

## ✅ Definition of Done

- [ ] 프롬프트 템플릿 V2 작성
- [ ] DataAggregator 서비스 구현
- [ ] StockAnalysisService 업데이트
- [ ] 토큰 길이 최적화 (≤4,000)
- [ ] 10건 테스트 분석 성공
- [ ] 평균 분석 시간 ≤5초
- [ ] 코드 리뷰 및 머지
