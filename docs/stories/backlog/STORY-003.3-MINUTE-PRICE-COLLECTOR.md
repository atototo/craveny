# Story 003.3: KIS API 1분봉 데이터 수집기 구현 및 DB 누적

**Epic**: Epic 003 - 한국투자증권 API Phase 1 Infrastructure
**Status**: 📋 Ready
**Priority**: ⭐⭐⭐⭐⭐ (Critical - 실시간 추적 핵심)
**Estimated Effort**: 5-7일
**Dependencies**: Story 003.1, 003.2 완료 필수
**Assignee**: TBD
**Sprint**: TBD

---

## 📋 Story Overview

**As a** 시스템,
**I want** 장중(9:00~15:30) 매 1분마다 50개 종목의 1분봉 데이터를 수집하여 DB에 누적하고,
**so that** 장중 급변 감지 및 정밀한 뉴스-주가 매칭에 활용할 수 있다.

### 💡 핵심 가치

- ⏰ **실시간 추적**: 뉴스 발표 후 장중 주가 반응 정밀 추적
- 📊 **고해상도 데이터**: 일봉 대비 390배 상세한 데이터 (390분 × 50종목 = 19,500건/일)
- 🎯 **급변 감지 기반**: Phase 3 실시간 시스템의 근간

---

## 🎯 Acceptance Criteria

### 필수 기준 (Must Have)

1. ✅ **PostgreSQL 테이블 생성**
   - `stock_prices_minute` 테이블 생성
   - 컬럼: stock_code, datetime, open, high, low, close, volume, source
   - 인덱스: `idx_minute_stock_datetime (stock_code, datetime)`
   - UNIQUE: `uk_stock_datetime (stock_code, datetime)`

2. ✅ **KIS API 1분봉 조회 구현**
   - 당일 1분봉 데이터 조회 (최대 30개 레코드/요청)
   - 반복 호출로 전체 시간대 수집 (9:00~15:30)
   - OHLCV 파싱 및 DataFrame 변환

3. ✅ **1분봉 수집기 구현**
   - 50개 종목 병렬 수집
   - 중복 데이터 방지 (datetime 기준)
   - 수집 성공률 ≥98%
   - 장중 자동 실행 (9:00~15:30, 매 1분)

4. ✅ **APScheduler 작업 등록**
   - Cron: 9:00~15:30, 매 1분 실행
   - 장 시간대 체크 (주말/공휴일/장 마감 후 skip)
   - 에러 핸들링 및 재시도

5. ✅ **데이터 검증**
   - 일일 수집 목표: 19,500건 (50종목 × 390분)
   - 실제 수집률: ≥98% (약 19,100건 이상)
   - 데이터 연속성 확인 (시간 gap 감지)

### 선택 기준 (Nice to Have)

- 🔹 실시간 수집 현황 대시보드
- 🔹 분봉 → 5분봉/10분봉/30분봉 자동 변환 (Pandas resample)
- 🔹 메모리 최적화 (배치 삽입)

---

## 📐 Technical Design

### 1. 아키텍처 다이어그램

```
┌──────────────────┐
│  APScheduler     │
│  (Every minute   │
│   9:00~15:30)    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│ MinuteCollector  │────►│  KIS Client     │
│  (50 stocks)     │     │  (Rate 20/sec)  │
└────────┬─────────┘     └─────────────────┘
         │
         ▼
┌──────────────────┐
│  PostgreSQL      │
│  stock_prices_   │
│  minute          │
│  (Partitioned)   │
└──────────────────┘
```

### 2. 파일 구조

```
backend/
├── crawlers/
│   └── kis_minute_collector.py   # 1분봉 수집기
├── db/
│   ├── models/
│   │   └── stock.py               # StockPriceMinute ORM 추가
│   └── migrations/
│       └── create_minute_table.sql
└── schedulers/
    └── stock_scheduler.py         # 1분봉 작업 추가

scripts/
└── backfill_minute_prices.py      # 당일 분봉 백필

tests/
└── crawlers/
    └── test_kis_minute_collector.py
```

