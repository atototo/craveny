# Sprint Change Proposal - LLM 예측 품질 개선

**Date:** 2025-11-02
**Author:** Sarah (PO Agent)
**Status:** Proposed
**Epic:** Epic 2 - LLM 기반 예측 및 알림 시스템

---

## 📋 Executive Summary

**Problem Identified:**
사용자가 현재 LLM 예측 결과를 신뢰할 수 없음. NFR8 목표("사용자 만족도 80%") 미달.

**Proposed Solution:**
새로운 Story 2.9 생성하여 LLM 예측 품질을 체계적으로 개선.

**Impact:**
- **Epic 2 상태**: 기능 완료 → 품질 개선 단계
- **관련 Stories**: Story 2.2 (완료 유지), Story 2.6 (간접 영향), Dashboard UI (간접 영향)
- **Timeline**: Phase 1 (1-2일), Phase 2 (3-5일), Phase 3 (Optional)

---

## 1. Issue Discovery

### 1.1 문제 발견 경위

**Date:** 2025-11-02
**Source:** 사용자 테스트 (개발자 본인)

**User Feedback:**
> "신뢰도 점수가 의미가 없어 이걸 보고 내가 투자를 할건데 근거도 모르겠고, 종합 지표도 부족한거 같아. 개발자인 내가 그냥 믿을 수 없어."

### 1.2 Issue Type

- [x] **Quality Issue** - 기능은 구현되었으나 품질 목표 미달
- [ ] Fundamental misunderstanding
- [ ] New requirements
- [ ] External dependency change

### 1.3 Core Problems

1. **신뢰도 투명성 부재**
   - 문제: 신뢰도 85%라고 표시되지만, 왜 85%인지 설명 없음
   - 영향: 사용자가 예측을 신뢰할 수 없음
   - 증거: "신뢰도 점수가 의미가 없어"

2. **예측 근거 불충분**
   - 문제: 과거 유사 뉴스만 참조, 맥락 정보 부족
   - 영향: 투자 결정에 필요한 정보 부족
   - 증거: "근거도 모르겠고"

3. **종합 지표 부족**
   - 문제: 시장 상황, 종목 특성 정보 누락
   - 영향: 단편적 예측만 제공, 종합 판단 불가
   - 증거: "종합 지표도 부족한거 같아"

---

## 2. Epic & Story Impact Assessment

### 2.1 Current Epic Structure

**Epic 1: 데이터 수집 및 저장 인프라**
- Status: ✅ Completed
- Impact: 없음

**Epic 2: LLM 기반 예측 및 알림 시스템**
- Status: ⚠️ Functionally Complete, Quality Issue Identified
- Impact: Story 2.2 품질 개선 필요

### 2.2 Affected Stories

| Story | Status | Impact | Action Required |
|-------|--------|--------|-----------------|
| **Story 2.2** (LLM Prompt) | Completed | 🔴 High | 품질 개선 (새 Story 2.9로 분리) |
| **Story 2.6** (Telegram Bot) | Completed | 🟡 Medium | 예측 품질 개선 후 템플릿 검토 |
| **Dashboard UI** | Completed | 🟡 Medium | UI 변경 불필요, 데이터만 개선 |
| Stories 2.1, 2.3-2.5, 2.7-2.8 | Completed | 🟢 Low | 변경 불필요 |

### 2.3 Epic Continuation Assessment

**Question 1:** Is there a current Epic this work belongs to?
- **Answer:** Yes, Epic 2 (LLM 기반 예측 및 알림 시스템)

**Question 2:** Can the Epic continue or is it blocked?
- **Answer:** Epic은 계속 진행 가능. 기능은 완료되었고, 품질 개선은 별도 Story로 처리.

**Question 3:** Are there related stories that are affected?
- **Answer:** Yes
  - Story 2.6 (Telegram Bot): 알림 메시지에 개선된 예측 데이터 반영
  - Dashboard UI: UI는 변경 없이 백엔드 데이터만 개선

---

## 3. Artifact Conflict Analysis

### 3.1 PRD Review

**Relevant Requirements:**

**FR8-FR9 (LLM 예측):**
- FR8: "영향도 점수(0~10), 예상 변동폭(%), 영향 지속 기간(일)을 출력"
- FR9: "예측 근거를 자연어로 생성"
- **Status:** ✅ Implemented, ⚠️ Quality Issue

**NFR8 (사용자 만족도):**
- "LLM 분석 품질에 대한 사용자 평가 '도움됨'이 80% 이상이어야 한다"
- **Status:** ❌ **Not Met** - 개발자(사용자) 본인도 신뢰 불가

**Conflict Type:** ❌ **Critical Quality Gap**
- 기능 요구사항은 구현되었으나 비기능 요구사항(품질) 미달

### 3.2 Architecture Review

**Current Architecture:**
- AI/ML: OpenAI GPT-4o-mini, text-embedding-3-small (768d)
- Data Pipeline: APScheduler (크롤링), Celery (비동기 분석)
- Storage: PostgreSQL, Milvus, Redis

