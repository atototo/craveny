# Epic 006: 한국투자증권 API 마이그레이션 완료 및 시스템 최적화

**Status:** 📋 Planned
**Priority:** ⭐⭐⭐ (Medium - 마무리 및 확장)
**Estimated Effort:** 2-3주 (12-17 dev days)
**Dependencies:** Epic 003, Epic 004, Epic 005 완료 필요
**Target Completion:** Phase 3 완료 후 착수

---

## Epic 목표

FinanceDataReader를 **완전히 제거**하고 KIS API로 100% 전환을 완료합니다. KONEX/OTC/프리마켓 데이터 수집 가능성을 조사하고, 데이터 품질 모니터링 시스템을 구축하여 **장기 운영 안정성**을 확보합니다.

### 핵심 가치 제안

Epic 006 완료 시:

- ✅ FinanceDataReader 제거 → 단일 데이터 소스로 유지보수 간소화
- ✅ KONEX/OTC 시장 지원 → 커버리지 확대 (코스피/코스닥 + α)
- ✅ 데이터 품질 모니터링 → 이상치 자동 감지 및 알림
- ✅ 비용 최적화 → API 호출 최소화로 무료 한도 내 운영
- ✅ 성능 튜닝 → 응답 시간 20% 개선

**예상 ROI:** 운영 비용 절감 + 시스템 안정성 향상 → 개발 생산성 +25%

---

## Story 006.1: FinanceDataReader 제거 및 마이그레이션 검증

**As a** 개발자,
**I want** FinanceDataReader 의존성을 완전히 제거하고 KIS API로 100% 전환하여,
**so that** 단일 데이터 소스로 시스템을 단순화하고 유지보수를 용이하게 할 수 있다.

### 우선순위: ⭐⭐⭐⭐

### Estimated Effort: 4-5일

### Tasks

#### 1. FDR 사용처 전수 조사 (1일)
- [ ] 코드베이스 전체 검색 (`grep -r "FinanceDataReader"`)
- [ ] 사용 중인 파일 및 함수 목록 작성:
  ```
  backend/crawlers/stock_crawler.py: fetch_stock_data()
  scripts/collect_stock_history.py: backfill_historical_data()
  backend/services/stock_analysis_service.py: (fallback 로직?)
  ```
- [ ] 각 사용처의 대체 방안 계획:
  - `fetch_stock_data()` → KIS API 일봉 조회
  - `backfill_historical_data()` → KIS API 과거 데이터 조회
  - Fallback 로직 → 제거 (KIS API만 사용)

#### 2. FDR 제거 및 KIS API 대체 (2일)
- [ ] `backend/crawlers/stock_crawler.py` 수정:
  ```python
  # Before (FDR)
  import FinanceDataReader as fdr
  df = fdr.DataReader(stock_code, start=start_str)

  # After (KIS API)
  from backend.kis.client import KISClient
  kis = KISClient()
  df = await kis.get_daily_prices(stock_code, start_date=start_str)
  ```
- [ ] `scripts/collect_stock_history.py` 수정 (동일 로직)
- [ ] Fallback 로직 제거 (source 필드에서 'FDR' 제거)
- [ ] `requirements.txt`에서 `finance-datareader` 제거

#### 3. 데이터 정합성 검증 (1-2일)
- [ ] 검증 스크립트 작성 (`scripts/verify_migration.py`):
  ```python
  async def verify_data_consistency():
      """
      KIS API 데이터와 기존 FDR 데이터를 비교하여 정합성 검증.
      """
      stocks = ["005930", "000660", ...]  # 샘플 10개 종목

      for stock_code in stocks:
          # KIS API 데이터 조회
          kis_data = await kis_client.get_daily_prices(stock_code, start_date="2024-10-01")

          # DB에서 기존 FDR 데이터 조회
          fdr_data = db.query(StockPrice).filter(
              StockPrice.stock_code == stock_code,
              StockPrice.source == 'FDR',
              StockPrice.date >= "2024-10-01"
          ).all()

          # 비교: 날짜별 종가 차이
          for kis_row, fdr_row in zip(kis_data, fdr_data):
              diff = abs(kis_row['close'] - fdr_row.close)
              if diff > 0.01:  # 0.01원 이상 차이
                  print(f"⚠️  불일치: {stock_code} {kis_row['date']} KIS={kis_row['close']} FDR={fdr_row.close}")

      print("✅ 정합성 검증 완료")
  ```
