# Epic 004: 한국투자증권 API 보조 지표 수집

**Status:** 📋 Planned
**Priority:** ⭐⭐⭐⭐⭐ (High - 예측 정확도 향상 핵심)
**Estimated Effort:** 4-5주 (19-27 dev days)
**Dependencies:** Epic 003 (Phase 1 Infrastructure) 완료 필요
**Target Completion:** Phase 1 완료 후 즉시 착수

---

## Epic 목표

KIS API를 통해 **외국인/기관/개인 매매 데이터**와 **재무제표 정보**를 수집하여 LLM 분석에 활용함으로써 주식 예측 정확도를 **15~25% 향상**시킵니다.

### 핵심 가치 제안

현재 시스템은 **뉴스 + 주가 변동**만으로 예측을 수행합니다. Epic 004 완료 시:

- ✅ 외국인/기관 매수세 분석 → "스마트 머니" 추종 전략 가능
- ✅ 재무제표 기반 펀더멘털 분석 → 뉴스의 실체 검증
- ✅ LLM 프롬프트 강화 → 다차원 분석으로 정확도 대폭 상승
- ✅ A/B 테스트로 정량적 개선 효과 입증

**예상 ROI:** 예측 정확도 +15~25% → 사용자 신뢰도 증가 → 리텐션 향상

---

## Story 004.1: 외국인/기관/개인 매매 데이터 수집

**As a** 주식 분석 시스템,
**I want** 외국인, 기관, 개인 투자자의 일별 매매 데이터를 수집하여,
**so that** LLM이 "스마트 머니" 흐름을 분석하고 예측 정확도를 높일 수 있다.

### 우선순위: ⭐⭐⭐⭐⭐

### Estimated Effort: 5-7일

### Tasks

#### 1. KIS API 투자자 매매 엔드포인트 조사 및 테스트 (1일)
- [ ] API 문서에서 투자자별 매매 데이터 조회 방법 확인
- [ ] Mock 환경에서 API 호출 테스트 (삼성전자 예시)
- [ ] 응답 데이터 구조 분석 (외국인/기관/개인 매수/매도/순매수)
- [ ] Rate limit 확인 (20 req/sec 내에서 50개 종목 수집 가능성)

#### 2. PostgreSQL 스키마 설계 및 마이그레이션 (1일)
- [ ] `investor_trading` 테이블 생성
  ```sql
  CREATE TABLE investor_trading (
      id SERIAL PRIMARY KEY,
      stock_code VARCHAR(10) NOT NULL,
      date DATE NOT NULL,
      timestamp TIMESTAMP NOT NULL,
      -- 외국인 매매
      foreign_buy BIGINT,      -- 외국인 매수량
      foreign_sell BIGINT,     -- 외국인 매도량
      foreign_net BIGINT,      -- 외국인 순매수 (매수 - 매도)
      -- 기관 매매
      institution_buy BIGINT,
      institution_sell BIGINT,
      institution_net BIGINT,
      -- 개인 매매
      individual_buy BIGINT,
      individual_sell BIGINT,
      individual_net BIGINT,
      created_at TIMESTAMP DEFAULT NOW(),
      INDEX idx_investor_stock_date (stock_code, date),
      UNIQUE KEY uk_stock_date (stock_code, date)
  );
  ```
- [ ] SQLAlchemy ORM 모델 작성 (`backend/db/models/investor_trading.py`)
- [ ] DB 마이그레이션 스크립트 작성

#### 3. 투자자 매매 수집기 구현 (2-3일)
- [ ] `backend/crawlers/investor_trading_crawler.py` 생성
- [ ] KIS API 클라이언트 재사용 (Epic 003에서 구현)
- [ ] 일별 데이터 수집 로직 구현
  - 대상: Epic 003의 50개 우선 종목
  - 수집 시점: 매일 장 마감 후 (16:00)
  - 수집 범위: 당일 투자자별 매매 데이터
- [ ] Rate limiting 적용 (20 req/sec, sliding window)
- [ ] Retry 로직 구현 (exponential backoff)
- [ ] Circuit breaker 패턴 적용 (연속 실패 시 알림)

