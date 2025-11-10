# 📋 Story Board - KIS API Migration

## 📊 Current Sprint Status

### 🎯 In Progress (1)
- **STORY-003.2-DAILY-PRICE-COLLECTOR.md** - KIS API 일봉 수집기 구현
  - Status: Migration 완료, 수집기 구현 중
  - Priority: ⭐⭐⭐⭐⭐
  - Effort: 5-7일

### ✅ Done (1)
- **STORY-003.1-KIS-API-AUTHENTICATION.md** - KIS API 인증 시스템
  - Completed: 2025-01-08
  - Key Achievements:
    - OAuth 2.0 인증 구현
    - Token 자동 갱신
    - Rate Limiting (모의투자 5req/s)
    - 테스트 통과

### 📚 Backlog (13)

#### Epic 003: Phase 1 - 기본 인프라 (2/4 완료)
- ✅ STORY-003.1 - API 인증
- 🔄 STORY-003.2 - 일봉 수집기 (In Progress)
- 📋 STORY-003.3 - 분봉 수집기
- 📋 STORY-003.4 - FDR/KIS 검증

#### Epic 004: Phase 2 - 보조 지표 (0/4)
- 📋 STORY-004.1 - 투자자 매매 데이터
- 📋 STORY-004.2 - 재무제표 수집
- 📋 STORY-004.3 - LLM 프롬프트 통합
- 📋 STORY-004.4 - A/B 테스트

#### Epic 005: Phase 3 - 실시간 데이터 (0/4)
- 📋 STORY-005.1 - WebSocket 실시간 체결가
- 📋 STORY-005.2 - 실시간 호가
- 📋 STORY-005.3 - 급변 감지 알림
- 📋 STORY-005.4 - LLM 최적화

#### Epic 006: Phase 4 - 정리 및 최적화 (0/4)
- 📋 STORY-006.1 - FDR 제거
- 📋 STORY-006.2 - KONEX/OTC 조사
- 📋 STORY-006.3 - 품질 모니터링
- 📋 STORY-006.4 - 성능 튜닝

### 🗄️ Archive (28)
기존 구현 완료된 스토리들 (1.x, 2.x, STORY-00x 시리즈)

---

## 📂 Folder Structure

```
docs/stories/
├── README.md              # 이 파일 (스토리 보드)
├── in-progress/           # 현재 작업중인 스토리
├── done/                  # 완료된 스토리
├── backlog/               # 대기중인 스토리 (우선순위순)
└── archive/               # 기존 완료/사용안함 스토리
```

---

## 🔄 Story Workflow

1. **Backlog** → 준비된 스토리, 우선순위대로 대기
2. **In Progress** → 현재 개발중 (동시에 1-2개만)
3. **Done** → 완료 및 검증 완료
4. **Archive** → 오래된 또는 사용안함

---

## 📝 Story Naming Convention

- **KIS API Migration**: `STORY-00X.Y-FEATURE-NAME.md`
  - 00X: Epic 번호 (003-006)
  - Y: Epic 내 순서 (1-4)
  - 예: `STORY-003.2-DAILY-PRICE-COLLECTOR.md`

---

## 🎯 Current Sprint Goal

**Epic 003 완료 (Phase 1 기본 인프라)**
- Target: 2025-01-31
- Progress: 2/4 (50%)
- Next Up: Story 003.2 완료 후 → 003.3 분봉 수집기

---

**Last Updated**: 2025-01-08
**Scrum Master**: Bob 🏃