- [ ] 10개 종목, 최근 30일 데이터 비교
- [ ] 차이 발생 시 원인 분석 (분할/병합, 배당 조정 등)
- [ ] 허용 오차 정의 (±0.1% 이내)

#### 4. DB 정리 및 source 필드 업데이트 (1일)
- [ ] `stock_prices` 테이블에서 `source='FDR'` 데이터 처리:
  - Option A: 삭제 (KIS 데이터로 완전 대체)
  - Option B: 보관 (source='FDR_ARCHIVED'로 변경)
- [ ] `source` 필드 기본값 변경:
  ```sql
  ALTER TABLE stock_prices ALTER COLUMN source SET DEFAULT 'KIS';
  ```
- [ ] 통계 업데이트:
  ```sql
  SELECT source, COUNT(*) FROM stock_prices GROUP BY source;
  -- 결과: KIS=100%, FDR=0%
  ```

#### 5. 회귀 테스트 및 배포 (1일)
- [ ] 전체 워크플로우 E2E 테스트:
  - 주가 수집 → 뉴스 매칭 → LLM 분석 → 텔레그램 알림
- [ ] 성능 테스트 (처리 시간, 메모리 사용량)
- [ ] 프로덕션 배포
- [ ] 모니터링 (24시간 관찰)

### Acceptance Criteria

1. ✅ `FinanceDataReader` 의존성이 `requirements.txt`에서 제거된다.
2. ✅ 코드베이스에서 FDR 관련 코드가 모두 제거되거나 주석 처리된다.
3. ✅ 10개 종목, 30일 데이터 정합성 검증 시 **차이 ±0.1% 이내**이다.
4. ✅ `stock_prices` 테이블의 모든 새 데이터가 `source='KIS'`로 저장된다.
5. ✅ E2E 테스트가 **100% 성공**한다.
6. ✅ 프로덕션 배포 후 **24시간 무장애** 운영된다.

### Testing Strategy

- **Data Quality Tests**: KIS vs FDR 정합성 검증
- **Regression Tests**: 기존 기능 모두 정상 작동
- **Performance Tests**: 응답 시간, 메모리 사용량 비교
- **E2E Tests**: 전체 워크플로우 검증

---

## Story 006.2: KONEX/OTC/프리마켓 데이터 수집 조사 및 시범 구현

**As a** 개발자,
**I want** KONEX, OTC, 프리마켓 데이터 수집 가능성을 조사하여,
**so that** 시스템 커버리지를 확대하고 더 많은 투자 기회를 포착할 수 있다.

### 우선순위: ⭐⭐

### Estimated Effort: 3-5일

### Tasks

#### 1. KIS API KONEX/OTC 지원 조사 (1-2일)
- [ ] KIS API 문서에서 KONEX/OTC 관련 엔드포인트 확인:
  - KONEX 일봉 조회 가능 여부
  - OTC(장외) 시세 조회 가능 여부
  - 프리마켓/애프터마켓 데이터 제공 여부
- [ ] Mock 환경에서 테스트:
  ```python
  # KONEX 종목 예시: 089980 (상상인저축은행)
  konex_data = await kis_client.get_daily_prices("089980", market="KONEX")
  ```
- [ ] 조사 결과 문서화 (`docs/research/konex_otc_feasibility.md`)

#### 2. 지원 가능 시 시범 구현 (2일)
- [ ] `stocks` 테이블에 `market` 컬럼 추가:
  ```sql
  ALTER TABLE stocks ADD COLUMN market VARCHAR(10) DEFAULT 'KOSPI';
  -- 값: KOSPI, KOSDAQ, KONEX, OTC
  ```
- [ ] KONEX 종목 10개 추가 (시가총액 상위)
- [ ] 데이터 수집 테스트
- [ ] 분석 워크플로우 정상 작동 확인

