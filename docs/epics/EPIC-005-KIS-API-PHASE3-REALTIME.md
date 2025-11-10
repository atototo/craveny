# Epic 005: 한국투자증권 API 실시간 데이터 수집

**Status:** 📋 Planned
**Priority:** ⭐⭐⭐⭐ (High - 실시간성 핵심)
**Estimated Effort:** 3-4주 (16-22 dev days)
**Dependencies:** Epic 003, Epic 004 완료 필요
**Target Completion:** Phase 2 완료 후 즉시 착수

---

## Epic 목표

KIS API **WebSocket**을 통해 **실시간 체결가, 호가 데이터**를 수집하고, **장중 급변 감지 시스템**을 구축하여 뉴스 발표 후 **3초 이내** 텔레그램 알림을 발송함으로써 사용자 참여도를 **30% 향상**시킵니다.

### 핵심 가치 제안

현재 시스템은 **1분봉 기반 배치 수집**으로 지연이 발생합니다. Epic 005 완료 시:

- ✅ 실시간 체결가 수집 → 장중 급변 즉시 감지
- ✅ 실시간 호가 데이터 → 매수/매도 압력 분석
- ✅ 이벤트 기반 알림 → 3초 이내 텔레그램 발송
- ✅ LLM 응답 최적화 → 스트리밍 + 캐싱으로 속도 2배 개선

**예상 ROI:** 실시간 알림으로 사용자 참여도 +30%, 리텐션 +20%

---

## Story 005.1: WebSocket 실시간 체결가 수집

**As a** 주식 분석 시스템,
**I want** KIS API WebSocket을 통해 실시간 체결가 데이터를 수집하여,
**so that** 장중 급변을 즉시 감지하고 사용자에게 빠르게 알릴 수 있다.

### 우선순위: ⭐⭐⭐⭐⭐

### Estimated Effort: 5-7일

### Tasks

#### 1. KIS API WebSocket 조사 및 프로토타입 (2일)
- [ ] KIS API 문서에서 WebSocket 엔드포인트 확인
  - 체결가 구독 (실시간 OHLCV)
  - 인증 방식 (OAuth 2.0 토큰)
  - 데이터 포맷 (JSON, protobuf 등)
- [ ] Python `websockets` 라이브러리 선택 및 테스트
- [ ] Mock 환경에서 삼성전자 체결가 구독 프로토타입:
  ```python
  import asyncio
  import websockets
  import json

  async def subscribe_realtime_price(stock_code: str):
      uri = "wss://openapi.koreainvestment.com/..."
      async with websockets.connect(uri) as ws:
          # 인증 메시지 전송
          await ws.send(json.dumps({
              "header": {"approval_key": "..."},
              "body": {"input": {"tr_id": "H0STCNT0", "tr_key": stock_code}}
          }))

          # 실시간 데이터 수신
          async for message in ws:
              data = json.loads(message)
              print(f"체결: {data['output']['stck_prpr']}")  # 현재가
  ```
- [ ] 연결 안정성 테스트 (1시간 이상 지속)

#### 2. PostgreSQL 스키마 설계 (1일)
- [ ] `stock_prices_realtime` 테이블 생성
  ```sql
  CREATE TABLE stock_prices_realtime (
      id SERIAL PRIMARY KEY,
      stock_code VARCHAR(10) NOT NULL,
      timestamp TIMESTAMP NOT NULL,
      price FLOAT NOT NULL,          -- 체결가
      change_rate FLOAT,              -- 등락률
      volume BIGINT,                  -- 체결량
      cumulative_volume BIGINT,       -- 누적 거래량
      bid_price FLOAT,                -- 매수 호가
      ask_price FLOAT,                -- 매도 호가
      created_at TIMESTAMP DEFAULT NOW(),
      INDEX idx_realtime_stock_timestamp (stock_code, timestamp)
  );

  -- 파티셔닝: 일별로 분할하여 성능 최적화
  CREATE TABLE stock_prices_realtime_2024_11_08 PARTITION OF stock_prices_realtime
  FOR VALUES FROM ('2024-11-08') TO ('2024-11-09');
  ```
