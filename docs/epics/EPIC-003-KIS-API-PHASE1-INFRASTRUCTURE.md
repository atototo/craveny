# Epic 003: 한국투자증권 API 기초 인프라 구축 (Phase 1)

**Status**: 📝 Draft
**Priority**: 🔴 High
**Estimated Duration**: 3-4 weeks (16-23 dev days)
**Dependencies**: None
**Related Research**: `docs/KIS_API_MIGRATION_RESEARCH.md`

---

## Epic Goal

FinanceDataReader에서 한국투자증권 Open API로 전환하기 위한 기초 인프라를 구축하고, **일봉 및 1분봉 데이터 수집**을 안정적으로 수행하여 실시간 장중 추적과 향후 고급 데이터(외국인/기관 매매, 재무제표 등) 수집의 토대를 마련한다.

---

## Executive Summary

### Why This Matters

**현재 문제점:**
- FinanceDataReader는 일봉 데이터만 제공 → 장중 실시간 추적 불가
- 외국인/기관 매매, 재무제표 등 보조 지표 부재
- 예측 정확도 향상에 필요한 데이터 부족

**한투 API 전환 시 얻는 것:**
- ✅ **완전 무료** (API 사용료 없음)
- ✅ **1분봉 데이터** → 장중 실시간 추적 가능 ⭐⭐⭐⭐⭐
- ✅ **외국인/기관 매매** (Phase 2) → 예측 정확도 +15~25% 향상 예상
- ✅ **재무제표** (Phase 2) → 기본적 분석 가능
- ✅ **실시간 WebSocket** (Phase 3) → 장중 리포트 동적 업데이트

**Phase 1의 목표:**
- 한투 API 인증 및 기본 클라이언트 구현
- 일봉 데이터 수집 (FDR 대체)
- **1분봉 데이터 수집 및 DB 누적** ⭐ 핵심!
- FDR과의 정합성 검증 (99.5% 이상)

---

## Existing System Context

### Current Architecture

**데이터 소스**: FinanceDataReader (FDR)

**수집 데이터**:
- 일봉 OHLCV만 (Open, High, Low, Close, Volume)
- 과거 90일 (3개월)

**수집 대상**:
- 코스피/코스닥 대형주 50개 종목

**수집 주기**:
- 1분마다 (장중 9:00~15:30)

**저장 위치**:
- PostgreSQL `stock_prices` 테이블

**Technology Stack**:
- Python 3.11+
- FastAPI
- PostgreSQL 15
- FinanceDataReader
- APScheduler (스케줄 관리)
- Pandas (데이터 처리)

### Integration Points

**주요 파일:**
- `backend/crawlers/stock_crawler.py` - 주가 수집 로직
- `backend/db/models/stock.py` - Stock, StockPrice 모델
- `backend/db/session.py` - DB 세션 관리
- `backend/db/base.py` - SQLAlchemy Base

**주요 한계:**
- ❌ 일봉 데이터만 가능
- ❌ 장중 실시간 추적 불가
- ❌ 외국인/기관 매매 데이터 없음
- ❌ 재무제표 데이터 없음

---

## Enhancement Details

### What's Being Added

#### 1. 한국투자증권 API 클라이언트

**파일**: `backend/clients/kis_client.py`

**기능:**
- OAuth 2.0 인증 (APP Key + APP Secret)
- 토큰 발급 및 자동 갱신 (만료 1시간 전)
- REST API 호출 래퍼 함수
- Rate Limiting (초당 5회, 모의투자 기준)
- Retry 로직 (exponential backoff, 최대 3회)
- Circuit Breaker 패턴 (연속 실패 5회 시 일시 중단)
- 로깅 및 모니터링

**환경 변수** (`.env`):
```env
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_ACCOUNT_NUMBER=your_mock_account
```

#### 2. 일봉 데이터 수집기

**기능:**
- 한투 API로 일봉 OHLCV 조회
- TR ID: `FHKST01010400` (국내주식 일봉 조회)
- FDR과 동일한 데이터 형식
- PostgreSQL `stock_prices` 테이블 저장

**DB 스키마 확장:**
```sql
ALTER TABLE stock_prices ADD COLUMN source VARCHAR(20) DEFAULT 'FDR';
CREATE INDEX idx_stock_prices_source ON stock_prices(source);
```

#### 3. 1분봉 데이터 수집기 ⭐ **핵심 추가**