### 3. 데이터 모델

#### 3.1 StockPriceMinute Model

```python
# backend/db/models/stock.py

class StockPriceMinute(Base):
    """1분봉 데이터 모델"""

    __tablename__ = "stock_prices_minute"

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    datetime = Column(DateTime, nullable=False, index=True)

    # OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger)

    # 메타데이터
    source = Column(String(20), default='KIS', nullable=False)
    created_at = Column(DateTime, default=func.now())

    # 제약 조건
    __table_args__ = (
        UniqueConstraint('stock_code', 'datetime', name='uk_stock_datetime'),
        Index('idx_minute_stock_datetime', 'stock_code', 'datetime'),
    )
```

#### 3.2 테이블 파티셔닝 (선택)

**성능 최적화를 위한 일별 파티셔닝**:

```sql
-- 파티션 테이블 (PostgreSQL 10+)
CREATE TABLE stock_prices_minute (
    id SERIAL,
    stock_code VARCHAR(10) NOT NULL,
    datetime TIMESTAMP NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume BIGINT,
    source VARCHAR(20) DEFAULT 'KIS',
    created_at TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (datetime);

-- 일별 파티션 예시
CREATE TABLE stock_prices_minute_2024_11_08 PARTITION OF stock_prices_minute
FOR VALUES FROM ('2024-11-08 00:00:00') TO ('2024-11-09 00:00:00');

-- 인덱스 (파티션별 자동 생성)
CREATE INDEX ON stock_prices_minute (stock_code, datetime);
```

### 4. KIS API 스펙

#### 4.1 1분봉 시세 조회

```http
GET /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice
Host: openapi.koreainvestment.com:9443

Headers:
  authorization: Bearer {access_token}
  appkey: {app_key}
  appsecret: {app_secret}
  tr_id: FHKST03010200        # 모의투자

Query Parameters:
  FID_ETC_CLS_CODE: ""        # 공백
  FID_COND_MRKT_DIV_CODE: J   # J: 주식
  FID_INPUT_ISCD: 005930      # 종목코드
  FID_INPUT_HOUR_1: 000000    # 시작 시각 (HHmmss, 000000=당일 시작)
  FID_PW_DATA_INCU_YN: Y      # Y: 과거 데이터 포함

Response:
{
  "rt_cd": "0",
  "msg1": "정상처리 되었습니다.",
  "output2": [
    {
      "stck_bsop_date": "20241108",  // 날짜
      "stck_cntg_hour": "153000",    // 시각 (HHmmss)
      "stck_prpr": "72500",          // 현재가 (=종가)
      "stck_oprc": "72000",          // 시가
      "stck_hgpr": "72600",          // 고가
      "stck_lwpr": "71900",          // 저가
      "cntg_vol": "123456"           // 거래량
    },
    // ... 최대 30개
  ]
}
```

**제약 사항**:
- ⚠️ **당일 데이터만** 조회 가능 (과거 분봉 조회 불가)
- ⚠️ 최대 30개 레코드 반환 → 반복 호출 필요
- ⚠️ `FID_INPUT_HOUR_1`: 시작 시각 지정 (예: 090000 = 9시부터)

---

## 🔧 Implementation Tasks

### Task 1: PostgreSQL 테이블 생성 (0.5일)

**Migration Script**: `backend/db/migrations/create_minute_table.sql`

```sql
-- 1분봉 테이블 생성
CREATE TABLE IF NOT EXISTS stock_prices_minute (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    datetime TIMESTAMP NOT NULL,

    -- OHLCV
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume BIGINT,

    -- 메타데이터
    source VARCHAR(20) DEFAULT 'KIS' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    -- 제약 조건
    CONSTRAINT uk_stock_datetime UNIQUE (stock_code, datetime)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_minute_stock_datetime
ON stock_prices_minute (stock_code, datetime DESC);

CREATE INDEX IF NOT EXISTS idx_minute_datetime
ON stock_prices_minute (datetime DESC);

-- 통계 업데이트
ANALYZE stock_prices_minute;

-- 코멘트
COMMENT ON TABLE stock_prices_minute IS '주식 1분봉 데이터';
COMMENT ON COLUMN stock_prices_minute.datetime IS '체결 시각 (분 단위, 예: 2024-11-08 09:01:00)';
```