- [ ] SQLAlchemy ORM 모델 작성
- [ ] TimescaleDB 또는 파티셔닝 적용 (데이터 급증 대비)

#### 3. 실시간 체결가 수집기 구현 (2-3일)
- [ ] `backend/crawlers/realtime_price_crawler.py` 생성
- [ ] WebSocket 연결 관리:
  - 자동 재연결 (exponential backoff)
  - Heartbeat (30초마다 ping/pong)
  - 장 시작(9:00) 자동 연결, 장 마감(15:30) 자동 종료
- [ ] 50개 종목 동시 구독:
  - 멀티 WebSocket 연결 (stock당 1개) 또는
  - 단일 연결에서 복수 종목 구독 (KIS API 스펙 확인)
- [ ] 데이터 파싱 및 DB 저장:
  ```python
  async def handle_realtime_message(message: dict):
      data = parse_kis_message(message)
      await save_to_db(StockPriceRealtime(
          stock_code=data['stock_code'],
          timestamp=data['timestamp'],
          price=data['price'],
          change_rate=data['change_rate'],
          volume=data['volume'],
          ...
      ))
  ```
- [ ] 급변 감지 로직:
  - 1분 내 5% 이상 변동 시 이벤트 발행
  - Redis Pub/Sub로 알림 시스템에 전달
- [ ] 에러 핸들링:
  - WebSocket 연결 끊김 시 재연결
  - 데이터 파싱 실패 시 로그 기록 및 스킵

#### 4. 시스템 서비스 통합 (1일)
- [ ] `backend/main.py`에서 백그라운드 태스크로 실행:
  ```python
  from fastapi import BackgroundTasks

  @app.on_event("startup")
  async def startup_event():
      asyncio.create_task(start_realtime_crawler())

  async def start_realtime_crawler():
      crawler = RealtimePriceCrawler()
      await crawler.run()  # 장중 9:00-15:30 자동 실행
  ```
- [ ] Graceful shutdown 구현 (SIGTERM 시 WebSocket 정리)
- [ ] 헬스체크 엔드포인트 추가:
  ```python
  @app.get("/health/realtime")
  async def health_realtime():
      return {
          "status": "healthy" if crawler.is_connected else "unhealthy",
          "connected_stocks": len(crawler.subscriptions),
          "last_message_at": crawler.last_message_time
      }
  ```

#### 5. 테스트 및 검증 (1일)
- [ ] 장중 테스트 (실제 장 시간대)
- [ ] 50개 종목 동시 구독 성공 확인
- [ ] 데이터 저장 성공률 측정 (목표: ≥99%)
- [ ] 지연 시간 측정 (체결 발생 → DB 저장, 목표: <1초)
- [ ] 급변 감지 정확도 테스트

### Acceptance Criteria

1. ✅ WebSocket으로 50개 종목의 실시간 체결가가 수집된다.
2. ✅ 장중(9:00-15:30) 자동 연결/종료가 정상 작동한다.
3. ✅ 데이터 저장 성공률이 **99% 이상**이다.
4. ✅ 체결 발생부터 DB 저장까지 **평균 1초 이내**로 처리된다.
5. ✅ 급변 감지(1분 내 5% 이상) 시 Redis Pub/Sub 이벤트가 발행된다.
6. ✅ WebSocket 연결 끊김 시 **30초 이내 자동 재연결**된다.
7. ✅ 헬스체크 엔드포인트가 WebSocket 상태를 정확히 반영한다.

### Testing Strategy

- **Unit Tests**: 데이터 파싱, 급변 감지 로직
- **Integration Tests**: WebSocket 연결, DB 저장
- **Load Tests**: 50개 종목 동시 구독 안정성
- **E2E Tests**: 장중 실시간 수집 → 급변 감지 → 이벤트 발행

---