**Conflict Assessment:**
- ✅ **No Architectural Changes Required**
- Improvement Area: `backend/llm/predictor.py` logic enhancement
- Data Enhancement: Market indices, stock fundamentals

**Impact:** Low - Logic-level improvements only

### 3.3 Frontend Spec Review

**Current UI:**
- Dashboard: 예측 결과 표시 (신뢰도, 근거, 기간별 예측)
- Telegram: 알림 메시지 템플릿

**Conflict Assessment:**
- ✅ **No UI Changes Required**
- UI는 올바르게 구현됨, 백엔드 데이터 품질만 개선
- User confirmation: "대시보드 UI 다 영향이 있어" → 데이터 품질 영향

**Impact:** Low - Backend data quality improvement only

---

## 4. Path Forward Evaluation

### Option 1: Direct Adjustment (Story 2.2 내에서 수정)
- **Pros:** 빠른 수정
- **Cons:** 범위 혼재 (기본 구현 + 품질 개선)
- **Risk:** Medium

### Option 2: Rollback & Fix (Epic 2 일부 롤백)
- **Pros:** 완전한 재작업
- **Cons:** 기존 작업 손실, 시간 낭비
- **Risk:** High

### Option 3: Re-scoping (새 Story 생성) ⭐ **SELECTED**
- **Pros:**
  - 명확한 범위 분리 (기본 구현 vs 품질 개선)
  - 기존 작업 보존 (Story 2.2는 "완료" 유지)
  - 추적 가능성 향상 (품질 개선 독립 관리)
- **Cons:** 추가 Story 관리 필요
- **Risk:** Low

**User Decision:** "3번이 좋을거 같아"

---

## 5. Proposed Changes

### 5.1 New Story Creation

**Story ID:** 2.9
**Title:** LLM 예측 품질 개선
**Epic:** 2 - LLM 기반 예측 및 알림 시스템
**Type:** Quality Improvement
**Priority:** High

**File Created:** `/docs/stories/2.9.llm-quality-improvement.md`

### 5.2 Story Scope

**3-Phase Approach:**

**Phase 1 - Immediate (1-2일):** ⚡ Priority 1
- 프롬프트 개선 (공시 정보 포함)
- 신뢰도 계산 로직 투명화
- 예측 근거 구체화 (유사 패턴 통계)
- **Goal:** 즉시 체감 가능한 품질 개선

**Phase 2 - Data Enhancement (3-5일):** 📊 Priority 2
- 시장 지수 수집 (KOSPI/KOSDAQ)
- 섹터 지수 수집
- 종목 펀더멘털 (시가총액, PER, PBR)
- 시계열 확장 (T+2, T+10, T+20일)
- **Goal:** 종합적 투자 판단 지원

**Phase 3 - Advanced (Optional):** 🚀 Priority 3
- Multi-model 앙상블 (GPT-4o + Claude)
- 피드백 루프 (예측 vs 실제 비교)
- 자동 프롬프트 최적화
- **Goal:** 지속적 개선 시스템

### 5.3 Acceptance Criteria

**AC1:** 신뢰도 계산 로직 투명화
- 신뢰도 구성 요소 3가지 이상 제공
- 예: "유사 뉴스 5건, 평균 유사도 92%, 패턴 일관성 85%"

**AC2:** 예측 근거 강화
- 종목 특성 포함 (시가총액, 섹터, 실적)
- 공시 정보 포함 (DART 데이터)
- 과거 패턴 통계 (평균/최대/최소 변동률)

**AC3:** 종합 지표 추가
- 시장 맥락 (KOSPI/KOSDAQ 지수)
- 섹터 동향
- 시계열 확장 (T+1, T+2, T+10, T+20일)

**AC4:** 프롬프트 재설계
- JSON 응답 스키마 확장 (confidence_breakdown, similar_patterns, market_context)

**AC5:** 품질 검증
- NFR8 목표 달성 (사용자 만족도 확인)
- 10건 실제 뉴스 테스트

---

## 6. Impact Analysis

### 6.1 Code Changes

**Primary File:**
- `backend/llm/predictor.py` - LLM 프롬프트 및 로직 개선

**Secondary Files:**
- `backend/llm/prompts/` - 프롬프트 템플릿 분리 (optional)
- `backend/db/models/` - 새 테이블 모델 (market_indices, sector_indices)
- `backend/crawlers/` - 시장/섹터 지수 수집 스크립트

**No Changes:**
- Frontend UI (Dashboard, Telegram templates)
- Architecture (GPT-4o, Milvus, Redis 유지)
- API contracts (내부 데이터 구조만 확장)

### 6.2 Database Changes