**실행**:
```bash
# psql 실행
psql -U postgres -d craveny -f backend/db/migrations/create_minute_table.sql
```

**또는 Python 마이그레이션**:
```python
# scripts/migrate_minute_table.py
from sqlalchemy import text
from backend.db.session import SessionLocal

def create_minute_table():
    with open("backend/db/migrations/create_minute_table.sql") as f:
        sql = f.read()

    db = SessionLocal()
    try:
        db.execute(text(sql))
        db.commit()
        print("✅ stock_prices_minute 테이블 생성 완료")
    except Exception as e:
        db.rollback()
        print(f"❌ 실패: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_minute_table()
```

---

### Task 2: KIS API 1분봉 조회 구현 (1.5일)

**Code**: `backend/kis/client.py` (확장)

```python
# ... 기존 KISClient 클래스에 추가

from typing import Literal


class KISClient:
    # ... 기존 코드 ...

    async def get_minute_prices(
        self,
        stock_code: str,
        start_time: str = "000000",
        end_time: str = "153000"
    ) -> pd.DataFrame:
        """
        1분봉 시세 조회 (당일 데이터만)

        Args:
            stock_code: 종목 코드 (6자리)
            start_time: 시작 시각 (HHmmss, 기본: 000000=당일 시작)
            end_time: 종료 시각 (HHmmss, 기본: 153000=장 마감)

        Returns:
            DataFrame (columns: datetime, open, high, low, close, volume)

        Note:
            - 당일 데이터만 조회 가능
            - 최대 30개 레코드/요청 → 반복 호출 필요
        """
        all_data = []

        current_start_time = start_time

        # tr_id: 모의투자 vs 실전투자
        tr_id = "VHKST03010200" if self.config.is_mock else "FHKST03010200"

        while True:
            # 요청 파라미터
            params = {
                "FID_ETC_CLS_CODE": "",
                "FID_COND_MRKT_DIV_CODE": "J",  # J: 주식
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_HOUR_1": current_start_time,
                "FID_PW_DATA_INCU_YN": "Y"
            }

            headers = {
                "tr_id": tr_id
            }

            # API 호출
            response = await self.get(
                endpoint="/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                headers=headers,
                params=params
            )

            # 응답 파싱
            output = response.get("output2", [])

            if not output:
                logger.debug(f"No more data for {stock_code} after {current_start_time}")
                break

            all_data.extend(output)

            # 마지막 시각 확인
            last_time = output[-1]["stck_cntg_hour"]

            # 종료 시각 도달 또는 30개 미만 (마지막 페이지)
            if last_time >= end_time or len(output) < 30:
                break

            # 다음 시작 시각 설정 (+1분)
            last_hour = int(last_time[:2])
            last_minute = int(last_time[2:4])

            last_minute += 1
            if last_minute >= 60:
                last_hour += 1
                last_minute = 0

            current_start_time = f"{last_hour:02d}{last_minute:02d}00"

            logger.debug(f"Fetching next batch from {current_start_time}")

        if not all_data:
            logger.warning(f"No minute data for {stock_code}")
            return pd.DataFrame()

        # DataFrame 변환
        df = pd.DataFrame(all_data)

        # 컬럼 매핑
        df = df.rename(columns={
            "stck_bsop_date": "date",
            "stck_cntg_hour": "time",
            "stck_oprc": "open",
            "stck_hgpr": "high",
            "stck_lwpr": "low",
            "stck_prpr": "close",
            "cntg_vol": "volume"
        })

        # datetime 생성
        df["datetime"] = pd.to_datetime(
            df["date"] + df["time"],
            format="%Y%m%d%H%M%S"
        )

        # 데이터 타입 변환
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(int)

        # 정렬
        df = df.sort_values("datetime").reset_index(drop=True)

        logger.debug(f"Fetched {len(df)} minute bars for {stock_code}")

        return df[["datetime", "open", "high", "low", "close", "volume"]]
```