## Story 005.2: 실시간 호가 데이터 수집

**As a** 주식 분석 시스템,
**I want** 실시간 호가창 데이터(매수/매도 1~10호가)를 수집하여,
**so that** 매수/매도 압력을 분석하고 LLM 예측 정확도를 높일 수 있다.

### 우선순위: ⭐⭐⭐

### Estimated Effort: 3-5일

### Tasks

#### 1. KIS API 호가 WebSocket 조사 (1일)
- [ ] 호가 구독 엔드포인트 확인
- [ ] 데이터 포맷 분석 (매수/매도 1~10호가, 잔량)
- [ ] Mock 환경 테스트

#### 2. PostgreSQL 스키마 설계 (1일)
- [ ] `stock_orderbook` 테이블 생성
  ```sql
  CREATE TABLE stock_orderbook (
      id SERIAL PRIMARY KEY,
      stock_code VARCHAR(10) NOT NULL,
      timestamp TIMESTAMP NOT NULL,
      -- 매수 호가 (1~10호가)
      bid_price_1 FLOAT, bid_volume_1 BIGINT,
      bid_price_2 FLOAT, bid_volume_2 BIGINT,
      ... (생략: bid_price_10, bid_volume_10까지)
      -- 매도 호가 (1~10호가)
      ask_price_1 FLOAT, ask_volume_1 BIGINT,
      ask_price_2 FLOAT, ask_volume_2 BIGINT,
      ... (생략: ask_price_10, ask_volume_10까지)
      -- 파생 지표
      bid_ask_spread FLOAT,           -- 호가 스프레드
      total_bid_volume BIGINT,        -- 총 매수 잔량
      total_ask_volume BIGINT,        -- 총 매도 잔량
      buy_pressure_ratio FLOAT,       -- 매수 압력 비율
      created_at TIMESTAMP DEFAULT NOW(),
      INDEX idx_orderbook_stock_timestamp (stock_code, timestamp)
  );
  ```
- [ ] ORM 모델 작성

#### 3. 호가 수집기 구현 (2일)
- [ ] `backend/crawlers/realtime_orderbook_crawler.py` 생성
- [ ] WebSocket 구독 (Story 005.1과 유사)
- [ ] 호가 데이터 파싱 및 DB 저장
- [ ] 매수/매도 압력 지표 계산:
  ```python
  buy_pressure_ratio = total_bid_volume / (total_bid_volume + total_ask_volume)
  ```
- [ ] 급격한 호가 변동 감지 (압력 비율 0.7 이상/0.3 이하)

#### 4. 테스트 및 검증 (1일)
- [ ] 장중 테스트
- [ ] 데이터 품질 확인 (호가 순서, 잔량 정합성)
- [ ] 저장 성공률 측정 (목표: ≥98%)

### Acceptance Criteria

1. ✅ 50개 종목의 실시간 호가 데이터가 수집된다.
2. ✅ 매수/매도 1~10호가 및 잔량이 정확히 저장된다.
3. ✅ 매수 압력 비율이 실시간으로 계산된다.
4. ✅ 데이터 저장 성공률이 **98% 이상**이다.
5. ✅ 급격한 호가 변동 감지 시 이벤트가 발행된다.

### Testing Strategy

- **Unit Tests**: 호가 파싱, 압력 지표 계산
- **Integration Tests**: WebSocket 구독, DB 저장
- **Data Quality Tests**: 호가 순서, 잔량 정합성 검증

---

## Story 005.3: 장중 급변 감지 및 이벤트 기반 알림 시스템

**As a** 사용자,
**I want** 장중 급변(5% 이상 변동 또는 매수 압력 급증) 발생 시 3초 이내 텔레그램 알림을 받아,
**so that** 실시간으로 투자 기회를 포착할 수 있다.

### 우선순위: ⭐⭐⭐⭐⭐

### Estimated Effort: 4-6일

### Tasks

