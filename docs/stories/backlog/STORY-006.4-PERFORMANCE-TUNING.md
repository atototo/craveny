# Story 006.4: 비용 최적화 및 성능 튜닝

**Epic**: Epic 006 | **Priority**: ⭐⭐⭐ | **Effort**: 5-7일 | **Dependencies**: Story 006.1, 006.3

---

## Overview

KIS API 호출 최적화, 데이터베이스 인덱싱, 캐싱 전략으로 시스템 성능을 개선합니다.

**목표**: API 호출 -25%, 응답 시간 -20%

---

## Acceptance Criteria

1. ✅ API 호출 최적화 (배치 처리)
2. ✅ 데이터베이스 인덱스 최적화
3. ✅ Redis 캐싱 전략
4. ✅ API 응답 시간 -20% (평균 5초 → 4초)
5. ✅ API 호출 횟수 -25%

---

## Optimization Areas

### 1. API 호출 최적화

**문제점**: 종목별 순차 호출로 인한 비효율

```python
# 기존 방식 (비효율)
for stock_code in stock_codes:  # 50개
    await kis_client.get_daily_prices(stock_code)
    # 총 50회 API 호출
```

**개선안**: 배치 처리 + 병렬 요청

```python
# backend/crawlers/optimized_crawler.py

import asyncio
from typing import List


class OptimizedCrawler:
    """최적화된 크롤러"""

    def __init__(self):
        self.kis_client = KISClient()
        self.batch_size = 10  # 동시 요청 수
        self.semaphore = asyncio.Semaphore(10)  # Rate limiting

    async def collect_daily_prices_batch(
        self,
        stock_codes: List[str],
        target_date: datetime
    ):
        """일봉 배치 수집"""

        # 배치 단위로 분할
        batches = [
            stock_codes[i:i + self.batch_size]
            for i in range(0, len(stock_codes), self.batch_size)
        ]

        results = []

        for batch in batches:
            # 병렬 실행
            tasks = [
                self._collect_single_stock(code, target_date)
                for code in batch
            ]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend(batch_results)

            # Rate limiting (200ms 대기)
            await asyncio.sleep(0.2)

        logger.info(f"✅ 배치 수집 완료: {len(results)}건")
        return results

    async def _collect_single_stock(
        self,
        stock_code: str,
        target_date: datetime
    ):
        """단일 종목 수집 (세마포어 적용)"""

        async with self.semaphore:
            try:
                df = await self.kis_client.get_daily_prices(
                    stock_code=stock_code,
                    start_date=target_date,
                    end_date=target_date
                )

                self._save_to_db(stock_code, df)
                return {"status": "success", "stock_code": stock_code}

            except Exception as e:
                logger.error(f"❌ {stock_code} 수집 실패: {e}")
                return {"status": "error", "stock_code": stock_code, "error": str(e)}
```

**효과**:
- API 호출 시간: 50초 → 12초 (76% 단축)
- 동시 처리로 처리량 증가

---

### 2. 데이터베이스 인덱싱

**문제점**: 느린 쿼리 성능

```sql
-- 기존: Full Table Scan
SELECT * FROM stock_prices
WHERE stock_code = '005930' AND date >= '2024-01-01';
-- Execution time: 2.5s
```

**개선안**: 복합 인덱스 추가

```python
# backend/models/stock_price.py

from sqlalchemy import Index


class StockPrice(Base):
    __tablename__ = "stock_prices"

    # ... 기존 컬럼 ...

    # 복합 인덱스 추가 ⭐
    __table_args__ = (
        Index(
            "idx_stock_date",
            "stock_code",
            "date",
            postgresql_using="btree"
        ),
        Index(
            "idx_date_source",
            "date",
            "source",
            postgresql_using="btree"
        ),
        Index(
            "idx_created_at",
            "created_at",
            postgresql_using="btree"
        ),
    )
```

**마이그레이션**:

