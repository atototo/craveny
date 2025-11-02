# 크롤링 전략 구현 완료

## 개요

사용자 요청에 따라 3가지 뉴스 수집 전략을 구현했습니다:
1. ✅ **최신 뉴스 크롤링** (기존 기능)
2. ✅ **종목별 뉴스 검색** (신규 구현)
3. ✅ **DART 공시 크롤링** (신규 구현)

## 구현 상세

### 1. 최신 뉴스 크롤링 (기존)

**목적**: 주요 언론사에서 최신 경제 뉴스 수집

**실행 주기**: 10분마다

**수집 대상**:
- 네이버 뉴스 (최대 10건)
- 한국경제 뉴스 (최대 10건)
- 매일경제 뉴스 (최대 10건)

**구현 위치**: `backend/scheduler/crawler_scheduler.py:_crawl_all_sources()`

### 2. 종목별 뉴스 검색 (신규)

**목적**: DB에 등록된 종목별로 관련 뉴스 검색

**실행 주기**: 10분마다

**수집 전략**:
- 활성화된 종목(`is_active=True`)만 대상
- 우선순위별 차등 수집
  - Priority 1-2 (높은 우선순위): 10건
  - Priority 3 (중간 우선순위): 5건
  - Priority 4-5 (낮은 우선순위): 3건

**검색 방법**:
- NaverNewsSearchCrawler 사용
- 종목명을 키워드로 검색
- 최신순 정렬

**구현 위치**: `backend/scheduler/crawler_scheduler.py:_crawl_stock_specific_news()`

**주요 코드**:
```python
def _crawl_stock_specific_news(self) -> None:
    """종목별로 뉴스를 검색하여 수집합니다."""
    db = SessionLocal()
    saver = NewsSaver(db)
    search_crawler = NaverNewsSearchCrawler()

    # DB에서 활성화된 종목 조회
    stocks = db.query(Stock).filter(
        Stock.is_active == True
    ).order_by(Stock.priority).all()

    for stock in stocks:
        # 우선순위별 수집량 결정
        if stock.priority <= 2:
            limit = 10
        elif stock.priority == 3:
            limit = 5
        else:
            limit = 3

        # 종목명으로 뉴스 검색
        news_list = search_crawler.search_news(
            query=stock.name,
            max_pages=1,
            max_results=limit
        )

        if news_list:
            saved, skipped = saver.save_news_batch(news_list)
```

### 3. DART 공시 크롤링 (신규)

**목적**: 금융감독원 전자공시시스템에서 기업 공시 정보 수집

**실행 주기**: 5분마다

**수집 대상**:
- Priority 1-2 종목만 (중요 종목만)
- 최근 3일간 공시