#### 1. 급변 감지 로직 설계 (1일)
- [ ] 감지 조건 정의:
  - **조건 1**: 1분 내 주가 5% 이상 변동
  - **조건 2**: 매수 압력 비율 0.8 이상 (강한 매수세)
  - **조건 3**: 거래량 급증 (평균 대비 3배 이상)
- [ ] Redis Pub/Sub 아키텍처 설계:
  ```
  [WebSocket Crawler] → [급변 감지] → [Redis Pub/Sub] → [Alarm Worker] → [Telegram]
  ```
- [ ] 중복 알림 방지 (5분 내 동일 종목 1회만 알림)

#### 2. Redis Pub/Sub 이벤트 시스템 구현 (2일)
- [ ] `backend/events/market_events.py` 생성
- [ ] 이벤트 발행:
  ```python
  async def publish_sudden_change(stock_code: str, change_rate: float):
      event = {
          "type": "sudden_change",
          "stock_code": stock_code,
          "change_rate": change_rate,
          "timestamp": datetime.now().isoformat()
      }
      await redis_client.publish("market_events", json.dumps(event))
  ```
- [ ] 이벤트 구독 Worker:
  ```python
  async def subscribe_market_events():
      pubsub = redis_client.pubsub()
      await pubsub.subscribe("market_events")

      async for message in pubsub.listen():
          if message['type'] == 'message':
              event = json.loads(message['data'])
              await handle_market_event(event)
  ```
- [ ] FastAPI 백그라운드 태스크로 Worker 실행

#### 3. LLM 긴급 분석 모드 구현 (2일)
- [ ] `backend/services/urgent_analysis_service.py` 생성
- [ ] 급변 발생 시 즉시 LLM 분석 트리거:
  ```python
  async def analyze_sudden_change(stock_code: str, change_rate: float):
      # 1. 최근 뉴스 조회 (1시간 이내)
      recent_news = get_recent_news(stock_code, hours=1)

      # 2. 실시간 데이터 조회
      realtime_data = get_realtime_data(stock_code)

      # 3. LLM 긴급 분석
      prompt = f"""
      [긴급 상황]
      종목: {stock_code}
      현재 변동률: {change_rate}%
      최근 뉴스: {recent_news}
      실시간 호가: {realtime_data['orderbook']}

      이 급변의 원인을 분석하고, 향후 전망을 간략히 제시하세요.
      """
      response = await openai_client.chat.completions.create(
          model="gpt-4-turbo",
          messages=[{"role": "user", "content": prompt}],
          max_tokens=300  # 빠른 응답 위해 제한
      )

      return response.choices[0].message.content
  ```
- [ ] 응답 캐싱 (동일 종목 5분 내 재분석 방지)

#### 4. 텔레그램 알림 최적화 (1-2일)
- [ ] `backend/services/telegram_service.py` 수정
- [ ] 알림 템플릿 개선:
  ```
  🚨 급변 감지!

  📈 삼성전자 (005930)
  현재가: 72,500원 (▲5.2%)
  거래량: 평균 대비 3.5배

  🤖 AI 분석:
  {LLM 분석 결과 요약}

  ⏰ {현재 시각}
  ```
- [ ] 비동기 전송 (asyncio)
- [ ] 재시도 로직 (Telegram API 실패 시)

#### 5. 성능 최적화 및 테스트 (1일)
- [ ] 전체 파이프라인 지연 시간 측정:
  - 체결 발생 → 급변 감지 → LLM 분석 → 텔레그램 전송
  - 목표: **평균 3초 이내**
- [ ] 부하 테스트 (동시 급변 10건)
- [ ] 모니터링 대시보드 (Grafana)

### Acceptance Criteria

1. ✅ 급변 감지부터 텔레그램 알림까지 **평균 3초 이내**로 처리된다.
2. ✅ 중복 알림이 방지된다 (5분 내 동일 종목 1회).
3. ✅ LLM 분석 결과가 알림에 포함된다.
4. ✅ 텔레그램 전송 성공률이 **99% 이상**이다.
5. ✅ Redis Pub/Sub 이벤트 유실률이 **0.1% 미만**이다.
6. ✅ 동시 급변 10건 발생 시에도 정상 작동한다.

