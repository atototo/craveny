# Epic 1: 데이터 수집 및 저장 인프라

### Epic 목표

프로젝트의 기술 기반을 구축하고, 뉴스와 주가 데이터를 자동으로 수집하여 AI 분석에 필요한 지식 베이스를 구축합니다. 모든 인프라(PostgreSQL, Milvus, Redis)가 Docker Compose로 관리되며, 10분마다 뉴스를 수집하고 1분마다 주가 데이터를 수집하는 안정적인 파이프라인이 작동합니다. Epic 완료 시, 헬스체크 API를 통해 데이터 수집 상태를 확인할 수 있으며, 최소 500건 이상의 과거 뉴스-주가 패턴이 벡터 DB에 저장되어 있습니다.

---

### Story 1.1: 프로젝트 초기 설정 및 인프라 구성

**As a** 개발자,
**I want** Git 레포지토리, Docker Compose, 환경 변수 설정을 완료하고,
**so that** 로컬과 프로덕션 환경에서 동일하게 개발할 수 있다.

#### Acceptance Criteria

1. Git 레포지토리가 생성되고 `.gitignore`에 `.env`, `milvus_data/`, `__pycache__/` 등이 포함되어 있다.
2. `docker-compose.yml`이 PostgreSQL, Milvus(etcd, minio 포함), Redis를 정의한다.
3. `.env.example` 파일이 필요한 환경 변수 템플릿을 제공한다 (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, DB_HOST 등).
4. `docker-compose up`으로 모든 서비스가 정상 실행된다.
5. `requirements.txt`가 주요 의존성을 포함한다 (fastapi, pymilvus, psycopg2, openai, python-telegram-bot, celery, redis, apscheduler 등).
6. 프로젝트 디렉토리 구조가 `backend/`, `data/`, `scripts/`, `tests/`, `docs/`로 구성된다.
7. README.md에 로컬 환경 설정 방법이 문서화되어 있다.

---

### Story 1.2: PostgreSQL 데이터베이스 스키마 설계 및 구축

**As a** 시스템,
**I want** 뉴스, 주가, 뉴스-주가 매칭 데이터를 저장할 PostgreSQL 스키마를 구축하고,
**so that** 수집된 데이터를 효율적으로 저장하고 조회할 수 있다.

#### Acceptance Criteria

1. `news` 테이블이 생성되며, 컬럼은 id(PK), title, content, published_at, source, stock_code, created_at을 포함한다.
2. `stock_prices` 테이블이 생성되며, 컬럼은 id(PK), stock_code, date, open, high, low, close, volume을 포함한다.
3. `news_stock_match` 테이블이 생성되며, 컬럼은 id(PK), news_id(FK), stock_code, price_change_1d, price_change_3d, price_change_5d, calculated_at을 포함한다.
4. `telegram_users` 테이블이 생성되며, 컬럼은 id(PK), user_id, subscribed_at, is_active를 포함한다.
5. 인덱스가 news(stock_code, published_at), stock_prices(stock_code, date)에 생성된다.
6. 데이터베이스 마이그레이션 스크립트(`scripts/init_db.py`)가 제공된다.
7. 로컬 테스트: 샘플 데이터 삽입 및 조회가 성공한다.

---

### Story 1.3: Milvus 벡터 DB 설정 및 컬렉션 생성

**As a** 시스템,
**I want** Milvus 벡터 DB를 Docker로 실행하고 뉴스 임베딩 컬렉션을 생성하여,
**so that** 과거 유사 뉴스를 빠르게 검색할 수 있다.

#### Acceptance Criteria

1. Milvus가 Docker Compose의 일부로 포트 19530에서 실행된다.
2. `news_embeddings` 컬렉션이 생성되며, 필드는 id(INT64, PK, auto_id), news_id(INT64), embedding(FLOAT_VECTOR, dim=768), stock_code(VARCHAR), price_change_1d(FLOAT), price_change_3d(FLOAT), price_change_5d(FLOAT)를 포함한다.
3. 인덱스가 embedding 필드에 생성된다 (metric_type: L2, index_type: IVF_FLAT).
4. Python 스크립트(`scripts/init_milvus.py`)로 컬렉션 생성 및 인덱스 구축이 자동화된다.
5. 로컬 테스트: 샘플 벡터 삽입 및 유사도 검색(TOP 5)이 성공한다.
6. Milvus 연결 헬퍼 함수(`backend/db/milvus_client.py`)가 제공된다.

---

### Story 1.4: 뉴스 크롤러 구현 (10분 주기)

**As a** 시스템,
**I want** 10분마다 한국 주요 언론사의 증권 뉴스를 자동으로 수집하여 PostgreSQL에 저장하고,
**so that** 최신 뉴스 데이터가 지속적으로 축적된다.

#### Acceptance Criteria

1. 뉴스 크롤러(`backend/crawlers/news_crawler.py`)가 네이버 뉴스, 한국경제, 매일경제를 크롤링한다.
2. APScheduler로 10분마다 크롤러가 자동 실행된다.
3. 각 뉴스에서 제목, 본문, 발표 시간, 종목코드(기업명 매칭)를 추출하여 `news` 테이블에 저장한다.
4. 중복 뉴스는 제목 유사도로 필터링하여 저장하지 않는다.
5. 크롤링 실패 시 에러 로그를 기록하고, 다음 주기에 재시도한다.
6. 크롤링 성공률을 추적하는 로그가 생성된다.
7. 종목코드 매핑 테이블(`stock_codes.json`)이 제공되어 기업명 → 종목코드 변환이 가능하다.