**검증**:
```python
# 테스트
async def test_minute_prices():
    async with get_kis_client() as client:
        df = await client.get_minute_prices("005930")  # 삼성전자
        print(f"Total records: {len(df)}")
        print(df.head())
        print(df.tail())

asyncio.run(test_minute_prices())
```

---

### Task 3: 1분봉 수집기 구현 (2.5일)

**Code**: `backend/crawlers/kis_minute_collector.py`

```python
"""
KIS API 1분봉 데이터 수집기
"""
import logging
from datetime import datetime, time
from typing import List, Dict

import pandas as pd
from sqlalchemy.orm import Session

from backend.kis.client import get_kis_client
from backend.db.models.stock import StockPriceMinute
from backend.db.session import SessionLocal
from backend.utils.stock_loader import load_target_stocks


logger = logging.getLogger(__name__)


class KISMinuteCollector:
    """KIS API 1분봉 수집기"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.should_close_db = db is None

    def is_market_hours(self) -> bool:
        """
        현재 장 시간인지 확인

        Returns:
            True: 9:00~15:30, False: 그 외
        """
        now = datetime.now()

        # 주말 체크
        if now.weekday() >= 5:
            return False

        # 시간 체크 (9:00~15:30)
        market_open = time(9, 0)
        market_close = time(15, 30)

        current_time = now.time()

        return market_open <= current_time <= market_close

    async def collect_minute_prices(
        self,
        stock_codes: List[str] = None,
        start_time: str = "090000",
        end_time: str = "153000"
    ) -> Dict[str, int]:
        """
        1분봉 데이터 수집 및 DB 저장

        Args:
            stock_codes: 종목 코드 리스트 (None이면 전체 50개)
            start_time: 시작 시각 (HHmmss)
            end_time: 종료 시각 (HHmmss)

        Returns:
            {stock_code: 저장 건수} 딕셔너리
        """
        if not self.is_market_hours():
            logger.info("장 시간이 아니므로 수집 skip")
            return {}

        if stock_codes is None:
            target_stocks = load_target_stocks()
            stock_codes = [stock["code"] for stock in target_stocks]

        results = {}

        async with get_kis_client() as kis_client:
            for stock_code in stock_codes:
                try:
                    logger.debug(f"Collecting minute prices for {stock_code}")

                    # KIS API 호출
                    df = await kis_client.get_minute_prices(
                        stock_code=stock_code,
                        start_time=start_time,
                        end_time=end_time
                    )

                    if df.empty:
                        logger.warning(f"No minute data for {stock_code}")
                        results[stock_code] = 0
                        continue

                    # DB 저장
                    saved_count = self._save_to_db(stock_code, df)
                    results[stock_code] = saved_count

                    logger.debug(f"✅ {stock_code}: {saved_count}건 저장")

                except Exception as e:
                    logger.error(f"❌ {stock_code} 수집 실패: {e}")
                    results[stock_code] = 0

        # 결과 요약
        total_saved = sum(results.values())
        success_count = sum(1 for count in results.values() if count > 0)

        logger.info(
            f"1분봉 수집 완료: {success_count}/{len(stock_codes)}개 종목, "
            f"총 {total_saved}건 저장"
        )

        return results

    def _save_to_db(self, stock_code: str, df: pd.DataFrame) -> int:
        """
        DataFrame을 DB에 저장

        Args:
            stock_code: 종목 코드
            df: 1분봉 DataFrame

        Returns:
            저장된 레코드 수
        """
        saved_count = 0

        try:
            for _, row in df.iterrows():
                # 중복 체크
                existing = (
                    self.db.query(StockPriceMinute)
                    .filter(
                        StockPriceMinute.stock_code == stock_code,
                        StockPriceMinute.datetime == row["datetime"],
                    )
                    .first()
                )

                if existing:
                    # 업데이트
                    existing.open = float(row["open"])
                    existing.high = float(row["high"])
                    existing.low = float(row["low"])
                    existing.close = float(row["close"])
                    existing.volume = int(row["volume"])
                    existing.source = "KIS"
                else:
                    # 삽입
                    minute_price = StockPriceMinute(
                        stock_code=stock_code,
                        datetime=row["datetime"],
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                        source="KIS"
                    )
                    self.db.add(minute_price)

                saved_count += 1

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"DB 저장 실패: {stock_code}, {e}")
            return 0

        return saved_count

    def __del__(self):
        if self.should_close_db and self.db:
            self.db.close()


# 싱글톤 팩토리
def get_minute_collector(db: Session = None) -> KISMinuteCollector:
    return KISMinuteCollector(db)
```