#### 3. 지원 불가 시 대안 조사 (1일)
- [ ] 대안 데이터 소스 조사:
  - 한국거래소(KRX) 공개 데이터
  - 네이버 금융, 다음 증권
  - 금융감독원 전자공시시스템(DART)
- [ ] 크롤링 법적 이슈 검토
- [ ] 비용/효과 분석 후 Phase 5 에픽 계획

### Acceptance Criteria

1. ✅ KIS API KONEX/OTC 지원 여부가 명확히 파악된다.
2. ✅ 조사 결과가 문서화된다 (`docs/research/konex_otc_feasibility.md`).
3. ✅ 지원 가능 시 KONEX 종목 10개 시범 수집이 성공한다.
4. ✅ 지원 불가 시 대안이 2개 이상 제시된다.

### Testing Strategy

- **API Tests**: KONEX/OTC 엔드포인트 호출 테스트
- **Data Quality Tests**: KONEX 데이터 정합성 검증
- **Integration Tests**: 기존 워크플로우와 통합 테스트

---

## Story 006.3: 데이터 품질 모니터링 시스템 구축

**As a** 운영자,
**I want** 데이터 품질 이상치를 자동 감지하고 알림받아,
**so that** 데이터 오류로 인한 예측 실패를 사전에 방지할 수 있다.

### 우선순위: ⭐⭐⭐⭐

### Estimated Effort: 4-6일

### Tasks

#### 1. 품질 체크 규칙 정의 (1일)
- [ ] 이상치 감지 규칙:
  - **Rule 1**: 주가 급변 (전일 대비 ±30% 초과 → 상한가/하한가 제외)
  - **Rule 2**: 거래량 이상 (평균 대비 10배 초과 또는 0)
  - **Rule 3**: 데이터 누락 (장 종료 후 데이터 미수집)
  - **Rule 4**: 중복 데이터 (동일 종목+날짜 2건 이상)
  - **Rule 5**: 시가=고가=저가=종가 (거래 정지 의심)
- [ ] 허용 임계값 설정 (상한가/하한가는 정상으로 간주)

#### 2. 품질 체크 스크립트 구현 (2-3일)
- [ ] `backend/services/data_quality_service.py` 생성
- [ ] 각 규칙별 체크 함수:
  ```python
  async def check_sudden_price_change():
      """주가 급변 감지 (상한가/하한가 제외)"""
      issues = []
      stocks = db.query(StockPrice).filter(
          StockPrice.date == today
      ).all()

      for stock in stocks:
          prev_price = get_previous_close(stock.stock_code)
          if prev_price:
              change_rate = (stock.close - prev_price) / prev_price * 100

              # 상한가/하한가 확인 (±30%)
              is_limit = abs(change_rate) >= 29.5

              if abs(change_rate) > 30 and not is_limit:
                  issues.append({
                      "stock_code": stock.stock_code,
                      "issue": f"급변 {change_rate:.1f}% (상한가/하한가 아님)",
                      "severity": "high"
                  })

      return issues

  async def check_missing_data():
      """데이터 누락 감지"""
      expected_stocks = get_active_stocks()  # 50개
      collected_stocks = db.query(StockPrice.stock_code).filter(
          StockPrice.date == today
      ).distinct().count()

      if collected_stocks < len(expected_stocks):
          missing = set(expected_stocks) - set(collected_stocks)
          return [{
              "issue": f"데이터 누락: {len(missing)}개 종목",
              "details": list(missing),
              "severity": "critical"
          }]

      return []
  ```
- [ ] 통합 체크 함수:
  ```python
  async def run_quality_checks() -> List[dict]:
      all_issues = []
      all_issues.extend(await check_sudden_price_change())
      all_issues.extend(await check_missing_data())
      all_issues.extend(await check_duplicate_data())
      all_issues.extend(await check_volume_anomaly())
      all_issues.extend(await check_trading_halt())
      return all_issues
  ```