#### 4. APScheduler 작업 등록 및 테스트 (1일)
- [ ] `scheduler.py`에 매일 16:00 작업 등록
  ```python
  scheduler.add_job(
      collect_investor_trading,
      trigger=CronTrigger(hour=16, minute=0),
      id='investor_trading_collector',
      replace_existing=True
  )
  ```
- [ ] 로컬 환경에서 수동 실행 테스트
- [ ] 50개 종목 수집 성공률 확인 (목표: ≥98%)
- [ ] DB 저장 검증 (중복 방지, 데이터 무결성)

#### 5. 과거 데이터 백필 스크립트 (1일)
- [ ] `scripts/backfill_investor_trading.py` 작성
- [ ] 과거 90일 데이터 일괄 수집 (Phase 1과 동일 범위)
- [ ] 배치 처리 (10개 종목씩, rate limit 준수)
- [ ] 진행률 표시 및 에러 핸들링
- [ ] 완료 시 데이터 건수 검증

### Acceptance Criteria

1. ✅ `investor_trading` 테이블이 생성되고 ORM 모델이 정상 작동한다.
2. ✅ 매일 16:00에 자동으로 50개 종목의 투자자 매매 데이터가 수집된다.
3. ✅ 수집 성공률이 **98% 이상**이다 (50개 중 49개 이상 성공).
4. ✅ 중복 데이터가 저장되지 않는다 (UNIQUE 제약 조건 작동).
5. ✅ 과거 90일 데이터가 백필되어 최소 **4,500건** (50종목 × 90일) 이상 저장된다.
6. ✅ Rate limit을 준수하며 (20 req/sec), circuit breaker가 연속 실패 시 작동한다.
7. ✅ 로그에 수집 성공/실패 건수가 기록되고 Slack/텔레그램 알림이 발송된다.

### Testing Strategy

- **Unit Tests**: KIS API 클라이언트, 데이터 파싱 로직, DB 저장 로직
- **Integration Tests**: APScheduler 작업 실행, DB 마이그레이션
- **E2E Tests**: 전체 수집 → 저장 → 조회 워크플로우
- **Performance Tests**: 50개 종목 수집 시간 측정 (목표: 10초 이내)

---

## Story 004.2: 재무제표 데이터 수집

**As a** 주식 분석 시스템,
**I want** 종목별 분기 재무제표 데이터(매출, 영업이익, 당기순이익, EPS, PER, PBR 등)를 수집하여,
**so that** LLM이 펀더멘털 분석을 통해 뉴스의 실체를 검증하고 예측 정확도를 높일 수 있다.

### 우선순위: ⭐⭐⭐⭐

### Estimated Effort: 5-7일

### Tasks

#### 1. KIS API 재무제표 엔드포인트 조사 및 테스트 (1-2일)
- [ ] API 문서에서 재무제표 조회 방법 확인
- [ ] Mock 환경에서 API 호출 테스트 (삼성전자 예시)
- [ ] 응답 데이터 구조 분석:
  - 손익계산서: 매출액, 영업이익, 당기순이익
  - 재무상태표: 자산총계, 부채총계, 자본총계
  - 주요 지표: EPS, PER, PBR, ROE, 부채비율
- [ ] 분기별 데이터 조회 가능 여부 확인 (최근 8분기)

#### 2. PostgreSQL 스키마 설계 및 마이그레이션 (1일)
- [ ] `financial_statements` 테이블 생성
  ```sql
  CREATE TABLE financial_statements (
      id SERIAL PRIMARY KEY,
      stock_code VARCHAR(10) NOT NULL,
      quarter VARCHAR(10) NOT NULL,  -- 예: '2024Q3'
      -- 손익계산서
      revenue BIGINT,               -- 매출액
      operating_profit BIGINT,      -- 영업이익
      net_income BIGINT,            -- 당기순이익
      -- 재무상태표
      total_assets BIGINT,          -- 자산총계
      total_liabilities BIGINT,     -- 부채총계
      total_equity BIGINT,          -- 자본총계
      -- 주요 지표
      eps FLOAT,                    -- 주당순이익
      per FLOAT,                    -- 주가수익비율
      pbr FLOAT,                    -- 주가순자산비율
      roe FLOAT,                    -- 자기자본이익률
      debt_ratio FLOAT,             -- 부채비율
      created_at TIMESTAMP DEFAULT NOW(),
      UNIQUE KEY uk_stock_quarter (stock_code, quarter),
      INDEX idx_financial_quarter (quarter)
  );
  ```