---

### Task 4: APScheduler 작업 등록 (1일)

**Code**: `backend/schedulers/stock_scheduler.py` (확장)

```python
# ... 기존 imports에 추가
from backend.crawlers.kis_minute_collector import get_minute_collector


async def collect_minute_prices_job():
    """
    1분봉 수집 작업 (매 1분 실행, 9:00~15:30)
    """
    collector = get_minute_collector()

    # 장 시간 체크
    if not collector.is_market_hours():
        return

    try:
        results = await collector.collect_minute_prices()

        total = len(results)
        success = sum(1 for count in results.values() if count > 0)
        total_saved = sum(results.values())

        logger.info(
            f"📊 1분봉 수집: {success}/{total}개 종목, {total_saved}건 저장"
        )

        # 실패 종목 로깅
        if success < total:
            failed = [code for code, count in results.items() if count == 0]
            logger.warning(f"실패 종목: {failed}")

    except Exception as e:
        logger.error(f"1분봉 수집 실패: {e}", exc_info=True)


def start_scheduler():
    """스케줄러 시작"""
    # ... 기존 일봉 작업 ...

    # 1분봉 수집: 매 1분 (9:00~15:30)
    scheduler.add_job(
        collect_minute_prices_job,
        trigger=CronTrigger(
            day_of_week="mon-fri",
            hour="9-15",
            minute="*",  # 매 1분
            timezone="Asia/Seoul"
        ),
        id="kis_minute_collector",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Stock Scheduler started (with minute collection)")
```

**실행 주기**:
- 월~금요일
- 9시~15시, 매 1분마다
- 총 실행 횟수: 390회/일 (6.5시간 × 60분)

---

### Task 5: 당일 분봉 백필 스크립트 (1일)

**Code**: `scripts/backfill_minute_prices.py`

```python
"""
당일 1분봉 데이터 백필 스크립트

장 마감 후 누락된 데이터를 일괄 수집합니다.
"""
import asyncio
import logging
from datetime import datetime
from tqdm import tqdm

from backend.crawlers.kis_minute_collector import get_minute_collector
from backend.utils.stock_loader import load_target_stocks


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_today_minutes():
    """
    당일 1분봉 백필
    """
    logger.info("당일 1분봉 백필 시작")

    # 종목 리스트
    target_stocks = load_target_stocks()
    stock_codes = [stock["code"] for stock in target_stocks]

    logger.info(f"대상 종목: {len(stock_codes)}개")

    collector = get_minute_collector()

    # 배치 처리 (10개씩)
    results = {}

    with tqdm(total=len(stock_codes), desc="백필 진행") as pbar:
        batch_size = 10

        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i + batch_size]

            batch_results = await collector.collect_minute_prices(
                stock_codes=batch,
                start_time="090000",
                end_time="153000"
            )

            results.update(batch_results)
            pbar.update(len(batch))

            # Rate limit 준수
            await asyncio.sleep(1)

    # 결과 요약
    total_saved = sum(results.values())
    success_count = sum(1 for count in results.values() if count > 0)

    logger.info("=" * 50)
    logger.info("백필 완료")
    logger.info(f"성공: {success_count}/{len(stock_codes)}개 종목")
    logger.info(f"총 {total_saved}건 저장")
    logger.info(f"목표 대비: {total_saved / 19500 * 100:.1f}% (목표: 19,500건)")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(backfill_today_minutes())
```