#### 3. APScheduler 작업 등록 (1일)
- [ ] 매일 장 마감 후 17:00 실행:
  ```python
  scheduler.add_job(
      run_quality_checks_and_alert,
      trigger=CronTrigger(hour=17, minute=0),
      id='data_quality_check',
      replace_existing=True
  )

  async def run_quality_checks_and_alert():
      issues = await run_quality_checks()

      if issues:
          # Slack/텔레그램 알림
          await send_alert(f"⚠️  데이터 품질 이슈 {len(issues)}건 감지")

          # 상세 리포트 저장
          save_quality_report(issues)
  ```
- [ ] 알림 템플릿:
  ```
  ⚠️  데이터 품질 이슈 감지

  🔴 Critical: 2건
  - 데이터 누락: 삼성전자, SK하이닉스

  🟠 High: 1건
  - 급변 이상: NAVER (35% 상승, 상한가 아님)

  상세: /reports/quality_2024-11-08.json
  ```

#### 4. 품질 리포트 대시보드 (1-2일)
- [ ] FastAPI 엔드포인트 추가:
  ```python
  @app.get("/api/data-quality/report")
  async def get_quality_report(date: str = None):
      if date is None:
          date = datetime.now().strftime("%Y-%m-%d")

      report = load_quality_report(date)
      return {
          "date": date,
          "total_issues": len(report),
          "critical": [i for i in report if i['severity'] == 'critical'],
          "high": [i for i in report if i['severity'] == 'high'],
          "medium": [i for i in report if i['severity'] == 'medium']
      }
  ```
- [ ] 간단한 HTML 대시보드 (Jinja2 템플릿)
- [ ] 히스토리 조회 (최근 30일 품질 추이)

#### 5. 테스트 및 검증 (1일)
- [ ] 인위적 이상 데이터 삽입하여 감지 테스트
- [ ] 알림 발송 테스트
- [ ] 대시보드 UI 테스트

### Acceptance Criteria

1. ✅ 5가지 품질 체크 규칙이 모두 구현되고 정상 작동한다.
2. ✅ 매일 17:00에 자동으로 품질 체크가 실행된다.
3. ✅ 이상치 감지 시 **3분 이내** 알림이 발송된다.
4. ✅ 품질 리포트 API가 정상 작동하고 JSON 형식으로 응답한다.
5. ✅ 대시보드에서 최근 30일 품질 추이를 조회할 수 있다.
6. ✅ False positive 비율이 **5% 이하**이다 (상한가/하한가 오탐지 방지).

### Testing Strategy

- **Unit Tests**: 각 품질 체크 함수
- **Integration Tests**: APScheduler 작업, 알림 발송
- **E2E Tests**: 이상 데이터 삽입 → 감지 → 알림 → 리포트
- **False Positive Tests**: 상한가/하한가 정상 감지 검증

---

## Story 006.4: 비용 최적화 및 성능 튜닝

**As a** 개발자,
**I want** KIS API 호출을 최적화하고 시스템 성능을 개선하여,
**so that** 무료 한도 내에서 운영하고 응답 시간을 단축할 수 있다.

### 우선순위: ⭐⭐⭐

### Estimated Effort: 3-4일

### Tasks

#### 1. API 호출 최적화 (1-2일)
- [ ] 호출 패턴 분석:
  - 일봉 수집: 50개 종목, 하루 1회 → 50 req/day
  - 분봉 수집: 50개 종목 × 390분 → 19,500 req/day (장중)
  - 투자자 매매: 50개 종목, 하루 1회 → 50 req/day
  - 재무제표: 50개 종목, 분기 1회 → 50 req/quarter
  - **총 호출**: ~20,000 req/day (실시간 제외)
- [ ] 배치 요청 구현 (가능 시):
  - 단일 요청으로 복수 종목 조회
  - 예: `get_multiple_stocks(["005930", "000660", ...])`
- [ ] 캐싱 전략 강화:
  - 일봉 데이터: 1시간 캐시 (장중 변동 없음)
  - 투자자 매매: 4시간 캐시 (일 1회 업데이트)