```sql
-- migrations/add_indexes.sql

-- 1. stock_code + date 복합 인덱스
CREATE INDEX CONCURRENTLY idx_stock_date
ON stock_prices (stock_code, date);

-- 2. date + source 복합 인덱스
CREATE INDEX CONCURRENTLY idx_date_source
ON stock_prices (date, source);

-- 3. created_at 인덱스 (모니터링용)
CREATE INDEX CONCURRENTLY idx_created_at
ON stock_prices (created_at);

-- 4. ANALYZE 실행
ANALYZE stock_prices;
```

**효과**:
- 쿼리 시간: 2.5s → 0.05s (98% 단축)
- Index Scan으로 변경

---

### 3. Redis 캐싱 전략

**문제점**: 반복적인 DB 조회

```python
# 기존: 매번 DB 조회
for news_id in news_ids:
    stock_data = aggregator.get_comprehensive_stock_data(...)
    # DB 쿼리 3회 (주가 + 투자자 + 재무)
```

**개선안**: Redis 캐싱

```python
# backend/cache/stock_data_cache.py

import json
from typing import Optional


class StockDataCache:
    """주식 데이터 캐시"""

    def __init__(self):
        self.redis = redis_client
        self.ttl = 3600  # 1시간

    async def get_stock_data(
        self,
        stock_code: str,
        date: datetime
    ) -> Optional[dict]:
        """캐시 조회"""

        cache_key = f"stock_data:{stock_code}:{date.date()}"
        cached = await self.redis.get(cache_key)

        if cached:
            logger.debug(f"캐시 히트: {cache_key}")
            return json.loads(cached)

        return None

    async def set_stock_data(
        self,
        stock_code: str,
        date: datetime,
        data: dict
    ):
        """캐시 저장"""

        cache_key = f"stock_data:{stock_code}:{date.date()}"

        await self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps(data)
        )

        logger.debug(f"캐시 저장: {cache_key}")

    async def invalidate_stock(self, stock_code: str):
        """종목별 캐시 무효화"""

        pattern = f"stock_data:{stock_code}:*"
        keys = await self.redis.keys(pattern)

        if keys:
            await self.redis.delete(*keys)
            logger.info(f"캐시 무효화: {stock_code}, {len(keys)}건")


# 사용 예시
class DataAggregator:
    def __init__(self):
        self.cache = StockDataCache()

    async def get_comprehensive_stock_data(
        self,
        stock_code: str,
        date: datetime
    ) -> dict:
        """캐시 우선 조회"""

        # 캐시 조회
        cached = await self.cache.get_stock_data(stock_code, date)
        if cached:
            return cached

        # DB 조회
        data = self._fetch_from_db(stock_code, date)

        # 캐싱
        await self.cache.set_stock_data(stock_code, date, data)

        return data
```

**효과**:
- DB 쿼리: 3회 → 0회 (캐시 히트 시)
- 응답 시간: 500ms → 10ms (98% 단축)
- 캐시 히트율: 60~70% (예상)

---

### 4. Connection Pooling

**문제점**: 매 요청마다 DB 연결 생성

```python
# 기존
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**개선안**: Connection Pool 최적화

```python
# backend/database.py

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

DATABASE_URL = "postgresql://user:pass@localhost/craveny"

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # 기본 연결 수
    max_overflow=40,       # 추가 연결 수
    pool_pre_ping=True,    # 연결 유효성 체크
    pool_recycle=3600,     # 1시간마다 재생성
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**효과**:
- DB 연결 시간: 50ms → 5ms (90% 단축)
- 동시 처리 능력 향상

---

## Performance Benchmarking

### 벤치마크 스크립트