**기능:**
- 장중 1분마다 1분봉 OHLCV 수집
- 당일 데이터 30건씩 조회 (한투 API 제한)
- 매일 DB에 누적 → 과거 분봉 데이터 확보
- Pandas resample()로 3/5/10/30/60분봉 생성 가능

**DB 스키마 (신규):**
```sql
CREATE TABLE stock_prices_minute (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    datetime TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume BIGINT,
    source VARCHAR(20) DEFAULT 'KIS',
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_minute_stock_datetime (stock_code, datetime),
    UNIQUE KEY uk_stock_datetime (stock_code, datetime)
);
```

**수집 전략:**
- 장중 9:00~15:30, 1분마다 실행
- 50개 종목 × 390분 = 19,500건/일
- 병렬 처리 (10개 종목씩 배치)
- 실패 시 다음 주기에 재시도

#### 4. 데이터 검증 시스템

**기능:**
- FDR vs 한투 API 일봉 데이터 정합성 비교
- 차이 허용 오차: ±0.5%
- 검증 리포트 생성 (CSV)
- 로그 기록 및 Slack 알림 (optional)

**검증 범위:**
- 50개 종목 × 최근 30일 = 1,500건
- 정합성 목표: ≥ 99.5%

---

## How It Integrates

### System Architecture

```
┌─────────────────────────────────────────────┐
│         APScheduler (Cron Jobs)             │
├─────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐      │
│  │ Daily Job    │    │ Minute Job   │      │
│  │ (일봉 수집)   │    │ (분봉 수집)   │      │
│  └──────┬───────┘    └──────┬───────┘      │
│         │                    │              │
│         ▼                    ▼              │
│  ┌──────────────────────────────────┐      │
│  │      StockCrawler (Extended)     │      │
│  ├──────────────────────────────────┤      │
│  │  - FDR Client (기존)             │      │
│  │  - KIS Client (신규) ⭐          │      │
│  └──────┬───────────────────┬───────┘      │
│         │                    │              │
│         ▼                    ▼              │
│  ┌─────────────┐      ┌─────────────┐      │
│  │stock_prices │      │stock_prices │      │
│  │   (일봉)     │      │  _minute    │      │
│  │             │      │   (분봉) ⭐  │      │
│  └─────────────┘      └─────────────┘      │
└─────────────────────────────────────────────┘
```

### Integration Flow

1. **초기 설정** (Story 1)
   - API 가입 → Key 발급
   - `.env` 설정
   - `KISClient` 클래스 생성

2. **일봉 수집** (Story 2)
   - `StockCrawler` 확장
   - FDR과 병행 수집 (Dual-run)
   - `source` 컬럼으로 구분

3. **분봉 수집** (Story 3)
   - 신규 테이블 생성
   - APScheduler 스케줄 추가
   - 장중 1분마다 자동 실행

4. **검증** (Story 4)
   - FDR vs 한투 API 비교
   - 정합성 99.5% 달성 시 Phase 2 진행

---

## Stories

### Story 1: 한국투자증권 API 인증 및 설정 관리

**Priority**: 🔴 Critical
**Estimated**: 3-5 dev days

**Description:**
한국투자증권 계좌 개설, API Key 발급, 환경 변수 설정, OAuth 토큰 발급/갱신 로직을 구현하여 API 호출의 기초를 마련한다.

**Tasks:**
- [ ] 한국투자증권 모의투자 계좌 신청
- [ ] KIS Developers 가입 및 APP Key/Secret 발급
- [ ] `.env` 파일에 API 키 저장
- [ ] `backend/clients/kis_client.py` 생성 (KISClient 클래스)
- [ ] OAuth 토큰 발급 API 구현 (`/oauth2/tokenP`)
- [ ] 토큰 자동 갱신 로직 구현 (만료 1시간 전)
- [ ] Rate Limiting 구현 (초당 5회, 모의투자 기준)
- [ ] Retry 로직 구현 (exponential backoff, 최대 3회)
- [ ] Circuit Breaker 패턴 적용 (연속 실패 5회 시 일시 중단)
- [ ] 단위 테스트 작성 (`tests/unit/clients/test_kis_client.py`)
- [ ] 문서 작성 (`docs/KIS_API_INTEGRATION.md`)

