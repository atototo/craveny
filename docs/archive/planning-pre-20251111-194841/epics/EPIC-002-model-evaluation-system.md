---
epic_id: EPIC-002
title: LLM 모델 평가 시스템
status: complete
priority: high
created: 2025-11-05
completed: 2025-11-07
analyst: Mary (Business Analyst)
estimated_duration: 2-3 weeks
actual_duration: 2 days
---

# Epic: LLM 모델 평가 시스템

## 📊 Business Context

### 현재 문제
- **모델 성능 측정 불가**: LLM 모델들(Qwen3, DeepSeek, GPT-4o)의 예측 정확도를 정량적으로 측정할 방법 없음
- **목표가/손절가 추적 부재**: Investment Report에서 제시한 목표가, 손절가 달성 여부를 실제 주가와 비교하지 못함
- **A/B 테스트 결과 불명확**: 2개 모델 A/B 테스트 중이지만 어느 모델이 더 우수한지 데이터 기반 판단 불가
- **전문가 인사이트 부재**: 자동 메트릭만으로는 LLM 예측의 정성적 품질(분석 논리, 실용성)을 평가할 수 없음

### Business Impact
- **모델 선택 근거 부족**: 어떤 모델을 메인으로 사용할지 데이터 기반 의사결정 불가
- **투자 신뢰도 검증 불가**: 사용자에게 제공하는 투자 리포트의 정확도 검증 안됨
- **개선 방향 불명확**: 어떤 부분을 개선해야 하는지 인사이트 부족
- **비용 최적화 실패**: 비싼 모델과 저렴한 모델의 성능 대비 비용 효율성 측정 불가

### 목표
**자동 평가 + 사람 평가를 결합한 하이브리드 모델 평가 시스템 구축**
- 매일 자동으로 모델 예측 vs 실제 주가 비교
- 전문가가 정성적 평가 (분석 품질, 실용성)
- Daily 평가 누적 및 트렌드 분석
- 모델별 성능 리더보드 및 상세 분석 대시보드

## 🎯 Success Metrics

| Metric | Current | Target | Measure |
|--------|---------|--------|---------|
| 모델 평가 데이터 | 없음 | Daily 축적 | 일일 평가 건수 |
| 목표가 달성률 추적 | 불가 | 자동 측정 | 달성률 % |
| 사람 평가 커버리지 | 0% | 30%+ | Priority 1-2 종목 |
| 평가 소요 시간 | - | < 30초/건 | 평가 UI 효율성 |
| 모델 비교 가능 | 불가 | 가능 | 리더보드 제공 |

## 🔍 Research Summary

### 평가 방법론 리서치
1. **자동 평가 메트릭 (70%)**
   - 전통적 ML 메트릭(정확도, F1)은 금융 예측에 부적합
   - 금융 특화 지표 필수: 수익률, 샤프 비율, 최대 낙폭, 목표가 달성률, 타이밍 정확도

2. **사람 평가 (30%)**
   - LLM 예측의 정성적 품질은 사람만 판단 가능
   - 분석 품질, 실용성, 종합 만족도 (1-5점 척도)
   - HITL(Human-in-the-Loop) 시스템 설계 원칙 적용

3. **하이브리드 점수 산정**
   - 최종 점수 = 자동 70% + 사람 30%
   - 객관성과 전문성의 균형

### 평가 대상 명확화
- ✅ **Investment Report (종합 투자 리포트)**: 목표가, 손절가 포함 → 평가 가능
- ❌ **News Prediction (뉴스별 간단 예측)**: 구체적 숫자 없음 → 평가 불가

## 📋 Stories

### Phase 1: 기본 평가 인프라 (Week 1)
1. **[STORY-004] DB 스키마 설계 및 마이그레이션**
   - `model_evaluations` 테이블 생성
   - `daily_model_performance` 집계 테이블 생성
   - `evaluation_history` 수정 이력 테이블 생성
   - 마이그레이션 스크립트 작성 및 실행

2. **[STORY-005] 자동 평가 배치 작업**
   - 매일 16:00 자동 평가 배치 실행
   - 실제 주가 데이터 수집 (T+1일, T+5일)
   - 목표가 달성 여부, 손절가 이탈 여부 판단
   - 자동 점수 계산 (목표가 정확도, 타이밍, 리스크 관리)

3. **[STORY-006] Daily 성능 집계 배치 작업**
   - 매일 17:00 모델별 성능 집계
   - 평균 점수, 달성률 등 통계 계산
   - `daily_model_performance` 테이블 업데이트

### Phase 2: 사람 평가 시스템 (Week 2)
4. **[STORY-007] 평가 API 엔드포인트**
   - `GET /api/evaluations/queue` - 평가 대기 목록
   - `GET /api/evaluations/daily` - Daily 평가 내역
   - `POST /api/evaluations/{id}/rate` - 사람 평가 저장
   - `PUT /api/evaluations/{id}/rate` - 평가 수정
   - `GET /api/evaluations/dashboard` - 대시보드 데이터

5. **[STORY-008] 평가 UI 구현**
   - 평가 대기 목록 화면
   - 평가 모달 (1-5점 척도 + 선택적 코멘트)
   - Daily 평가 내역 화면 (날짜별 조회/수정)
   - 평가 수정 이력 추적

### Phase 3: 대시보드 & 분석 (Week 3)
6. **[STORY-009] 모델 성능 대시보드**
   - 모델 리더보드 (최종 점수 기준)
   - 성능 트렌드 차트 (최근 30일)
   - 오늘의 평가 현황