### Testing Strategy

- **Performance Tests**: 지연 시간, 처리량 측정
- **Load Tests**: 동시 급변 10건 부하 테스트
- **Integration Tests**: 전체 파이프라인 E2E 테스트
- **Failover Tests**: Redis/Telegram API 장애 시나리오

---

## Story 005.4: LLM 응답 속도 최적화 (스트리밍 + 캐싱)

**As a** 개발자,
**I want** LLM 응답 속도를 2배 개선하여,
**so that** 급변 알림 지연을 최소화하고 사용자 경험을 향상시킬 수 있다.

### 우선순위: ⭐⭐⭐

### Estimated Effort: 4-5일

### Tasks

#### 1. GPT-4 스트리밍 API 적용 (2일)
- [ ] OpenAI Streaming API 조사 및 테스트:
  ```python
  async def stream_llm_analysis(prompt: str):
      stream = await openai_client.chat.completions.create(
          model="gpt-4-turbo",
          messages=[{"role": "user", "content": prompt}],
          stream=True
      )

      full_response = ""
      async for chunk in stream:
          if chunk.choices[0].delta.content:
              content = chunk.choices[0].delta.content
              full_response += content
              # 실시간 전송 (WebSocket or SSE)
              yield content

      return full_response
  ```
- [ ] 텔레그램 알림에 스트리밍 적용:
  - 초기 메시지 전송 (제목 + "분석 중...")
  - 스트리밍으로 메시지 업데이트 (edit_message)
- [ ] 응답 시간 측정 (Before: 5초 → After: 2.5초 목표)

#### 2. Redis 캐싱 전략 구현 (2일)
- [ ] 캐싱 대상 정의:
  - 동일 뉴스에 대한 분석 결과 (TTL: 1시간)
  - 종목별 최근 분석 (TTL: 5분)
  - 프롬프트 템플릿 (TTL: 24시간)
- [ ] 캐시 키 설계:
  ```python
  cache_key = f"analysis:{stock_code}:{news_id}:{hash(prompt)}"
  ```
- [ ] 캐시 히트율 목표: **60% 이상**
- [ ] 캐시 무효화 로직 (급변 발생 시 관련 캐시 삭제)

#### 3. 프롬프트 최적화 (1일)
- [ ] 토큰 수 감소 (5,000 → 3,000 tokens):
  - 핵심 정보만 포함
  - Few-shot examples 축소
  - JSON 포맷 응답 요청 (파싱 속도 개선)
- [ ] 응답 길이 제한 (max_tokens=300)
- [ ] 빠른 모델 테스트 (GPT-3.5-turbo vs GPT-4-turbo)

#### 4. 성능 벤치마크 및 A/B 테스트 (1일)
- [ ] Before/After 비교:
  - 평균 응답 시간
  - 캐시 히트율
  - 비용 절감율 (캐시 효과)
- [ ] 품질 저하 없는지 확인 (정성적 평가)

### Acceptance Criteria

1. ✅ LLM 평균 응답 시간이 **5초 → 2.5초**로 단축된다.
2. ✅ 캐시 히트율이 **60% 이상**이다.
3. ✅ 스트리밍 적용으로 사용자 체감 지연이 **50% 감소**한다.
4. ✅ 비용이 캐싱으로 **30% 이상** 절감된다.
5. ✅ 분석 품질이 최적화 전과 동등하다 (정성적 평가).

### Testing Strategy

- **Performance Tests**: 응답 시간, 캐시 히트율
- **Load Tests**: 동시 요청 100건 부하 테스트
- **Quality Tests**: 최적화 전후 분석 품질 비교
- **Cost Analysis**: OpenAI API 비용 절감율 측정

---

## 리스크 및 완화 전략