**New Tables (Phase 2):**
```sql
-- 시장 지수
CREATE TABLE market_indices (
    id SERIAL PRIMARY KEY,
    index_name VARCHAR(50),  -- 'KOSPI', 'KOSDAQ'
    date TIMESTAMP,
    close FLOAT,
    change_pct FLOAT
);

-- 섹터 지수
CREATE TABLE sector_indices (
    id SERIAL PRIMARY KEY,
    sector_name VARCHAR(100),
    date TIMESTAMP,
    close FLOAT,
    change_pct FLOAT
);

-- 종목 펀더멘털
ALTER TABLE stocks ADD COLUMN market_cap BIGINT;
ALTER TABLE stocks ADD COLUMN per FLOAT;
ALTER TABLE stocks ADD COLUMN pbr FLOAT;
```

**Schema Extension:**
```sql
-- 시계열 확장
ALTER TABLE news_stock_match ADD COLUMN price_change_2d FLOAT;
ALTER TABLE news_stock_match ADD COLUMN price_change_10d FLOAT;
ALTER TABLE news_stock_match ADD COLUMN price_change_20d FLOAT;
```

### 6.3 Timeline & Effort

| Phase | Duration | Effort | Priority |
|-------|----------|--------|----------|
| Phase 1 | 1-2일 | Medium | High |
| Phase 2 | 3-5일 | High | Medium |
| Phase 3 | TBD | High | Low (Optional) |

**Total Estimate:** 4-7일 (Phase 1+2), Phase 3는 별도 평가

---

## 7. Risk Assessment

### Risk 1: API 비용 증가
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:**
  - Redis 캐싱 강화 (TTL 연장)
  - 프롬프트 압축 기법
  - 비용 모니터링

### Risk 2: 응답 시간 증가
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:**
  - 데이터 사전 로드 (메모리 캐시)
  - 비동기 병렬 조회
  - NFR1 유지 (5분 이내)

### Risk 3: 데이터 수집 실패
- **Likelihood:** Low
- **Impact:** Low
- **Mitigation:**
  - Phase 1은 데이터 의존성 없음
  - Phase 2는 단계적 추가

**Overall Risk:** 🟡 Medium (Manageable)

---

## 8. Success Metrics

### 정량적 지표
- [ ] 신뢰도 구성 요소 3개 이상 제공
- [ ] 유사 패턴 통계 제공 (평균/최대/최소)
- [ ] 시계열 예측 4개 시점 이상
- [ ] 시장/섹터 맥락 정보 포함

### 정성적 지표
- [ ] NFR8 달성: 사용자(개발자) "신뢰 가능" 평가
- [ ] 예측 근거가 투자 결정에 충분
- [ ] Telegram 알림이 actionable insights 제공

**Target:** NFR8 목표 80% 사용자 만족도 달성

---

## 9. Dependencies

### Existing System
- ✅ Story 2.1: 벡터 유사도 검색 (재사용)
- ✅ Story 2.2: 기본 LLM 프롬프트 (개선)
- ⚠️ Story 1.4: 뉴스 크롤러 (DART 데이터 활용)
- ⚠️ Story 1.5: 주가 수집 (시계열 확장)

### New Data Sources
- KOSPI/KOSDAQ 지수 (새 수집)
- 섹터 지수 (새 수집)
- 종목 펀더멘털 (새 수집)

---

## 10. Recommendation

### Proposed Action: **APPROVE & PROCEED**

**Rationale:**
1. ✅ **명확한 문제 정의**: NFR8 미달, 사용자 신뢰 부족
2. ✅ **충돌 없음**: Architecture, Frontend 변경 불필요
3. ✅ **Low Risk**: Phase 1은 로직 레벨 개선만
4. ✅ **High Value**: 즉시 체감 가능한 품질 향상
5. ✅ **User Alignment**: "3번이 좋을거 같아" (Re-scoping 선택)

**Next Steps:**
1. ✅ Story 2.9 생성 완료 (`/docs/stories/2.9.llm-quality-improvement.md`)
2. ⏳ Phase 1 작업 시작 (프롬프트 개선, 신뢰도 투명화)
3. ⏳ 10건 테스트 뉴스로 검증
4. ⏳ NFR8 목표 달성 확인
5. ⏳ Phase 2 착수 여부 결정

---

## 11. User Approval

**Status:** ⏳ Pending User Review

**Questions for User:**
1. Phase 1 (1-2일) 즉시 시작해도 될까요?
2. Phase 2 (데이터 보강)는 Phase 1 완료 후 결정할까요?
3. 다른 우선순위 작업이 있나요?

**User Response:**
_To be filled_

---

## Appendices

### A. Story 2.9 Full Specification
See: `/docs/stories/2.9.llm-quality-improvement.md`

### B. Related Documents
- PRD: `/docs/prd.md`
- Architecture: `/docs/architecture.md`
- Story 2.2: `/docs/stories/2.2.llm-prompt-rag.md`
- Epic 2: `/docs/prd/epic-2-llm-prediction-notifications.md`

### C. Change History

| Date | Author | Change |
|------|--------|--------|
| 2025-11-02 | Sarah (PO) | Initial Sprint Change Proposal created |

---

**END OF SPRINT CHANGE PROPOSAL**