**Acceptance Criteria:**
- [ ] 모의투자 계좌 개설 완료
- [ ] APP Key, APP Secret 발급 및 `.env` 저장
- [ ] `KISClient.get_token()` 호출 시 access_token 정상 발급
- [ ] 토큰 만료 시 자동 갱신 확인 (로그 확인)
- [ ] Rate Limiting 작동 (초당 5회 초과 시 대기)
- [ ] API 실패 시 3회 재시도 확인
- [ ] 연속 5회 실패 시 Circuit Breaker 작동 확인
- [ ] 단위 테스트 커버리지 ≥ 80%

**Dependencies**: None

---

### Story 2: 한투 API 일봉 데이터 수집기 구현

**Priority**: 🔴 Critical
**Estimated**: 5-7 dev days

**Description:**
한국투자증권 API를 사용하여 일봉 OHLCV 데이터를 수집하고, 기존 `stock_prices` 테이블에 저장하는 기능을 구현한다.

**Tasks:**
- [ ] DB 마이그레이션: `stock_prices` 테이블에 `source VARCHAR(20)` 컬럼 추가
- [ ] `KISClient.get_daily_price()` 메서드 구현
  - TR ID: `FHKST01010400` (국내주식 일봉 조회)
  - 시장 구분: `J` (주식)
- [ ] 5~10개 테스트 종목으로 수집 테스트
- [ ] OHLCV 파싱 및 검증
- [ ] 에러 핸들링 (API 실패, Rate Limit 초과, 네트워크 오류)
- [ ] 로깅 구현 (`logs/kis_daily_collector.log`)
- [ ] `StockCrawler` 클래스 확장 (한투 API 통합)
- [ ] 통합 테스트 작성 (`tests/integration/test_kis_daily_collector.py`)

**Acceptance Criteria:**
- [ ] `stock_prices` 테이블 스키마 변경 완료 (migration 스크립트)
- [ ] 삼성전자(005930) 일봉 데이터 정상 조회
- [ ] OHLCV 값이 정확하게 파싱됨 (타입 검증)
- [ ] `source='KIS'`로 DB 저장 확인
- [ ] API 실패 시 재시도 로직 작동
- [ ] Rate Limit 초과 시 대기 후 재시도
- [ ] 평균 응답 시간 < 500ms (10개 종목 기준)
- [ ] 로그 파일 생성 확인

**Dependencies**: Story 1

---

### Story 3: 1분봉 데이터 수집기 및 DB 누적 시스템 구현 ⭐

**Priority**: 🔴 Critical
**Estimated**: 5-7 dev days

**Description:**
장중 실시간 추적을 위해 1분봉 OHLCV 데이터를 수집하고, 매일 DB에 누적하여 과거 분봉 데이터를 확보한다.

**Tasks:**
- [ ] DB 마이그레이션: `stock_prices_minute` 테이블 생성
- [ ] `KISClient.get_minute_price()` 메서드 구현
  - TR ID 확인 (API 문서 참조)
  - 당일 1분봉 30건씩 조회
- [ ] APScheduler 스케줄 추가:
  - 장중 9:00~15:30, 1분마다 실행
  - 50개 종목 순회 수집
- [ ] 병렬 처리 로직 (10개 종목씩 배치)
- [ ] Pandas resample() 유틸 함수 작성
  - 1분봉 → 3분/5분/10분/30분/60분봉 변환
- [ ] 에러 핸들링 및 로깅 (`logs/kis_minute_collector.log`)
- [ ] 통합 테스트 작성

**Acceptance Criteria:**
- [ ] `stock_prices_minute` 테이블 생성 완료
- [ ] 삼성전자(005930) 1분봉 데이터 정상 조회
- [ ] 장중 1분마다 자동 수집 확인 (APScheduler 로그)
- [ ] 30건씩 조회 제한 확인 (API 응답 검증)
- [ ] DB에 누적 저장 확인 (중복 체크: UNIQUE 제약)
- [ ] Pandas resample() 함수 작동 확인 (1분봉 → 5분봉 변환 테스트)
- [ ] 50개 종목 × 390분 = 19,500건 수집 성공 (1일 기준)
- [ ] 수집 성공률 ≥ 98%
- [ ] 로그 파일 생성 확인

**Dependencies**: Story 1

**Technical Notes:**

**1분봉 수집 최적화 전략:**

1. **병렬 처리**:
   - 50개 종목을 10개씩 배치
   - 각 배치마다 0.2초 대기 (초당 5회 제한 준수)

2. **우선순위 큐**:
   - 시가총액 상위 종목 우선 수집
   - 실패 종목은 다음 주기에 재시도