- [ ] SQLAlchemy ORM 모델 작성 (`backend/db/models/financial_statements.py`)
- [ ] DB 마이그레이션 스크립트 작성

#### 3. 재무제표 수집기 구현 (2-3일)
- [ ] `backend/crawlers/financial_statements_crawler.py` 생성
- [ ] KIS API 클라이언트 재사용
- [ ] 분기별 데이터 수집 로직 구현
  - 대상: Epic 003의 50개 우선 종목
  - 수집 범위: 최근 8분기 (2년치 데이터)
  - 수집 주기: 분기 결산 발표 후 (연 4회)
- [ ] 데이터 파싱 및 정규화 로직
- [ ] Rate limiting 및 retry 로직 적용

#### 4. APScheduler 작업 등록 및 테스트 (1일)
- [ ] `scheduler.py`에 분기별 수집 작업 등록 (결산 발표 시즌)
  ```python
  # 분기 결산 발표 시즌: 1월, 4월, 7월, 10월 중순
  scheduler.add_job(
      collect_financial_statements,
      trigger=CronTrigger(month='1,4,7,10', day=15, hour=18, minute=0),
      id='financial_statements_collector',
      replace_existing=True
  )
  ```
- [ ] 수동 실행 테스트 및 검증

#### 5. 과거 데이터 백필 스크립트 (1일)
- [ ] `scripts/backfill_financial_statements.py` 작성
- [ ] 최근 8분기 데이터 일괄 수집
- [ ] 50개 종목 × 8분기 = 400건 목표
- [ ] 진행률 표시 및 에러 핸들링

### Acceptance Criteria

1. ✅ `financial_statements` 테이블이 생성되고 ORM 모델이 정상 작동한다.
2. ✅ 분기별로 50개 종목의 재무제표 데이터가 자동 수집된다.
3. ✅ 과거 8분기 데이터가 백필되어 최소 **400건** (50종목 × 8분기) 이상 저장된다.
4. ✅ 주요 지표(EPS, PER, PBR, ROE, 부채비율)가 정확히 파싱되어 저장된다.
5. ✅ 중복 데이터가 저장되지 않는다 (stock_code + quarter UNIQUE).
6. ✅ 수집 성공률이 **95% 이상**이다 (API 제공 범위 내).
7. ✅ 로그에 수집 현황이 기록되고 알림이 발송된다.

### Testing Strategy

- **Unit Tests**: 재무제표 파싱 로직, 데이터 정규화
- **Integration Tests**: APScheduler 작업, DB 저장
- **Data Validation Tests**: 지표 계산 정확도 검증 (PER = 주가 / EPS 등)

---

## Story 004.3: LLM 프롬프트 통합 및 분석 로직 강화

**As a** 개발자,
**I want** 외국인/기관 매매 데이터와 재무제표 정보를 LLM 프롬프트에 통합하여,
**so that** AI가 다차원 분석을 수행하고 예측 정확도를 높일 수 있다.

### 우선순위: ⭐⭐⭐⭐⭐

### Estimated Effort: 4-6일

### Tasks

#### 1. 프롬프트 템플릿 설계 (1-2일)
- [ ] 기존 프롬프트 분석 (`backend/llm/prompts.py` 또는 관련 파일)
- [ ] 새로운 데이터 포함 프롬프트 템플릿 설계:
  ```python
  # 예시 프롬프트 구조
  """
  [뉴스 정보]
  - 제목: {news_title}
  - 내용: {news_content}
  - 발표 시각: {published_at}

  [주가 정보]
  - 현재가: {current_price}
  - 1일 변동: {price_change_1d}
  - 거래량: {volume}

  [투자자 매매 동향] ⭐ NEW
  - 외국인 순매수: {foreign_net} 주
  - 기관 순매수: {institution_net} 주
  - 개인 순매수: {individual_net} 주

  [재무 현황] ⭐ NEW
  - 최근 분기 매출: {revenue} 억원
  - 영업이익률: {operating_margin}%
  - PER: {per}, PBR: {pbr}
  - ROE: {roe}%, 부채비율: {debt_ratio}%

  이 뉴스가 주가에 미칠 영향을 분석하고, 1일/3일/5일 후 예상 변동률을 제시하세요.
  """
  ```
