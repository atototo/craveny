# PRD: 예측 시스템 구조 개선 (Prediction System Refactoring)

## 📋 개요

**작성일**: 2025-01-06
**버전**: 1.0
**상태**: Planning

### 목적
뉴스 분석과 가격 예측의 책임을 명확히 분리하여 시스템의 명확성과 유지보수성을 향상시킨다.

### 문제 정의
현재 시스템은 뉴스 분석 단계에서 가격 예측을 수행하고, 종합 리포트에서도 가격 예측을 수행하여 책임이 중복되고 애매한 `confidence` 필드로 인해 혼란이 발생한다.

### 해결 방안
- **뉴스 분석**: 영향도 분석만 수행 (sentiment, impact level, urgency)
- **종합 리포트**: 뉴스 영향도 + 기술적 지표 기반으로 가격 예측 수행

---

## 🎯 목표

### 비즈니스 목표
1. 시스템 아키텍처의 명확성 향상
2. 예측 정확도 개선 (영향도 + 기술적 지표 통합)
3. 사용자 혼란 감소 (신뢰도 제거)

### 기술 목표
1. 명확한 책임 분리 (Separation of Concerns)
2. 확장 가능한 구조 (새로운 영향도 차원 추가 용이)
3. 데이터 일관성 유지 (마이그레이션)

### 성공 지표
- [ ] 모든 기존 예측 데이터 마이그레이션 성공률 100%
- [ ] API 호환성 유지 (Breaking Change 최소화)
- [ ] 프론트엔드 정상 작동 확인
- [ ] 종합 리포트 생성 성공률 100%

---

## 🏗️ 아키텍처 변경

### AS-IS (현재)
```
뉴스 분석 (Predictor)
  ↓
- direction (상승/하락/유지)
- confidence (0-100)
- short_term, medium_term, long_term (가격 예측)
- confidence_breakdown
  ↓
종합 리포트 (Investment Report)
  ↓
- 예측 데이터 집계
- 기술적 지표 추가
- 시나리오 생성 (1일~1주, 1주~1개월, 1개월+)
```

### TO-BE (변경 후)
```
뉴스 분석 (Predictor)
  ↓
- sentiment_direction (positive/negative/neutral)
- sentiment_score (-1.0 ~ 1.0)
- impact_level (low/medium/high/critical)
- relevance_score (0.0 ~ 1.0)
- urgency_level (routine/notable/urgent/breaking)
- impact_analysis (상세 영향도)
  ↓
종합 리포트 (Investment Report)
  ↓
- 뉴스 영향도 집계
- 기술적 지표 분석
- **가격 예측 수행** (목표가, 손절가)
- 시나리오 생성 (1일~1주, 1주~1개월, 1개월+)
```

---

## 📊 데이터 모델 변경

### Prediction 모델

#### 제거할 필드
| 필드명 | 타입 | 사유 |
|--------|------|------|
| `short_term` | Text | 가격 예측은 종합 리포트에서 담당 |
| `medium_term` | Text | 가격 예측은 종합 리포트에서 담당 |
| `long_term` | Text | 가격 예측은 종합 리포트에서 담당 |
| `confidence` | Float | 기준이 애매하고 혼란 초래 |
| `confidence_breakdown` | JSON | confidence 제거로 불필요 |

#### 추가할 필드
| 필드명 | 타입 | 설명 | 값 범위 |
|--------|------|------|---------|
| `sentiment_score` | Float | 감성 점수 | -1.0 (매우 부정) ~ 1.0 (매우 긍정) |
| `impact_level` | String | 영향도 등급 | low, medium, high, critical |
| `relevance_score` | Float | 관련성 점수 | 0.0 (무관) ~ 1.0 (직접 관련) |
| `urgency_level` | String | 긴급도 | routine, notable, urgent, breaking |
| `impact_analysis` | JSON | 상세 영향도 분석 | 구조화된 JSON |

#### 변경할 필드
| 기존 필드명 | 새 필드명 | 변경 사유 |
|------------|----------|-----------|
| `direction` | `sentiment_direction` | 의미 명확화 (가격 방향 → 감성 방향) |

