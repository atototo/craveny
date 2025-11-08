# Epic 3: API 변경사항 문서

## 개요

Epic 3에서 Prediction 모델의 필드가 변경되었습니다. 기존의 가격 예측 중심에서 **뉴스 영향도 분석** 중심으로 전환되었습니다.

## 변경된 데이터베이스 필드

### 새로 추가된 필드 (Required)

| 필드명 | 타입 | 범위 | 설명 |
|-------|------|------|------|
| `sentiment_direction` | String | `positive`, `negative`, `neutral` | 뉴스의 감성 방향 |
| `sentiment_score` | Float | -1.0 ~ 1.0 | 감성 점수 (양수=긍정, 음수=부정) |
| `impact_level` | String | `low`, `medium`, `high`, `critical` | 뉴스의 영향도 레벨 |
| `relevance_score` | Float | 0.0 ~ 1.0 | 종목과의 관련성 점수 |
| `urgency_level` | String | `routine`, `notable`, `urgent`, `breaking` | 뉴스의 긴급도 |
| `impact_analysis` | JSONB | - | 영향도 상세 분석 (business_impact, market_sentiment_impact 등) |

### Deprecated 필드 (하위 호환성 유지)

| 필드명 | 상태 | 비고 |
|-------|------|------|
| `direction` | Nullable | 기존 상승/하락/유지 예측 (새 레코드는 NULL) |
| `confidence` | Nullable | 기존 신뢰도 (새 레코드는 NULL) |
| `short_term` | Nullable | 기존 단기 예측 (새 레코드는 NULL) |
| `medium_term` | Nullable | 기존 중기 예측 (새 레코드는 NULL) |
| `long_term` | Nullable | 기존 장기 예측 (새 레코드는 NULL) |

## API 변경사항

### 1. GET /api/stocks/{stock_code}

#### 응답 구조 변경

**Before (Epic 2 이전):**
```json
{
  "recent_news": [
    {
      "id": 123,
      "title": "...",
      "prediction": {
        "direction": "up",
        "confidence": 85,
        "reasoning": "...",
        "short_term": "...",
        "medium_term": "...",
        "long_term": "..."
      }
    }
  ]
}
```

**After (Epic 3 이후):**
```json
{
  "recent_news": [
    {
      "id": 123,
      "title": "...",
      "prediction": {
        // 새로운 영향도 분석 필드 (우선 사용 권장)
        "sentiment_direction": "positive",
        "sentiment_score": 0.75,
        "impact_level": "high",
        "relevance_score": 0.85,
        "urgency_level": "urgent",
        "impact_analysis": {
          "business_impact": "매출 증가 예상",
          "market_sentiment_impact": "긍정적 반응",
          "competitive_impact": "경쟁 우위",
          "regulatory_impact": "변화 없음"
        },
        "reasoning": "...",

        // Deprecated 필드 (하위 호환성, NULL일 수 있음)
        "direction": null,
        "confidence": null,
        "short_term": null,
        "medium_term": null,
        "long_term": null,
        "confidence_breakdown": null,
        "pattern_analysis": null
      }
    }
  ]
}
```

### 2. Investment Report API (stocks.py:398-440)

Epic 3에서 투자 리포트는 **영향도 분석 기반**으로 생성됩니다:

- **감성 분포**: 긍정/부정/중립 뉴스 개수
- **영향도 분포**: 높음/중간/낮음 영향도 개수
- **평균 감성 점수**: -1.0 ~ 1.0
- **평균 관련성**: 0.0 ~ 1.0
- **가격 예측**: 뉴스 영향도 + 기술적 지표 결합

## 마이그레이션 가이드

### Frontend 마이그레이션

#### 1단계: 새 필드 우선 사용

```typescript
// Before
if (prediction.direction === "up") {
  // 상승 처리
}

// After (권장)
if (prediction.sentiment_direction === "positive") {
  // 긍정 뉴스 처리
}
```

#### 2단계: 하위 호환성 처리

```typescript
// 새 필드가 없으면 기존 필드 사용 (Epic 2 이전 데이터)
const direction = prediction.sentiment_direction || prediction.direction || "neutral";
const score = prediction.sentiment_score ?? (prediction.confidence ? prediction.confidence / 100 : 0);
```

#### 3단계: UI 업데이트

```tsx
// 영향도 레벨 표시
<Badge color={impactLevelColor(prediction.impact_level)}>
  {impactLevelText(prediction.impact_level)}
</Badge>

// 감성 점수 표시
<ProgressBar
  value={(prediction.sentiment_score + 1) / 2 * 100}
  label={`감성: ${(prediction.sentiment_score * 100).toFixed(0)}%`}
/>
```

### Backend 마이그레이션

#### 필드 검증

```python
# Epic 3 이후 Predictor가 생성하는 구조
prediction = {
    "sentiment_direction": "positive",  # Required
    "sentiment_score": 0.75,            # Required
    "impact_level": "high",             # Required
    "relevance_score": 0.85,            # Required
    "urgency_level": "urgent",          # Required
    "impact_analysis": {...},           # Required
    "reasoning": "...",                 # Required

    # Deprecated (None으로 저장됨)
    "direction": None,
    "confidence": None,
    "short_term": None,
    "medium_term": None,
    "long_term": None
}
```

## 테스트

### Epic 3 통합 테스트

```bash
# Epic 3 완료 확인 테스트
uv run python scripts/test_investment_report.py
```

**예상 결과:**
```
✅ Epic 3 완료 조건 충족: 3개 이상 종목 리포트 생성 성공
```

### API 테스트

```bash
# 종목 상세 API 테스트
curl http://localhost:8000/api/stocks/005930 | jq '.recent_news[0].prediction'
```

**예상 응답:**
```json
{
  "sentiment_direction": "neutral",
  "sentiment_score": 0.0,
  "impact_level": "medium",
  "relevance_score": 0.8,
  "urgency_level": "notable",
  "impact_analysis": {...},
  "reasoning": "...",
  "direction": null,  // Deprecated
  "confidence": null  // Deprecated
}
```

## 롤백 계획

Epic 3 이전으로 롤백이 필요한 경우:

1. **데이터베이스**: Deprecated 필드가 nullable이므로 기존 데이터는 유지됨
2. **API**: 하위 호환성이 유지되므로 Frontend는 변경 없이 동작
3. **Predictor**: `backend/llm/predictor.py`의 `_build_prompt()` 및 파싱 로직을 Epic 2 버전으로 복구

## 참고 문서

- Epic 2 완료 문서: `backend/tests/test_impact_analysis_integration.py`
- Epic 3 완료 문서: `scripts/test_investment_report.py`
- PRD: Epic 2, Epic 3 스펙 참조