- [ ] Jinja2 템플릿 또는 f-string 방식 선택
- [ ] 프롬프트 길이 최적화 (GPT-4 token limit 고려)

#### 2. 데이터 조회 헬퍼 함수 구현 (1일)
- [ ] `backend/services/data_aggregator.py` 생성
- [ ] 뉴스-주가-투자자-재무 데이터 통합 조회 함수 작성:
  ```python
  def get_comprehensive_stock_data(stock_code: str, date: datetime) -> dict:
      """
      특정 종목의 종합 데이터를 조회합니다.

      Returns:
          {
              "stock_info": {...},
              "price_data": {...},
              "investor_trading": {...},
              "financial_statements": {...}
          }
      """
      pass
  ```
- [ ] 데이터 없을 경우 기본값 처리 (None → "데이터 없음")
- [ ] 성능 최적화 (JOIN 쿼리 또는 캐싱)

#### 3. LLM 분석 서비스 업데이트 (2일)
- [ ] `backend/services/stock_analysis_service.py` 수정
- [ ] 기존 분석 로직에 새 데이터 통합:
  ```python
  async def analyze_news_impact(news_id: int) -> dict:
      # 1. 뉴스 조회
      news = get_news_by_id(news_id)

      # 2. 종합 데이터 조회 ⭐ NEW
      stock_data = get_comprehensive_stock_data(
          stock_code=news.stock_code,
          date=news.published_at
      )

      # 3. 프롬프트 생성 ⭐ UPDATED
      prompt = render_prompt(news, stock_data)

      # 4. LLM 호출
      response = await openai_client.chat.completions.create(...)

      # 5. 결과 파싱 및 저장
      return parse_prediction(response)
  ```
- [ ] 에러 핸들링 (데이터 부족 시 degraded mode)
- [ ] 로깅 강화 (프롬프트 길이, LLM 응답 시간 등)

#### 4. 테스트 및 검증 (1일)
- [ ] 실제 뉴스 10건으로 분석 테스트
- [ ] 프롬프트 토큰 길이 측정 (tiktoken 라이브러리 사용)
- [ ] LLM 응답 품질 확인 (정성적 평가)
- [ ] 성능 테스트 (분석 시간 목표: 5초 이내)

### Acceptance Criteria

1. ✅ 외국인/기관 매매 데이터와 재무제표 정보가 LLM 프롬프트에 포함된다.
2. ✅ 프롬프트 토큰 길이가 **4,000 토큰 이하**로 유지된다 (GPT-4 context 절약).
3. ✅ 데이터가 없을 경우 graceful degradation 처리된다 (기존 방식으로 fallback).
4. ✅ 분석 시간이 **평균 5초 이내**로 완료된다.
5. ✅ 로그에 프롬프트 구조와 LLM 응답이 기록된다.
6. ✅ 10건의 테스트 뉴스 분석이 모두 성공한다.

### Testing Strategy

- **Unit Tests**: 데이터 조회 함수, 프롬프트 렌더링
- **Integration Tests**: LLM 호출, 응답 파싱
- **E2E Tests**: 전체 분석 워크플로우 (뉴스 → 데이터 조회 → LLM 분석 → 저장)

---

## Story 004.4: A/B 테스트 및 정확도 개선 검증

**As a** 개발자,
**I want** 기존 시스템(뉴스+주가)과 새 시스템(뉴스+주가+투자자+재무)을 A/B 테스트하여,
**so that** 예측 정확도 개선 효과를 정량적으로 입증할 수 있다.

### 우선순위: ⭐⭐⭐⭐

### Estimated Effort: 5-7일

### Tasks

#### 1. A/B 테스트 프레임워크 설계 (1-2일)
- [ ] 테스트 대상 정의:
  - **그룹 A (기존)**: 뉴스 + 주가 데이터만 사용
  - **그룹 B (신규)**: 뉴스 + 주가 + 투자자 + 재무 데이터 사용