#### 유지할 필드
- `reasoning`: 영향도 분석 근거 설명
- `pattern_analysis`: 과거 패턴 참고 데이터 (읽기 전용)
- `stock_code`, `news_id`, `model_id`, `created_at` 등 기본 필드

---

## 🔄 시스템 플로우

### 1. 뉴스 수집 및 분석
```
뉴스 크롤링
  ↓
유사 뉴스 검색
  ↓
Predictor: 영향도 분석
  - sentiment_score 계산
  - impact_level 판단
  - relevance_score 평가
  - urgency_level 결정
  ↓
DB 저장 (predictions 테이블)
```

### 2. 종합 리포트 생성
```
종목 선택
  ↓
최근 30일 뉴스 영향도 집계
  - 긍정/부정/중립 분포
  - 평균 영향도
  - 긴급 뉴스 개수
  ↓
기술적 지표 조회
  - 이동평균선
  - RSI, 볼린저밴드, MACD
  - 거래량 분석
  ↓
Investment Report: 가격 예측
  - 단기 목표가/손절가 (1일~1주)
  - 중기 목표가/손절가 (1주~1개월)
  - 장기 목표가/손절가 (1개월+)
  ↓
리포트 저장 및 표시
```

---

## 🎨 UI/UX 변경

### 뉴스 영향도 표시

**AS-IS**:
```
방향: 상승 ↑
신뢰도: 75%
단기: 2.5% 상승 예상
중기: 5.3% 상승 예상
장기: 7.8% 상승 예상
```

**TO-BE**:
```
감성: 긍정적 (0.7/1.0) 😊
영향도: 높음 🔥
관련성: 85%
긴급도: 주목할만함ⓘ

영향 분석:
- 사업 영향: 신제품 출시로 실적 개선 예상
- 시장 심리: 투자자 관심 증가 예상
- 경쟁 우위: 기술 격차 확대
```

### 종합 리포트 표시

**추가되는 섹션**:
```
## 뉴스 영향도 요약
- 최근 30일: 긍정 15건, 부정 3건, 중립 2건
- 평균 영향도: High
- 긴급 대응 필요: 2건

## 가격 예측 (영향도 + 기술적 지표 기반)
단기 (1일~1주):
  - 목표가: 85,000원 (+8.5%)
  - 손절가: 78,000원 (-0.5%)
  - 근거: 긍정 뉴스 다수 + RSI 과매도 → 반등 예상

중기 (1주~1개월):
  - 목표가: 92,000원 (+17.3%)
  - 손절가: 80,000원 (+2.0%)
  - 근거: 신제품 출시 효과 + MA20 상향 돌파

장기 (1개월+):
  - 목표가: 105,000원 (+33.8%)
  - 손절가: 85,000원 (+8.5%)
  - 근거: 시장 점유율 확대 전망
```

---

## 🚀 Epic & Story 구조

### Epic 1: 데이터 모델 변경
- **Story 1.1**: Prediction 모델 스키마 업데이트
- **Story 1.2**: 마이그레이션 스크립트 작성
- **Story 1.3**: 기존 데이터 마이그레이션 실행
- **Story 1.4**: 데이터 무결성 검증

### Epic 2: Predictor 리팩토링
- **Story 2.1**: 프롬프트를 영향도 분석 중심으로 변경
- **Story 2.2**: 응답 파싱 로직 수정
- **Story 2.3**: 새 필드 저장 로직 구현
- **Story 2.4**: 단위 테스트 작성 및 검증

### Epic 3: Investment Report 개선
- **Story 3.1**: 뉴스 영향도 집계 로직 구현
- **Story 3.2**: 가격 예측 프롬프트 추가
- **Story 3.3**: 리포트 생성 로직 수정
- **Story 3.4**: 통합 테스트 및 검증

### Epic 4: API 업데이트
- **Story 4.1**: Prediction API 응답 구조 변경
- **Story 4.2**: Investment Report API 응답 구조 변경
- **Story 4.3**: API 문서 업데이트
- **Story 4.4**: 하위 호환성 검증

### Epic 5: 프론트엔드 업데이트
- **Story 5.1**: 뉴스 영향도 표시 컴포넌트 개발
- **Story 5.2**: 종합 리포트 UI 개선
- **Story 5.3**: 기존 신뢰도 표시 제거
- **Story 5.4**: E2E 테스트