#### 2. 데이터베이스 쿼리 최적화 (1일)
- [ ] Slow query 식별 (PostgreSQL `pg_stat_statements`)
- [ ] 인덱스 추가:
  ```sql
  -- 자주 조회되는 컬럼 조합
  CREATE INDEX idx_stock_prices_code_date_desc ON stock_prices (stock_code, date DESC);
  CREATE INDEX idx_news_stock_published ON news (stock_code, published_at DESC);
  ```
- [ ] N+1 쿼리 해결 (SQLAlchemy `joinedload`)
- [ ] 커넥션 풀 튜닝 (`pool_size=20`, `max_overflow=10`)

#### 3. 애플리케이션 성능 튜닝 (1일)
- [ ] 비동기 처리 확대 (`asyncio.gather`):
  ```python
  # Before: 순차 처리
  for stock_code in stocks:
      await collect_data(stock_code)

  # After: 병렬 처리
  tasks = [collect_data(code) for code in stocks]
  await asyncio.gather(*tasks)
  ```
- [ ] LRU 캐시 적용 (자주 호출되는 함수):
  ```python
  from functools import lru_cache

  @lru_cache(maxsize=100)
  def get_stock_info(stock_code: str):
      return db.query(Stock).filter_by(code=stock_code).first()
  ```
- [ ] 메모리 프로파일링 (`memory_profiler`) 및 최적화

#### 4. 성능 벤치마크 (1일)
- [ ] Before/After 비교:
  - API 호출 수: 20,000 → 15,000 req/day (-25%)
  - 평균 응답 시간: 500ms → 400ms (-20%)
  - DB 쿼리 시간: 100ms → 70ms (-30%)
  - 메모리 사용량: 500MB → 400MB (-20%)
- [ ] 부하 테스트 (Locust, Apache JMeter)
- [ ] 결과 문서화 (`docs/reports/performance_tuning.md`)

### Acceptance Criteria

1. ✅ 일일 API 호출 수가 **25% 이상 감소**한다.
2. ✅ 평균 응답 시간이 **20% 이상 개선**된다.
3. ✅ DB 쿼리 시간이 **30% 이상 단축**된다.
4. ✅ 메모리 사용량이 **20% 이상 감소**한다.
5. ✅ 부하 테스트에서 초당 100 req 처리 가능.
6. ✅ 성능 개선 리포트가 작성되고 공유된다.

### Testing Strategy

- **Performance Tests**: 응답 시간, 처리량, 메모리 사용량
- **Load Tests**: Locust로 초당 100 req 부하 테스트
- **Profiling**: `cProfile`, `memory_profiler`로 병목 지점 분석
- **Benchmark**: Before/After 정량적 비교

---

## 리스크 및 완화 전략

### 리스크 1: FDR 제거 후 데이터 불일치
**Impact:** High | **Probability:** Low
- **완화 전략**:
  - 철저한 정합성 검증 (30일 × 10종목)
  - Dual-run 모드 1주일 유지 후 제거
  - 롤백 계획 수립 (FDR 재설치 스크립트)

### 리스크 2: KONEX/OTC API 미지원
**Impact:** Low | **Probability:** Medium
- **완화 전략**:
  - Phase 5 에픽으로 크롤링 방식 대안 검토
  - 현재는 KOSPI/KOSDAQ만으로도 충분한 커버리지

### 리스크 3: 품질 체크 오탐지 (False Positive)
**Impact:** Medium | **Probability:** Medium
- **완화 전략**:
  - 상한가/하한가 화이트리스트 관리
  - 임계값 조정 (30% → 35%)
  - 알림 severity 분류 (critical/high/medium)

### 리스크 4: 성능 개선 효과 미미
**Impact:** Low | **Probability:** Low
- **완화 전략**:
  - 프로파일링으로 실제 병목 지점 파악
  - 단계별 최적화 (쉬운 것부터)
  - 목표 미달 시 Phase 5로 이월

---

## 성공 지표 (Success Metrics)

### 정량적 지표
- ✅ FDR 의존성 제거: **100%**
- ✅ 데이터 정합성: **차이 ±0.1% 이내**
- ✅ 품질 체크 정확도: **False positive ≤5%**
- ✅ API 호출 감소: **≥25%**
- ✅ 응답 시간 개선: **≥20%**
- ✅ 메모리 사용 감소: **≥20%**