- [ ] 평가 지표 정의:
  - **방향 정확도**: 실제 등락 방향과 예측 방향 일치율
  - **MAE (Mean Absolute Error)**: 예측 변동률과 실제 변동률 차이 평균
  - **Hit Rate**: 신뢰구간 내 실제값 포함 비율
- [ ] 테스트 데이터셋 준비:
  - 최근 30일 뉴스 200건 무작위 샘플링
  - 각 그룹에 100건씩 할당
- [ ] 통계적 유의성 검정 방법 선택 (t-test, chi-square 등)

#### 2. 테스트 인프라 구축 (2일)
- [ ] `backend/services/ab_test_service.py` 생성
- [ ] A/B 그룹별 분석 함수 작성:
  ```python
  async def run_ab_test(news_ids: List[int]) -> dict:
      results = {
          'group_a': [],  # 기존 시스템 결과
          'group_b': []   # 신규 시스템 결과
      }

      for news_id in news_ids:
          # 그룹 A: 기존 프롬프트
          result_a = await analyze_with_basic_data(news_id)
          results['group_a'].append(result_a)

          # 그룹 B: 강화 프롬프트
          result_b = await analyze_with_full_data(news_id)
          results['group_b'].append(result_b)

      return results
  ```
- [ ] 실제 변동률 조회 함수 (T+1일, T+3일, T+5일)
- [ ] 정확도 계산 함수 작성:
  ```python
  def calculate_metrics(predictions: List, actuals: List) -> dict:
      return {
          'direction_accuracy': ...,
          'mae': ...,
          'hit_rate': ...
      }
  ```

#### 3. A/B 테스트 실행 및 데이터 수집 (2일)
- [ ] 200건 뉴스에 대해 A/B 테스트 실행
- [ ] 각 그룹의 예측 결과 저장 (DB 또는 CSV)
- [ ] 실제 변동률 수집 (T+5일 후)
- [ ] 정확도 지표 계산 및 저장

#### 4. 결과 분석 및 리포트 작성 (1-2일)
- [ ] 그룹 A vs B 비교 분석:
  - 방향 정확도 차이 계산
  - MAE 차이 계산
  - Hit Rate 차이 계산
- [ ] 통계적 유의성 검정 (p-value < 0.05 목표)
- [ ] 시각화 생성:
  - 정확도 비교 막대 그래프
  - MAE 분포 히스토그램
  - 시간대별 성능 추이
- [ ] 마크다운 리포트 작성 (`docs/reports/ab_test_results.md`)
  ```markdown
  # A/B 테스트 결과 리포트

  ## 테스트 개요
  - 기간: 2024-XX-XX ~ 2024-XX-XX
  - 샘플 수: 각 그룹 100건

  ## 핵심 발견
  - 방향 정확도: 그룹 A 65% → 그룹 B 82% (+17%p) ⭐
  - MAE: 그룹 A 3.2% → 그룹 B 2.1% (-34%) ⭐
  - Hit Rate: 그룹 A 58% → 그룹 B 79% (+21%p) ⭐

  ## 통계적 유의성
  - p-value: 0.003 (< 0.05, 통계적으로 유의함)

  ## 결론
  외국인/기관 매매 + 재무제표 데이터 통합으로 **예측 정확도 17%p 향상** 확인.
  ```

#### 5. 프로덕션 배포 준비 (1일)
- [ ] A/B 테스트 결과 리뷰 미팅
- [ ] 신규 시스템 배포 결정
- [ ] Feature flag 설정 (gradual rollout)
- [ ] 모니터링 대시보드 업데이트

### Acceptance Criteria

1. ✅ 200건의 뉴스에 대해 A/B 테스트가 완료된다.
2. ✅ 그룹 B(신규)의 방향 정확도가 그룹 A(기존)보다 **15%p 이상** 높다.
3. ✅ 그룹 B의 MAE가 그룹 A보다 **20% 이상** 낮다.
4. ✅ 통계적 유의성이 **p < 0.05**로 확인된다.
5. ✅ A/B 테스트 결과 리포트가 작성되고 공유된다.
6. ✅ 신규 시스템 배포 계획이 수립된다.

### Testing Strategy