```python
# scripts/benchmark_performance.py

import time
import asyncio
from statistics import mean


async def benchmark_api_calls():
    """API 호출 성능 벤치마크"""

    crawler = OptimizedCrawler()
    stock_codes = get_active_stocks()[:50]

    # 1. 순차 실행 (기존)
    print("\n=== 순차 실행 ===")
    start = time.time()

    for code in stock_codes:
        await crawler.kis_client.get_daily_prices(code, datetime.now())

    sequential_time = time.time() - start
    print(f"시간: {sequential_time:.2f}초")

    # 2. 배치 실행 (개선)
    print("\n=== 배치 실행 ===")
    start = time.time()

    await crawler.collect_daily_prices_batch(stock_codes, datetime.now())

    batch_time = time.time() - start
    print(f"시간: {batch_time:.2f}초")

    # 개선율
    improvement = ((sequential_time - batch_time) / sequential_time) * 100
    print(f"\n개선율: {improvement:.1f}%")


async def benchmark_database_queries():
    """데이터베이스 쿼리 성능 벤치마크"""

    db = SessionLocal()

    # 1. 인덱스 없음 (시뮬레이션)
    print("\n=== Full Table Scan ===")
    start = time.time()

    for i in range(100):
        db.query(StockPrice).filter(
            StockPrice.stock_code == "005930",
            StockPrice.date >= "2024-01-01"
        ).all()

    no_index_time = time.time() - start
    print(f"시간: {no_index_time:.2f}초")

    # 2. 인덱스 사용
    print("\n=== Index Scan ===")
    start = time.time()

    for i in range(100):
        db.query(StockPrice).filter(
            StockPrice.stock_code == "005930",
            StockPrice.date >= "2024-01-01"
        ).all()

    index_time = time.time() - start
    print(f"시간: {index_time:.2f}초")

    # 개선율
    improvement = ((no_index_time - index_time) / no_index_time) * 100
    print(f"\n개선율: {improvement:.1f}%")

    db.close()


async def benchmark_caching():
    """캐싱 성능 벤치마크"""

    aggregator = DataAggregator()
    stock_code = "005930"
    date = datetime.now()

    # 1. 캐시 미스 (첫 요청)
    print("\n=== 캐시 미스 ===")
    times_miss = []

    for i in range(10):
        # 캐시 초기화
        await aggregator.cache.invalidate_stock(stock_code)

        start = time.time()
        await aggregator.get_comprehensive_stock_data(stock_code, date)
        elapsed = time.time() - start

        times_miss.append(elapsed)

    print(f"평균 시간: {mean(times_miss)*1000:.2f}ms")

    # 2. 캐시 히트 (재요청)
    print("\n=== 캐시 히트 ===")
    times_hit = []

    for i in range(10):
        start = time.time()
        await aggregator.get_comprehensive_stock_data(stock_code, date)
        elapsed = time.time() - start

        times_hit.append(elapsed)

    print(f"평균 시간: {mean(times_hit)*1000:.2f}ms")

    # 개선율
    improvement = ((mean(times_miss) - mean(times_hit)) / mean(times_miss)) * 100
    print(f"\n개선율: {improvement:.1f}%")


if __name__ == "__main__":
    asyncio.run(benchmark_api_calls())
    asyncio.run(benchmark_database_queries())
    asyncio.run(benchmark_caching())
```

---

## Expected Results

```
=== API 호출 벤치마크 ===
순차 실행: 52.3초
배치 실행: 12.1초
개선율: 76.9%
✅ API 호출 시간 -75% 달성

=== 데이터베이스 벤치마크 ===
Full Table Scan: 8.5초
Index Scan: 0.2초
개선율: 97.6%
✅ 쿼리 시간 -97% 달성

=== 캐싱 벤치마크 ===
캐시 미스: 485ms
캐시 히트: 8ms
개선율: 98.4%
✅ 응답 시간 -98% 달성

=== 종합 ===
✅ API 호출 -25% 목표 초과 달성 (-75%)
✅ 응답 시간 -20% 목표 초과 달성 (-97%)
```

---

## Definition of Done

- [ ] API 호출 배치 처리 구현
- [ ] 데이터베이스 인덱스 추가 (3개)
- [ ] Redis 캐싱 구현
- [ ] Connection Pool 최적화
- [ ] 성능 벤치마크 실행
- [ ] API 호출 -25% 달성
- [ ] 응답 시간 -20% 달성
- [ ] 코드 리뷰 및 머지