---

### Story 1.5: 주가 데이터 수집기 구현 (1분 주기)

**As a** 시스템,
**I want** 1분마다 코스피/코스닥 주가 데이터를 수집하여 PostgreSQL에 저장하고,
**so that** 실시간에 가까운 주가 정보를 확보한다.

#### Acceptance Criteria

1. 주가 수집기(`backend/crawlers/stock_crawler.py`)가 FinanceDataReader를 사용하여 주가 데이터를 수집한다.
2. APScheduler로 1분마다 수집기가 자동 실행된다 (장중 9:00~15:30).
3. 대형주(시가총액 상위 50개)를 우선 수집하며, 종목 리스트는 설정 파일로 관리된다.
4. 시가/고가/저가/종가/거래량 데이터를 `stock_prices` 테이블에 저장한다.
5. 장 시작 전(9:00 이전)과 장 마감 후(15:30 이후)는 수집을 중단한다.
6. 수집 실패 시 에러 로그를 기록하고, 다음 주기에 재시도한다.
7. 로컬 테스트: 특정 종목의 1분봉 데이터가 정상 저장된다.

---

### Story 1.6: 뉴스-주가 매칭 및 변동률 계산

**As a** 시스템,
**I want** 뉴스 발표 후 1일/3일/5일 주가 변동률을 자동 계산하여 저장하고,
**so that** LLM이 과거 패턴을 참조할 수 있다.

#### Acceptance Criteria

1. 매칭 스크립트(`backend/crawlers/news_stock_matcher.py`)가 매일 장 마감 후(15:40) 실행된다.
2. 각 뉴스에 대해 발표 시점 주가(T0)와 T+1일, T+3일, T+5일 종가를 조회한다.
3. 변동률 = ((T+N일 종가 - T0 주가) / T0 주가) * 100으로 계산한다.
4. 계산된 변동률을 `news_stock_match` 테이블에 저장한다.
5. 주말/공휴일은 다음 영업일 종가를 사용한다.
6. 매칭 정확도가 90% 이상이다.
7. 로컬 테스트: 특정 뉴스의 변동률이 정확히 계산된다.

---

### Story 1.7: 뉴스 임베딩 및 Milvus 저장

**As a** 시스템,
**I want** 수집된 뉴스를 OpenAI Embedding API로 임베딩하여 Milvus에 저장하고,
**so that** 유사 뉴스 검색이 가능하다.

#### Acceptance Criteria

1. 임베딩 스크립트(`backend/llm/embedder.py`)가 매일 장 마감 후(16:00) 실행된다.
2. 아직 임베딩되지 않은 뉴스를 `news` 테이블에서 조회한다.
3. OpenAI text-embedding-3-small API로 뉴스를 768차원 벡터로 변환한다.
4. 벡터와 메타데이터를 Milvus `news_embeddings` 컬렉션에 저장한다.
5. 임베딩 비용이 1건당 $0.0001 이하로 유지된다.
6. 임베딩 실패 시 에러 로그를 기록하고, 다음 실행 시 재시도한다.
7. 로컬 테스트: 100건 뉴스 임베딩 및 Milvus 저장이 성공한다.

---

### Story 1.8: 초기 데이터 수집 (과거 3개월)

**As a** 개발자,
**I want** 과거 3개월 뉴스 및 주가 데이터를 일괄 수집하는 스크립트를 실행하여,
**so that** MVP 시작 시점에 충분한 학습 데이터(500~1,000건)가 확보된다.

#### Acceptance Criteria

1. 일괄 수집 스크립트(`scripts/initial_data_collection.py`)가 제공된다.
2. 과거 3개월의 증권 뉴스를 크롤링하여 PostgreSQL에 저장한다.
3. 동일 기간의 주가 데이터를 수집하여 PostgreSQL에 저장한다.
4. 뉴스-주가 매칭 및 변동률을 계산하여 저장한다.
5. 모든 뉴스를 임베딩하여 Milvus에 저장한다.
6. 최소 500건 이상의 뉴스가 Milvus에 저장된다.
7. 스크립트 실행 시간은 2시간 이내로 완료된다.
8. 로컬 테스트: 스크립트 완료 후 데이터 건수 확인이 성공한다.

---

### Story 1.9: 헬스체크 API 구현

**As a** 개발자/운영자,
**I want** 시스템 상태를 확인할 수 있는 헬스체크 API를 제공받아,
**so that** 데이터 수집 파이프라인이 정상 작동 중인지 모니터링할 수 있다.

#### Acceptance Criteria

1. FastAPI 헬스체크 엔드포인트 `GET /health`가 구현된다.
2. 응답은 다음 정보를 JSON으로 반환한다:
   - `status`: "healthy" 또는 "unhealthy"
   - `postgres`: 연결 상태 (true/false)
   - `milvus`: 연결 상태 (true/false)
   - `redis`: 연결 상태 (true/false)
   - `news_count`: PostgreSQL 뉴스 건수
   - `vector_count`: Milvus 벡터 건수
   - `last_news_collected`: 마지막 뉴스 수집 시간
3. 모든 서비스 정상이면 HTTP 200, 문제 있으면 HTTP 503 반환.
4. FastAPI 서버가 포트 8000에서 실행되며, `http://localhost:8000/health`로 접근 가능하다.
5. 로컬 테스트: 헬스체크 API 호출 시 정상 응답 반환.