### 리스크 1: WebSocket 연결 불안정
**Impact:** High | **Probability:** Medium
- **완화 전략**:
  - 자동 재연결 로직 (exponential backoff)
  - Heartbeat 메커니즘 (30초마다)
  - 연결 상태 모니터링 및 알림

### 리스크 2: 실시간 데이터 급증으로 DB 성능 저하
**Impact:** High | **Probability:** Medium
- **완화 전략**:
  - TimescaleDB 또는 파티셔닝 적용
  - Write-ahead log 최적화
  - 배치 삽입 (bulk insert, 100건씩)
  - 오래된 데이터 자동 아카이빙 (30일 이상)

### 리스크 3: LLM API 응답 지연/실패
**Impact:** Medium | **Probability:** Low
- **완화 전략**:
  - 타임아웃 설정 (3초)
  - Fallback 메시지 ("분석 중 오류 발생")
  - 재시도 로직 (exponential backoff)

### 리스크 4: 텔레그램 Rate Limit 초과
**Impact:** Medium | **Probability:** Low
- **완화 전략**:
  - Rate limiting (초당 1건)
  - 메시지 큐 (Redis Queue)
  - 우선순위 큐 (급변 > 일반 알림)

---

## 성공 지표 (Success Metrics)

### 정량적 지표
- ✅ 실시간 데이터 수집 성공률: **≥99%**
- ✅ 급변 감지부터 알림까지 지연: **평균 3초 이내**
- ✅ WebSocket 연결 안정성: **99.9% 업타임**
- ✅ LLM 응답 시간: **5초 → 2.5초** (50% 개선)
- ✅ 캐시 히트율: **≥60%**
- ✅ 텔레그램 전송 성공률: **≥99%**

### 정성적 지표
- ✅ 사용자 참여도: **+30%** (알림 클릭률 증가)
- ✅ 리텐션 향상: **+20%** (7일 리텐션 측정)
- ✅ 사용자 피드백: 긍정적 평가 (설문조사)

---

## Dependencies

### Epic 003, 004 완료 필수
- ✅ KIS API 인증 시스템
- ✅ 일봉/분봉 데이터 수집 파이프라인
- ✅ LLM 분석 시스템
- ✅ 텔레그램 알림 시스템

### 인프라 요구사항
- Redis 6.0+ (Pub/Sub 지원)
- PostgreSQL 15+ (파티셔닝 지원)
- FastAPI 백그라운드 태스크
- WebSocket 지원 (Python `websockets` 라이브러리)

---

## Timeline

```
Week 1:
  Day 1-2: Story 005.1 (WebSocket 조사 및 프로토타입)
  Day 3-4: Story 005.1 (체결가 수집기 구현)
  Day 5: Story 005.1 테스트

Week 2:
  Day 1-2: Story 005.2 (호가 WebSocket 구현)
  Day 3: Story 005.2 테스트
  Day 4-5: Story 005.3 (급변 감지 로직 설계 및 Redis Pub/Sub)

Week 3:
  Day 1-2: Story 005.3 (LLM 긴급 분석 및 텔레그램 최적화)
  Day 3: Story 005.3 E2E 테스트
  Day 4-5: Story 005.4 (스트리밍 API 적용)

Week 4:
  Day 1-2: Story 005.4 (Redis 캐싱 및 프롬프트 최적화)
  Day 3: 전체 성능 벤치마크
  Day 4-5: 리뷰, 버그 수정, 프로덕션 배포
```

---

## 다음 단계 (Phase 4 Preview)

Epic 005 완료 후 Phase 4에서:
- ✅ FinanceDataReader 완전 제거
- ✅ KIS API 전환 완료 검증
- ✅ KONEX/OTC 시장 지원 조사
- ✅ 장외/프리마켓 데이터 수집 (가능 시)
- ✅ 데이터 품질 모니터링 대시보드
- ✅ 비용 최적화 및 성능 튜닝

**최종 목표**: 100% KIS API 기반 시스템, 예측 정확도 +30% 달성