**실행 시점**: 장 마감 후(16:00)

```bash
uv run python scripts/backfill_minute_prices.py
```

---

### Task 6: 데이터 검증 및 모니터링 (1일)

**검증 쿼리**:

```sql
-- 당일 수집 현황
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT stock_code) as stock_count,
    MIN(datetime) as first_time,
    MAX(datetime) as last_time
FROM stock_prices_minute
WHERE DATE(datetime) = CURRENT_DATE;

-- 기대값: 19,500건 (50종목 × 390분)


-- 종목별 수집 현황
SELECT
    stock_code,
    COUNT(*) as record_count,
    MIN(datetime) as first_time,
    MAX(datetime) as last_time
FROM stock_prices_minute
WHERE DATE(datetime) = CURRENT_DATE
GROUP BY stock_code
ORDER BY record_count DESC;

-- 기대값: 각 종목 390건


-- 시간대별 수집 현황
SELECT
    EXTRACT(HOUR FROM datetime) as hour,
    COUNT(*) as record_count
FROM stock_prices_minute
WHERE DATE(datetime) = CURRENT_DATE
GROUP BY hour
ORDER BY hour;

-- 기대값: 9시~15시, 각 시간대 약 3,000건 (50종목 × 60분)
```

**모니터링 API**: `backend/api/endpoints/kis_health.py` (확장)

```python
from pydantic import BaseModel


class MinuteCollectionStatus(BaseModel):
    """1분봉 수집 현황"""
    today_total: int
    expected_total: int
    collection_rate: float
    stock_count: int
    first_time: str | None
    last_time: str | None


@router.get("/minute-status", response_model=MinuteCollectionStatus)
async def get_minute_collection_status():
    """
    1분봉 수집 현황 조회
    """
    from backend.db.session import SessionLocal
    from backend.db.models.stock import StockPriceMinute
    from sqlalchemy import func

    db = SessionLocal()

    try:
        today = datetime.now().date()

        # 오늘 수집 건수
        today_total = (
            db.query(func.count(StockPriceMinute.id))
            .filter(func.date(StockPriceMinute.datetime) == today)
            .scalar()
        )

        # 종목 수
        stock_count = (
            db.query(func.count(func.distinct(StockPriceMinute.stock_code)))
            .filter(func.date(StockPriceMinute.datetime) == today)
            .scalar()
        )

        # 시간 범위
        first_time = db.query(func.min(StockPriceMinute.datetime)).filter(
            func.date(StockPriceMinute.datetime) == today
        ).scalar()

        last_time = db.query(func.max(StockPriceMinute.datetime)).filter(
            func.date(StockPriceMinute.datetime) == today
        ).scalar()

        # 기대값: 50종목 × 390분
        expected_total = 50 * 390  # 19,500

        collection_rate = (today_total / expected_total * 100) if expected_total > 0 else 0

        return MinuteCollectionStatus(
            today_total=today_total,
            expected_total=expected_total,
            collection_rate=round(collection_rate, 2),
            stock_count=stock_count,
            first_time=first_time.isoformat() if first_time else None,
            last_time=last_time.isoformat() if last_time else None
        )

    finally:
        db.close()
```

**API 호출**:
```bash
curl http://localhost:8000/api/kis/minute-status

# 예상 응답
{
  "today_total": 19234,
  "expected_total": 19500,
  "collection_rate": 98.64,
  "stock_count": 50,
  "first_time": "2024-11-08T09:01:00",
  "last_time": "2024-11-08T15:29:00"
}
```

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/crawlers/test_kis_minute_collector.py