### Epic 6: 데이터 정리 및 문서화
- **Story 6.1**: Deprecated 필드 제거
- **Story 6.2**: 코드 주석 및 문서 업데이트
- **Story 6.3**: API 문서 최종 업데이트
- **Story 6.4**: 운영 가이드 작성

---

## ⚠️ 리스크 및 대응 방안

### 리스크 1: 데이터 마이그레이션 실패
- **확률**: Medium
- **영향도**: High
- **대응**:
  - 마이그레이션 전 전체 DB 백업
  - 롤백 스크립트 준비
  - 스테이징 환경에서 먼저 테스트

### 리스크 2: API Breaking Change
- **확률**: High
- **영향도**: High
- **대응**:
  - API 버전 관리 (v1 → v2)
  - 기존 API 일정 기간 유지 (Deprecated)
  - 마이그레이션 가이드 제공

### 리스크 3: 프론트엔드 호환성 이슈
- **확률**: Medium
- **영향도**: Medium
- **대응**:
  - 단계별 배포 (백엔드 먼저, 프론트엔드 나중)
  - Feature Flag 사용
  - 철저한 E2E 테스트

### 리스크 4: 종합 리포트 생성 실패
- **확률**: Low
- **영향도**: High
- **대응**:
  - LLM 프롬프트 충분한 테스트
  - Fallback 로직 구현
  - 에러 로깅 강화

---

## 📅 일정 계획

### Phase 1: 준비 (1일)
- Epic 1 완료 (데이터 모델 변경)
- 마이그레이션 스크립트 검증

### Phase 2: 백엔드 개발 (2일)
- Epic 2 완료 (Predictor 리팩토링)
- Epic 3 완료 (Investment Report 개선)
- Epic 4 완료 (API 업데이트)

### Phase 3: 프론트엔드 개발 (1일)
- Epic 5 완료 (프론트엔드 업데이트)
- E2E 테스트

### Phase 4: 배포 및 정리 (1일)
- 스테이징 배포 및 검증
- 프로덕션 배포
- Epic 6 완료 (문서화)

**총 예상 기간**: 5일

---

## ✅ 완료 조건

### Epic 1: 데이터 모델 변경
- [ ] 마이그레이션 스크립트 작성 완료
- [ ] 기존 1164개 예측 데이터 마이그레이션 성공
- [ ] 데이터 무결성 검증 완료

### Epic 2: Predictor 리팩토링
- [ ] 새 프롬프트로 10개 샘플 뉴스 분석 성공
- [ ] 모든 새 필드 정상 저장 확인
- [ ] 단위 테스트 통과

### Epic 3: Investment Report 개선
- [ ] 5개 종목 종합 리포트 생성 성공
- [ ] 가격 예측 포함 확인
- [ ] 통합 테스트 통과

### Epic 4: API 업데이트
- [ ] API 문서 업데이트 완료
- [ ] Postman/Swagger 테스트 성공
- [ ] 하위 호환성 검증 완료

### Epic 5: 프론트엔드 업데이트
- [ ] 뉴스 영향도 정상 표시
- [ ] 종합 리포트 정상 표시
- [ ] E2E 테스트 통과

### Epic 6: 데이터 정리
- [ ] Deprecated 필드 제거
- [ ] 모든 문서 업데이트 완료
- [ ] 운영 가이드 작성 완료

---

## 📚 참고 자료

- 기존 Prediction 모델: `backend/db/models/prediction.py`
- 기존 Predictor: `backend/llm/predictor.py`
- 기존 Investment Report: `backend/llm/investment_report.py`
- 평가 서비스: `backend/services/evaluation_service.py`
- 집계 서비스: `backend/services/aggregation_service.py`

---

## 🔗 관련 문서

- [Epic 1: 데이터 모델 변경](./epics/epic-1-data-model.md)
- [Epic 2: Predictor 리팩토링](./epics/epic-2-predictor.md)
- [Epic 3: Investment Report 개선](./epics/epic-3-investment-report.md)
- [Epic 4: API 업데이트](./epics/epic-4-api.md)
- [Epic 5: 프론트엔드 업데이트](./epics/epic-5-frontend.md)
- [Epic 6: 데이터 정리](./epics/epic-6-cleanup.md)
