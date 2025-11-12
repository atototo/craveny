# Epic 2: Predictor 리팩토링

**Epic ID**: PRED-002
**상태**: Ready
**예상 기간**: 1일
**담당**: Backend Team
**선행 조건**: Epic 1 완료

---

## 개요

Predictor 시스템을 가격 예측에서 영향도 분석 중심으로 리팩토링합니다.

---

## Story 목록

### Story 2.1: 프롬프트를 영향도 분석 중심으로 변경

**Story ID**: PRED-002-1
**우선순위**: P0
**예상 시간**: 3시간

#### 작업 내용
- `backend/llm/predictor.py`의 `_build_prompt` 메서드 수정
- 가격 예측 요청 제거
- 영향도 분석 요청 추가
- JSON 응답 구조 변경

#### 새 응답 구조
```json
{
  "sentiment_direction": "positive",
  "sentiment_score": 0.7,
  "impact_level": "high",
  "relevance_score": 0.85,
  "urgency_level": "urgent",
  "reasoning": "...",
  "impact_analysis": {
    "business_impact": "...",
    "market_sentiment_impact": "...",
    "competitive_impact": "...",
    "regulatory_impact": "..."
  },
  "pattern_analysis": {
    "avg_1d": 2.5,
    "avg_3d": 5.3,
    "avg_5d": 7.8
  }
}
```

#### 완료 조건
- [ ] 프롬프트 수정 완료
- [ ] JSON 스키마 업데이트
- [ ] 예시 응답 검증

---

### Story 2.2: 응답 파싱 로직 수정

**Story ID**: PRED-002-2
**우선순위**: P0
**예상 시간**: 2시간

#### 작업 내용
- `predict` 메서드의 응답 파싱 수정
- 새 필드 추출 로직 구현
- 에러 핸들링 강화

#### 완료 조건
- [ ] 응답 파싱 로직 구현
- [ ] 필드 매핑 정확성 검증
- [ ] 에러 케이스 처리

---

### Story 2.3: 새 필드 저장 로직 구현

**Story ID**: PRED-002-3
**우선순위**: P0
**예상 시간**: 2시간

#### 작업 내용
- DB 저장 로직 수정
- 새 필드 값 저장
- Deprecated 필드는 None으로 저장

#### 완료 조건
- [ ] 저장 로직 구현
- [ ] DB 저장 테스트 성공
- [ ] 필드 값 검증

---

### Story 2.4: 단위 테스트 작성 및 검증

**Story ID**: PRED-002-4
**우선순위**: P1
**예상 시간**: 3시간

#### 작업 내용
- 프롬프트 생성 테스트
- 응답 파싱 테스트
- DB 저장 테스트
- 통합 테스트

#### 테스트 케이스
```python
def test_predict_with_impact_analysis():
    """영향도 분석 응답 테스트"""
    result = predictor.predict(current_news, similar_news)

    assert "sentiment_direction" in result
    assert result["sentiment_score"] >= -1.0
    assert result["sentiment_score"] <= 1.0
    assert result["impact_level"] in ["low", "medium", "high", "critical"]
    assert "impact_analysis" in result
```

#### 완료 조건
- [ ] 10개 이상 테스트 케이스 작성
- [ ] 모든 테스트 통과
- [ ] 커버리지 > 80%

---

## Epic 완료 조건

- [ ] 모든 Story 완료
- [ ] 10개 샘플 뉴스로 테스트 성공
- [ ] 새 필드 정상 저장 확인
- [ ] 단위 테스트 통과