**API 정보**:
- DART Open API 사용
- API 키 필요 (https://opendart.fss.or.kr/)
- `.env` 파일에 `DART_API_KEY` 설정

**구현 위치**:
- `backend/crawlers/dart_crawler.py`: DartCrawler 클래스
- `backend/scheduler/crawler_scheduler.py:_crawl_dart_disclosures()`: 스케줄러 통합

**주요 코드**:
```python
def _crawl_dart_disclosures(self) -> None:
    """DART 공시 정보를 수집합니다."""
    db = SessionLocal()
    saver = NewsSaver(db)
    dart_crawler = DartCrawler()

    # Priority 1-2 종목만 조회 (중요 종목만)
    stocks = db.query(Stock).filter(
        Stock.is_active == True,
        Stock.priority <= 2
    ).all()

    for stock in stocks:
        # 최근 3일 공시 조회
        disclosures = dart_crawler.fetch_disclosures_by_stock_code(
            stock_code=stock.code,
            start_date=datetime.now() - timedelta(days=3),
            end_date=datetime.now(),
        )

        if disclosures:
            saved, skipped = saver.save_news_batch(disclosures)
```

## 스케줄러 등록

모든 크롤링 작업이 APScheduler에 등록되어 자동 실행됩니다:

```python
def start(self):
    # 1. 최신 뉴스 (10분 간격)
    self.scheduler.add_job(
        func=self._crawl_all_sources,
        trigger=IntervalTrigger(minutes=10),
        id="news_crawler_job",
        name="뉴스 크롤러"
    )

    # 2. 종목별 검색 (10분 간격)
    self.scheduler.add_job(
        func=self._crawl_stock_specific_news,
        trigger=IntervalTrigger(minutes=10),
        id="stock_news_search_job",
        name="종목별 뉴스 검색"
    )

    # 3. DART 공시 (5분 간격)
    self.scheduler.add_job(
        func=self._crawl_dart_disclosures,
        trigger=IntervalTrigger(minutes=5),
        id="dart_disclosure_job",
        name="DART 공시 크롤링"
    )
```

## 초기 실행

서버 시작 시 모든 크롤러를 한 번씩 즉시 실행:

```python
# 초기 실행
self._crawl_all_sources()          # 최신 뉴스
self._crawl_stock_specific_news()  # 종목별 검색
self._crawl_dart_disclosures()     # DART 공시
```

## 데이터 흐름

```
1. 뉴스 수집
   ↓
2. NewsArticle 테이블에 저장
   ↓
3. 종목 코드 추출 및 매칭
   ↓
4. 자동 예측 (LLM)
   ↓
5. Prediction 테이블에 저장
   ↓
6. 텔레그램 알림 발송 (조건 충족 시)
```

## 설정 방법

### 1. DART API 키 발급 (선택사항)

DART 공시 크롤링을 사용하려면 API 키가 필요합니다:

1. https://opendart.fss.or.kr/ 접속
2. 회원가입 후 로그인
3. API 키 신청 및 발급
4. `.env` 파일에 추가:

```env
DART_API_KEY=your_api_key_here
```

API 키가 없으면 DART 크롤링은 스킵됩니다.

### 2. 종목 관리

종목별 뉴스 검색과 DART 공시는 DB에 등록된 종목만 대상으로 합니다:

1. `/admin` 페이지에서 종목 추가/수정
2. 활성화 상태(`is_active`) 설정
3. 우선순위(`priority`) 설정
   - 1-2: 높은 우선순위 (많은 뉴스 수집, DART 공시 포함)
   - 3: 중간 우선순위
   - 4-5: 낮은 우선순위 (적은 뉴스 수집)

## 테스트

### DART 크롤러 테스트

```bash
python scripts/test_dart_crawler.py
```

삼성전자(005930) 종목의 최근 3일 공시를 조회합니다.

## 로그 확인

크롤링 작업 실행 시 로그로 상태를 확인할 수 있습니다:

```
🔄 종목별 뉴스 검색 시작 (#1)
   📊 삼성전자: 10건 검색, 5건 저장, 5건 스킵
   📊 SK하이닉스: 10건 검색, 3건 저장, 7건 스킵
✅ 종목별 검색 완료: 2개 종목, 총 8건 저장

📋 DART 공시 크롤링 시작 (#1)
   📊 삼성전자: 2건 수집, 2건 저장
   📊 SK하이닉스: 1건 수집, 1건 저장
✅ DART 공시 완료: 2개 종목, 총 3건 저장
```

## 문제 해결

### DART API 키 에러

```
⚠️  DART API 키가 설정되지 않았습니다
```

→ `.env` 파일에 `DART_API_KEY` 추가

### 종목이 검색되지 않음

→ 관리자 페이지에서 종목 활성화 상태 확인

### 중복 뉴스가 많이 스킵됨

→ 정상 동작입니다. 중복 방지를 위해 이미 저장된 뉴스는 스킵합니다.

## 요약

| 크롤링 유형 | 실행 주기 | 수집 대상 | 수집량 |
|------------|---------|----------|--------|
| 최신 뉴스 | 10분 | 주요 언론사 | 각 10건 |
| 종목별 검색 | 10분 | 활성 종목 | 우선순위별 3-10건 |
| DART 공시 | 5분 | P1-2 종목 | 최근 3일 전체 |

모든 크롤링은 DB 종목 관리와 연동되어 자동으로 예측 및 알림까지 처리됩니다.