3. **DB 인덱싱**:
   - `(stock_code, datetime)` 복합 인덱스
   - UNIQUE 제약으로 중복 방지

4. **Pandas Resample 예제**:
   ```python
   import pandas as pd

   # 1분봉 → 5분봉 변환
   df = pd.read_sql(
       "SELECT * FROM stock_prices_minute WHERE stock_code='005930'",
       engine
   )
   df['datetime'] = pd.to_datetime(df['datetime'])
   df.set_index('datetime', inplace=True)

   df_5min = df.resample('5T').agg({
       'open': 'first',
       'high': 'max',
       'low': 'min',
       'close': 'last',
       'volume': 'sum'
   })
   ```

---

### Story 4: FDR vs 한투 API 데이터 검증 및 Dual-run 모드

**Priority**: 🟡 High
**Estimated**: 3-4 dev days

**Description:**
FinanceDataReader와 한투 API에서 동시에 일봉 데이터를 수집하여 정합성을 비교하고, 차이가 발생하면 로그를 기록하여 데이터 품질을 검증한다.

**Tasks:**
- [ ] `scripts/validate_kis_data.py` 생성
- [ ] FDR과 한투 API에서 동일 종목, 동일 날짜 데이터 수집
- [ ] OHLCV 값 비교 (허용 오차: ±0.5%)
- [ ] 차이 발견 시:
  - 로그 기록 (종목, 날짜, FDR 값, 한투 값, 차이율)
  - Slack 알림 (optional)
- [ ] 검증 리포트 생성 (CSV: `data/kis_validation_report.csv`)
- [ ] 50개 종목 × 최근 30일 = 1,500건 검증
- [ ] 정합성 통계 계산 (평균 차이율, 최대 차이율)

**Acceptance Criteria:**
- [ ] FDR과 한투 API에서 동일 데이터 수집 확인
- [ ] 1,500건 중 정합성 ≥ 99.5% (차이 < 8건)
- [ ] 차이 발생 시 로그 파일 생성 (`logs/kis_validation.log`)
- [ ] 검증 리포트 CSV 생성
- [ ] 통계 출력:
  - 총 검증 건수
  - 정합성 비율 (%)
  - 평균 차이율 (%)
  - 최대 차이율 및 해당 종목
- [ ] **정합성 99.5% 이상 달성 시 Phase 2 진행 승인** ✅

**Dependencies**: Story 2

---

## Compatibility Requirements

- [x] 기존 `stock_prices` 테이블 구조 유지 (컬럼 추가만)
- [x] FDR 코드는 유지 (Dual-run 모드)
- [x] 기존 APScheduler 스케줄 변경 없음
- [x] 기존 API 엔드포인트 영향 없음
- [x] 성능 저하 없음 (병렬 수집으로 대응)

---

## Risk Mitigation

### Primary Risks

| Risk | Severity | Probability | Mitigation |
|------|----------|-------------|------------|
| 한투 API 데이터 불일치 | 🟡 Medium | 30% | Dual-run 모드, 검증 단계 (Story 4) |
| API 장애로 수집 실패 | 🟡 Medium | 20% | Circuit Breaker, FDR Fallback |
| Rate Limit 초과 | 🟢 Low | 10% | Rate Limiting, Retry 로직 |
| 1분봉 수집 실패 | 🟡 Medium | 25% | 재시도, 우선순위 큐 |
| DB 성능 저하 | 🟢 Low | 15% | 인덱싱, 배치 삽입 |

### Mitigation Strategies

**1. Dual-run 모드**
- FDR과 한투 API 동시 수집
- `source` 컬럼으로 구분
- 검증 완료 전까지 FDR 백업 유지

**2. Circuit Breaker 패턴**
- 연속 5회 실패 시 API 호출 일시 중단
- 1분 후 재시도
- FDR로 자동 Fallback

**3. 1분봉 수집 최적화**
- 병렬 처리 (배치 크기: 10개)
- 우선순위 큐 (시가총액 기준)
- 실패 재시도 (다음 주기)

**Rollback Plan:**

1. **완전 롤백** (최악의 경우):
   ```sql
   DELETE FROM stock_prices WHERE source='KIS';
   DROP TABLE stock_prices_minute;
   ```
2. 한투 API 클라이언트 비활성화 (`.env`에서 주석 처리)
3. FDR로 100% 복귀
4. APScheduler 스케줄 원복