7. **[STORY-010] 모델 상세 분석 페이지**
   - 모델별 세부 메트릭 브레이크다운
   - 종목별 성능 분석
   - 기간별 성과 추이

## 🗄️ Database Schema

### `model_evaluations` 테이블
```sql
- id: PK
- prediction_id: Investment Report FK
- model_id: 모델 ID
- stock_code: 종목 코드
- predicted_at: 예측 생성 일시

# 예측 정보 (스냅샷)
- predicted_target_price: 목표가
- predicted_support_price: 손절가
- predicted_base_price: 기준가
- predicted_confidence: 신뢰도

# 실제 결과
- actual_high_1d, actual_low_1d, actual_close_1d
- actual_high_5d, actual_low_5d, actual_close_5d
- target_achieved: 목표가 달성 여부 (boolean)
- target_achieved_days: 달성 소요일
- support_breached: 손절가 이탈 여부

# 자동 점수 (0-100)
- target_accuracy_score
- timing_score
- risk_management_score

# 사람 평가 (1-5)
- human_rating_quality: 분석 품질
- human_rating_usefulness: 실용성
- human_rating_overall: 종합 만족도
- human_evaluated_by: 평가자
- human_evaluated_at: 평가 일시

# 최종 점수
- final_score: (자동 70% + 사람 30%)
- evaluated_at, created_at
```

### `daily_model_performance` 테이블
```sql
- id: PK
- model_id: 모델 ID
- date: 평가 날짜
- total_predictions: 총 예측 건수
- evaluated_count: 평가 완료 건수
- human_evaluated_count: 사람 평가 건수

# 평균 점수
- avg_final_score
- avg_auto_score
- avg_human_score
- avg_target_accuracy
- avg_timing_score
- avg_risk_management

# 성과 지표
- target_achieved_rate: 목표 달성률 (%)
- support_breach_rate: 손절가 이탈률 (%)

- created_at, updated_at
- UNIQUE(model_id, date)
```

### `evaluation_history` 테이블
```sql
- id: PK
- evaluation_id: FK
- old_human_rating_quality, old_human_rating_usefulness, old_human_rating_overall
- new_human_rating_quality, new_human_rating_usefulness, new_human_rating_overall
- old_final_score, new_final_score
- modified_by: 수정자
- modified_at: 수정 일시
- reason: 수정 사유 (선택)
```

## 🎨 UI/UX Design

### 화면 구조
```
📈 평가 메뉴 (신규 추가)
  ├─ 📋 평가 대기 목록 (Today's Queue)
  ├─ 📅 Daily 평가 내역 (Historical View)
  ├─ 📊 모델 성능 대시보드 (Overview)
  └─ 🔬 모델 상세 분석 (Deep Dive)
```

### 핵심 UX 원칙
1. **평가자 피로 최소화**: Priority 1-2 종목만 사람 평가 (전체의 30%)
2. **빠른 평가**: 1-5점 척도로 30초 이내 평가 완료
3. **투명성**: 자동 평가 결과를 먼저 보여주고 사람 평가 진행
4. **유연성**: 평가 완료 후에도 수정 가능 (이력 추적)
5. **컨텍스트 제공**: 예측/실제 결과를 한눈에 비교

## 🔄 Workflow

### Daily 평가 워크플로우
```
매일 16:00 - 자동 평가 배치 실행
  ├─ D-1일 Investment Report 조회
  ├─ 오늘 실제 주가 데이터 수집
  ├─ 목표가/손절가 달성 여부 판단
  ├─ 자동 점수 계산 (0-100)
  └─ model_evaluations 테이블 저장

매일 17:00 - Daily 집계 배치 실행
  ├─ 오늘 평가 데이터 집계
  ├─ 모델별 평균 점수 계산
  └─ daily_model_performance 테이블 업데이트

사람 평가 (수시)
  ├─ Priority 1-2 종목 평가 대상 선별
  ├─ 평가 UI에서 1-5점 평가
  ├─ 최종 점수 재계산 (자동 70% + 사람 30%)
  └─ 평가 완료 후에도 수정 가능
```

## 📈 Timeline

**총 예상 기간: 2-3 weeks**

| Week | Phase | Stories | Deliverables |
|------|-------|---------|--------------|
| Week 1 | 기본 인프라 | STORY-004, 005, 006 | DB 스키마, 자동 평가 배치 |
| Week 2 | 사람 평가 | STORY-007, 008 | 평가 API, 평가 UI |
| Week 3 | 대시보드 | STORY-009, 010 | 리더보드, 상세 분석 |

## 🚀 Next Steps

1. ✅ **PRD 승인**: 사용자 확인 및 승인
2. **PM Agent 호출**: Epic → Story 분해
3. **Dev Agent 할당**: Story별 구현 시작

## 📚 References

- 리서치 리포트: [위 대화 내용 참조]
- 기존 시스템: `backend/db/models/prediction.py`, `backend/llm/investment_report.py`
- 주가 데이터: `backend/db/models/stock.py`, `backend/crawlers/stock_crawler.py`
- A/B 테스트: `backend/db/models/ab_test_config.py`

## 🎯 Success Criteria

### MVP 완성 조건
- [x] DB 스키마 생성 및 마이그레이션 완료
- [x] 자동 평가 배치 작업 정상 동작
- [x] 사람 평가 UI 완성 및 테스트
- [x] 모델 리더보드 표시
- [x] 최소 7일간 평가 데이터 축적

### 운영 준비 조건
- [x] 자동 배치 작업 에러 핸들링
- [x] 평가 수정 이력 추적
- [x] 대시보드 성능 최적화 (1초 이내 로딩)
- [x] 모바일 반응형 UI