import pytest
from datetime import datetime

from backend.crawlers.kis_minute_collector import KISMinuteCollector


@pytest.mark.asyncio
async def test_collect_single_stock():
    """단일 종목 1분봉 수집"""
    collector = KISMinuteCollector()

    results = await collector.collect_minute_prices(
        stock_codes=["005930"],
        start_time="090000",
        end_time="093000"  # 9:00~9:30 (30분)
    )

    assert "005930" in results
    assert results["005930"] >= 25  # 최소 25분 (주말 등 제외)


@pytest.mark.asyncio
async def test_is_market_hours():
    """장 시간 체크 테스트"""
    collector = KISMinuteCollector()

    # 모의 시간 테스트는 pytest-freezegun 사용
    from freezegun import freeze_time

    # 장중 (수요일 10:00)
    with freeze_time("2024-11-06 10:00:00"):
        assert collector.is_market_hours() is True

    # 장 마감 후 (수요일 16:00)
    with freeze_time("2024-11-06 16:00:00"):
        assert collector.is_market_hours() is False

    # 주말 (토요일 10:00)
    with freeze_time("2024-11-09 10:00:00"):
        assert collector.is_market_hours() is False
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_full_day_collection():
    """당일 전체 수집 테스트 (장 마감 후 실행)"""
    collector = KISMinuteCollector()

    results = await collector.collect_minute_prices()

    # 50개 종목 수집
    assert len(results) == 50

    # 총 19,000건 이상 (98% 이상)
    total_saved = sum(results.values())
    assert total_saved >= 19000
```

---

## 🚧 Known Issues & Risks

### 이슈 1: KIS API 1분봉 조회 제약
**Impact**: High | **Probability**: High
**문제**: 당일 데이터만 조회 가능, 과거 분봉 조회 불가
**완화**:
- 매일 장 마감 후 백필 스크립트 실행
- 누락 데이터 자동 감지 및 알림

### 이슈 2: 대용량 데이터 저장 (19,500건/일)
**Impact**: Medium | **Probability**: Medium
**문제**: PostgreSQL 부하 증가
**완화**:
- 테이블 파티셔닝 (일별)
- 배치 삽입 (bulk insert)
- 인덱스 최적화

### 이슈 3: Rate Limit 초과 가능성
**Impact**: Medium | **Probability**: Low
**문제**: 50개 종목 동시 수집 시 20 req/sec 초과
**완화**:
- Rate Limiter 엄격히 적용
- 배치 처리 (10개씩)
- Retry 로직

---

## 📊 Performance Metrics

### 수집 성능 목표
- **수집 주기**: 매 1분 (390회/일)
- **수집 시간**: 평균 10초 이내/종목
- **총 소요 시간**: 약 8-10분/회 (50개 종목)
- **성공률**: ≥98% (19,100건 이상/19,500건)

### 데이터 규모 예상
- **1일**: 19,500건
- **1주**: 97,500건 (5영업일)
- **1개월**: 390,000건 (20영업일)
- **1년**: 4,680,000건 (240영업일)

### 저장 공간 예상
- **1건**: ~100 bytes
- **1일**: 1.95MB
- **1년**: 468MB (압축 전)

---

## ✅ Definition of Done

- [ ] `stock_prices_minute` 테이블 생성
- [ ] `backend/kis/client.py`에 `get_minute_prices()` 구현
- [ ] `backend/crawlers/kis_minute_collector.py` 구현
- [ ] `backend/schedulers/stock_scheduler.py`에 1분봉 작업 등록
- [ ] `scripts/backfill_minute_prices.py` 구현
- [ ] APScheduler 매 1분 실행 검증 (9:00~15:30)
- [ ] 당일 수집률 ≥98% 검증 (19,100건 이상)
- [ ] `/api/kis/minute-status` 엔드포인트 구현
- [ ] 모든 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] main 브랜치 머지