**Partial Rollback** (일봉만 롤백, 분봉 유지):
   ```sql
   DELETE FROM stock_prices WHERE source='KIS';
   ```

---

## Definition of Done

### Epic-Level DoD

- [ ] 4개 스토리 모두 Acceptance Criteria 충족
- [ ] 단위 테스트 커버리지 ≥ 80%
- [ ] 통합 테스트 통과 (E2E 시나리오)
- [ ] 코드 리뷰 완료 (최소 2명)
- [ ] 문서 업데이트:
  - [ ] `docs/KIS_API_INTEGRATION.md` 생성
  - [ ] `README.md`에 한투 API 설정 방법 추가
  - [ ] 분봉 수집 가이드 추가
- [ ] **FDR 대비 일봉 데이터 정합성 ≥ 99.5% 검증** ✅
- [ ] **1분봉 데이터 1주일 수집 성공 (≥ 98% 성공률)** ✅
- [ ] 프로덕션 배포 및 1주일 모니터링 완료
- [ ] **Phase 2 진행 승인** ✅

### Quality Gates

1. **코드 품질**:
   - Pylint 점수 ≥ 8.0
   - Type hints 커버리지 ≥ 90%
   - 코드 리뷰 통과

2. **성능**:
   - 일봉 수집 평균 응답 시간 < 500ms
   - 1분봉 수집 성공률 ≥ 98%
   - DB 쿼리 성능 저하 없음

3. **데이터 품질**:
   - FDR 대비 정합성 ≥ 99.5%
   - 누락 데이터 < 0.5%

---

## Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| API 인증 성공률 | 100% | 로그 분석 |
| 일봉 수집 성공률 | ≥ 99% | DB 레코드 수 |
| 1분봉 수집 성공률 | ≥ 98% | DB 레코드 수 |
| FDR 정합성 | ≥ 99.5% | 검증 스크립트 |
| Rate Limit 위반 | 0건 | 로그 분석 |
| 평균 API 응답 시간 | < 500ms | 로그 분석 |

### Qualitative Metrics

- [ ] 팀원들이 한투 API 사용법을 이해함
- [ ] 문서가 명확하고 따라하기 쉬움
- [ ] 코드가 유지보수하기 쉬움
- [ ] 모니터링이 용이함

---

## Estimated Effort

### Story Breakdown

| Story | Dev Days | Testing Days | Total |
|-------|----------|--------------|-------|
| Story 1: API 인증 | 3-4 | 1 | 4-5 |
| Story 2: 일봉 수집 | 4-5 | 2 | 6-7 |
| Story 3: 분봉 수집 | 4-5 | 2 | 6-7 |
| Story 4: 데이터 검증 | 2-3 | 1 | 3-4 |
| **Total** | **13-17** | **6** | **19-23** |

### Timeline

- **Week 1**: Story 1 (API 인증)
- **Week 2**: Story 2 (일봉 수집)
- **Week 3**: Story 3 (분봉 수집)
- **Week 4**: Story 4 (검증) + 통합 테스트 + 문서화

**Total**: **3-4 weeks**

---

## Next Steps After Phase 1

### Phase 2: 보조 지표 추가 (Week 5-7) ⭐⭐⭐⭐⭐

**Epic 004 예정:**
- 외국인/기관 매매 데이터 수집 (장중 4회)
- 재무제표 데이터 수집 (분기별)
- LLM 프롬프트 업데이트
- A/B 테스트 (예측 정확도 +15~25% 목표)

### Phase 3: 실시간 최적화 (Week 8-9)

**Epic 005 예정:**
- WebSocket 실시간 호가/체결
- 장중 리포트 동적 업데이트

### Phase 4: 확장 및 정리 (Week 10+)

**Epic 006 예정:**
- FDR 완전 제거
- 장외/코넥스 지원 조사 및 구현 (가능 시)
- 프리마켓 조사 및 구현 (가능 시)

---

## References

- **리서치 문서**: `docs/KIS_API_MIGRATION_RESEARCH.md`
- **한투 API 공식 문서**: https://apiportal.koreainvestment.com
- **공식 GitHub**: https://github.com/koreainvestment/open-trading-api
- **커뮤니티 SDK**: https://github.com/pjueon/pykis

---

**Epic Owner**: PM (John)
**Technical Lead**: TBD
**Stakeholders**: Development Team, Product Team
**Created**: 2025-11-08
**Last Updated**: 2025-11-08