### 정성적 지표
- ✅ 시스템 단순화 (단일 데이터 소스)
- ✅ 운영 안정성 향상 (품질 모니터링)
- ✅ 개발 생산성 증가 (유지보수 용이)

---

## Dependencies

### Epic 003, 004, 005 완료 필수
- ✅ KIS API 완전 통합
- ✅ 모든 데이터 수집 파이프라인 정상 작동
- ✅ LLM 분석 시스템 안정화

### 인프라 요구사항
- PostgreSQL 15+ (쿼리 최적화)
- Redis 6.0+ (캐싱)
- Monitoring tools (Grafana, Prometheus)

---

## Timeline

```
Week 1:
  Day 1-2: Story 006.1 (FDR 사용처 조사 및 제거)
  Day 3-4: Story 006.1 (정합성 검증 및 DB 정리)
  Day 5: Story 006.1 회귀 테스트

Week 2:
  Day 1-2: Story 006.2 (KONEX/OTC 조사)
  Day 3: Story 006.2 (시범 구현 또는 대안 조사)
  Day 4-5: Story 006.3 (품질 체크 규칙 및 스크립트 구현)

Week 3:
  Day 1-2: Story 006.3 (APScheduler 작업, 대시보드)
  Day 3: Story 006.3 테스트
  Day 4-5: Story 006.4 (API/DB/앱 성능 최적화)

Week 4 (버퍼):
  Day 1-2: Story 006.4 (벤치마크 및 문서화)
  Day 3-4: 최종 리뷰 및 버그 수정
  Day 5: 프로덕션 배포 및 모니터링
```

---

## 프로젝트 최종 성과 (Epic 003~006 통합)

### 예측 정확도 개선
- **Phase 1** (Epic 003): 일봉/분봉 수집 → 기준선 확립
- **Phase 2** (Epic 004): 투자자 매매 + 재무제표 → **+15~25%p**
- **Phase 3** (Epic 005): 실시간 데이터 + LLM 최적화 → **+10%p**
- **Phase 4** (Epic 006): 품질 모니터링 + 성능 튜닝 → **+5%p**
- **총 개선**: **+30~40%p** (예: 60% → 90~100%)

### 사용자 경험 개선
- 실시간 알림 지연: 1분 → **3초 이내**
- 사용자 참여도: **+30%**
- 리텐션: **+20%**

### 시스템 안정성 및 효율성
- 데이터 소스 단순화: FDR + KIS → **KIS 100%**
- API 호출 최적화: **-25%**
- 응답 시간 개선: **-20%**
- 데이터 품질 모니터링: **자동화**

### 운영 비용
- KIS API: **완전 무료**
- 개발 생산성: **+25%** (유지보수 간소화)

---

## 다음 단계 (Phase 5+ - 선택적 확장)

Epic 006 완료 후 추가 확장 가능 영역:

### Phase 5A: KONEX/OTC 크롤링 (Epic 006.2 결과에 따라)
- 한국거래소 공개 데이터 활용
- 크롤링 인프라 구축
- 법적 검토 및 승인

### Phase 5B: 글로벌 주식 지원
- 미국 주식 (Yahoo Finance API, Alpha Vantage)
- 일본/중국 주식 확장

### Phase 5C: AI 고도화
- 멀티모달 분석 (뉴스 이미지, 차트 패턴)
- 강화학습 기반 전략 최적화
- 앙상블 모델 (GPT-4 + Claude + Gemini)

### Phase 5D: 사용자 기능 확장
- 포트폴리오 추적
- 커스텀 알림 설정
- 백테스팅 기능

---

## 마치며

Epic 003~006 완료 시 **한국투자증권 API 기반 완전 자동화 주식 분석 시스템**이 구축됩니다.

**핵심 달성 목표:**
✅ 예측 정확도 +30~40%p
✅ 실시간 알림 3초 이내
✅ 무료 운영 (KIS API)
✅ 안정적 품질 모니터링
✅ 높은 개발 생산성

**감사합니다! 🎉**