- **Statistical Tests**: t-test, chi-square test for significance
- **Data Validation**: 실제 변동률 데이터 정확성 검증
- **Reproducibility Tests**: 동일 데이터로 재실행 시 동일 결과 확인

---

## 리스크 및 완화 전략

### 리스크 1: KIS API 투자자 매매/재무제표 데이터 미제공
**Impact:** High | **Probability:** Low
- **완화 전략**:
  - Epic 004 시작 전 KIS API 문서 상세 확인
  - Mock 환경에서 사전 테스트 필수
  - 대안: 네이버 금융, 한국거래소 공개 데이터 크롤링

### 리스크 2: LLM 프롬프트 토큰 초과
**Impact:** Medium | **Probability:** Medium
- **완화 전략**:
  - 프롬프트 압축 기법 적용 (핵심 정보만 포함)
  - GPT-4-turbo 사용 (128K context window)
  - 재무 데이터 요약 (최근 2분기만 포함)

### 리스크 3: A/B 테스트 결과 미미
**Impact:** High | **Probability:** Low
- **완화 전략**:
  - 샘플 크기 확대 (200건 → 500건)
  - 테스트 기간 연장 (30일 → 60일)
  - LLM 프롬프트 튜닝 (few-shot examples 추가)

### 리스크 4: 재무제표 데이터 업데이트 지연
**Impact:** Low | **Probability:** Medium
- **완화 전략**:
  - 분기 결산 발표 일정 모니터링
  - 데이터 없을 시 graceful degradation
  - 알림 시스템으로 수동 트리거 지원

---

## 성공 지표 (Success Metrics)

### 정량적 지표
- ✅ 외국인/기관 매매 데이터 수집 성공률: **≥98%**
- ✅ 재무제표 데이터 수집 성공률: **≥95%**
- ✅ LLM 분석 성공률: **≥99%** (데이터 통합 후)
- ✅ A/B 테스트 방향 정확도 개선: **≥15%p**
- ✅ A/B 테스트 MAE 개선: **≥20%**
- ✅ 통계적 유의성: **p < 0.05**

### 정성적 지표
- ✅ LLM 분석 품질 향상 (정성적 평가)
- ✅ 사용자 신뢰도 증가 (리텐션 모니터링)
- ✅ 팀 만족도: A/B 테스트 결과에 대한 긍정적 피드백

---

## Dependencies

### Epic 003 완료 필수
- ✅ KIS API 인증 시스템
- ✅ KIS API 클라이언트 라이브러리
- ✅ 일봉 데이터 수집 파이프라인
- ✅ PostgreSQL 스키마 기반 인프라

### 외부 의존성
- KIS API 투자자 매매/재무제표 엔드포인트 정상 작동
- OpenAI GPT-4 API 사용 가능

---

## Timeline

```
Week 1:
  Day 1-3: Story 004.1 (투자자 매매 수집기) - API 조사, 스키마, 구현
  Day 4-5: Story 004.1 백필 및 테스트

Week 2:
  Day 1-3: Story 004.2 (재무제표 수집기) - API 조사, 스키마, 구현
  Day 4-5: Story 004.2 백필 및 테스트

Week 3:
  Day 1-3: Story 004.3 (LLM 프롬프트 통합) - 템플릿 설계, 헬퍼 함수, 서비스 업데이트
  Day 4-5: Story 004.3 테스트 및 검증

Week 4:
  Day 1-2: Story 004.4 (A/B 테스트 프레임워크) - 설계 및 인프라
  Day 3-4: A/B 테스트 실행 및 데이터 수집
  Day 5: 결과 분석 및 리포트 작성

Week 5 (버퍼):
  Day 1-2: 리뷰 및 버그 수정
  Day 3: 프로덕션 배포 준비
  Day 4-5: 배포 및 모니터링
```

---

## 다음 단계 (Phase 3 Preview)

Epic 004 완료 후 Phase 3에서:
- ✅ 실시간 WebSocket 데이터 수집 (체결가, 호가)
- ✅ 장중 급변 감지 및 즉시 분석
- ✅ 텔레그램 알림 최적화 (지연 시간 <3초)
- ✅ LLM 응답 속도 개선 (캐싱, 스트리밍)

**예상 ROI**: 실시간성 향상으로 사용자 참여도 30% 증가 목표
