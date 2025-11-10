# Story 003.3: KIS API 1분봉 데이터 수집기 구현

**Epic**: Epic 003 - 한국투자증권 API Phase 1 Infrastructure
**Status**: ⏸️ Pending Live Test (장중 실전 테스트 대기)
**Priority**: ⭐⭐⭐⭐⭐ (Critical)
**Estimated Effort**: 5-7일
**Dependencies**: Story 003.1, Story 003.2 완료 필수
**Assignee**: Claude Code
**Sprint**: 2025-W45
**Started**: 2025-11-09

---

## 📋 Story Overview

**As a** 시스템,
**I want** KIS API를 통해 1분봉 OHLCV 데이터를 수집하여 DB에 누적하고,
**so that** 장중 실시간 추적 및 다양한 시간대별 차트 분석을 수행할 수 있다.

---

## 🎯 Acceptance Criteria

### 필수 기준 (Must Have)

1. ✅ **DB 마이그레이션**
   - `stock_prices_minute` 테이블 생성
   - 복합 인덱스: `(stock_code, datetime)`
   - UNIQUE 제약: 중복 방지

2. ✅ **KIS API 1분봉 조회 구현**
   - `KISClient.get_minute_prices()` 메서드
   - TR ID 확인 및 구현
   - 당일 1분봉 30건씩 조회

3. ✅ **1분봉 수집기 구현**
   - 50개 종목 순회 수집
   - 병렬 처리 (10개 종목씩 배치)
   - DB 저장 및 중복 체크

4. ✅ **APScheduler 통합**
   - ✅ 장중 9:00~15:30, 1분마다 실행
   - ✅ 시장 시간 체크 (주말/공휴일 skip)
   - ✅ 에러 핸들링 및 알림

5. ✅ **Pandas Resample 유틸**
   - ✅ 1분봉 → 3분/5분/10분/30분/60분봉 변환
   - ✅ OHLCV 집계 함수

### 선택 기준 (Nice to Have)

- 🔹 우선순위 큐 (시가총액 상위 우선)
- 🔹 실패 종목 재시도 로직
- 🔹 수집 현황 대시보드
- 🔹 Grafana 모니터링 연동

---

## 📐 Technical Design

### 1. 아키텍처 다이어그램

```
┌──────────────────────────────────────────────────────┐
│             APScheduler                               │
│   (장중 9:00~15:30, 1분마다)                          │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│         MinutePriceCollector                         │
│  - 50개 종목 순회                                     │
│  - 10개씩 배치 처리                                   │
│  - Rate Limiting (초당 5회)                          │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│           KISClient                                  │
│  - get_minute_prices()                               │
│  - TR ID: FHKST03010200 (추정)                       │
│  - 당일 30건씩 조회                                   │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│         PostgreSQL                                   │
│    stock_prices_minute                               │
│  - datetime (timestamp)                              │
│  - stock_code, OHLCV                                 │
│  - UNIQUE(stock_code, datetime)                      │
└──────────────────────────────────────────────────────┘
```

### 2. 파일 구조

```
backend/
├── crawlers/
│   ├── kis_client.py              # KISClient 확장
│   └── kis_minute_collector.py    # 1분봉 수집기 (NEW)
├── db/
│   ├── models/
│   │   └── stock.py               # StockPriceMinute 모델 추가
│   └── migrations/
│       └── add_minute_table.py    # Migration (NEW)
├── scheduler/
│   └── crawler_scheduler.py       # 1분봉 스케줄 추가
└── utils/
    └── resample.py                # Pandas resample 유틸 (NEW)

scripts/
├── test_kis_minute_collector.py   # 테스트 스크립트 (NEW)
└── backfill_minute_prices.py      # 과거 분봉 백필 (Optional)
```

### 3. DB 스키마

#### `stock_prices_minute` 테이블

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
    source VARCHAR(20) DEFAULT 'kis',
    created_at TIMESTAMP DEFAULT NOW(),

    -- 인덱스
    CONSTRAINT uk_stock_datetime UNIQUE (stock_code, datetime)
);

-- 복합 인덱스
CREATE INDEX idx_minute_stock_datetime ON stock_prices_minute(stock_code, datetime DESC);
CREATE INDEX idx_minute_datetime ON stock_prices_minute(datetime DESC);
CREATE INDEX idx_minute_source ON stock_prices_minute(source);

-- 파티셔닝 (Optional, 나중에)
-- ALTER TABLE stock_prices_minute PARTITION BY RANGE (datetime);
```

### 4. KIS API 1분봉 조회

#### TR ID 조사

KIS API 문서에서 1분봉 조회 TR ID를 확인해야 합니다:
- 추정 TR ID: `FHKST03010200` (국내주식 분봉 조회)
- 또는: `FHKST03010300` (국내주식 체결가 조회)

**API 엔드포인트**:
```
GET /uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice
```

**Request Parameters**:
```python
{
    "FID_COND_MRKT_DIV_CODE": "J",     # 시장 구분 (J: 주식)
    "FID_INPUT_ISCD": "005930",        # 종목 코드
    "FID_INPUT_HOUR_1": "090000",      # 시작 시간 (HHMMSS)
    "FID_PW_DATA_INCU_YN": "N"         # 과거 데이터 포함 여부
}
```

**Response Format**:
```json
{
    "rt_cd": "0",
    "output1": {
        "prdt_type_cd": "300"
    },
    "output2": [
        {
            "stck_bsop_date": "20251109",
            "stck_cntg_hour": "153000",
            "stck_prpr": "59000",
            "stck_oprc": "59100",
            "stck_hgpr": "59200",
            "stck_lwpr": "58900",
            "cntg_vol": "123456"
        }
    ]
}
```

### 5. 1분봉 수집 전략

#### 병렬 처리

```python
# 10개 종목씩 배치
batch_size = 10

for i in range(0, len(stock_codes), batch_size):
    batch = stock_codes[i:i + batch_size]

    # 병렬 수집
    tasks = [collect_minute_data(code) for code in batch]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Rate limiting (초당 5회 제한)
    if i + batch_size < len(stock_codes):
        await asyncio.sleep(0.2)
```

#### 우선순위 큐 (Optional)

```python
# 시가총액 순으로 정렬
stocks_sorted = sorted(stocks, key=lambda s: s.market_cap, reverse=True)

# Priority 1 종목 우선 수집
priority_1 = [s for s in stocks_sorted if s.priority == 1]
priority_2 = [s for s in stocks_sorted if s.priority == 2]
```

### 6. Pandas Resample 유틸

#### `backend/utils/resample.py`

```python
"""
1분봉 → N분봉 변환 유틸리티
"""
import pandas as pd
from typing import Literal


TimeFrame = Literal["1T", "3T", "5T", "10T", "30T", "60T"]


def resample_ohlcv(
    df: pd.DataFrame,
    timeframe: TimeFrame = "5T"
) -> pd.DataFrame:
    """
    1분봉 → N분봉 변환

    Args:
        df: 1분봉 DataFrame (columns: datetime, open, high, low, close, volume)
        timeframe: 시간 단위 (1T=1분, 5T=5분, 60T=60분)

    Returns:
        Resampled DataFrame
    """
    # datetime을 인덱스로 설정
    df = df.copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    # Resample
    resampled = df.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    # NaN 제거
    resampled = resampled.dropna()

    # 인덱스를 컬럼으로 복원
    resampled.reset_index(inplace=True)

    return resampled
```

---

## 📝 Implementation Tasks

### Task 1: DB Migration (0.5일)

**목표**: `stock_prices_minute` 테이블 생성

**파일**: `backend/db/migrations/add_minute_table.py`

```python
"""
1분봉 테이블 추가 Migration
"""
from sqlalchemy import text
from backend.db.session import SessionLocal


def upgrade():
    """Migration 실행"""
    db = SessionLocal()

    try:
        # 테이블 생성
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS stock_prices_minute (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(10) NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT,
                source VARCHAR(20) DEFAULT 'kis',
                created_at TIMESTAMP DEFAULT NOW(),

                CONSTRAINT uk_stock_datetime UNIQUE (stock_code, datetime)
            );
        """))

        # 인덱스 생성
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_stock_datetime
            ON stock_prices_minute(stock_code, datetime DESC);
        """))

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_datetime
            ON stock_prices_minute(datetime DESC);
        """))

        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_minute_source
            ON stock_prices_minute(source);
        """))

        db.commit()
        print("✅ Migration 완료: stock_prices_minute 테이블 생성")

    except Exception as e:
        db.rollback()
        print(f"❌ Migration 실패: {e}")
        raise

    finally:
        db.close()


def downgrade():
    """Migration 롤백"""
    db = SessionLocal()

    try:
        db.execute(text("DROP TABLE IF EXISTS stock_prices_minute;"))
        db.commit()
        print("✅ Rollback 완료: stock_prices_minute 테이블 삭제")

    except Exception as e:
        db.rollback()
        print(f"❌ Rollback 실패: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    upgrade()
```

**실행**:
```bash
uv run python backend/db/migrations/add_minute_table.py
```

**검증**:
```sql
-- 테이블 확인
\d stock_prices_minute

-- 인덱스 확인
\di stock_prices_minute*
```

---

### Task 2: StockPriceMinute 모델 추가 (0.5일)

**목표**: ORM 모델 추가

**파일**: `backend/db/models/stock.py` (확장)

```python
# 기존 모델 아래에 추가

class StockPriceMinute(Base):
    """1분봉 주가 데이터"""

    __tablename__ = "stock_prices_minute"

    id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(String(10), ForeignKey("stocks.code"), nullable=False)
    datetime = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger)
    source = Column(String(20), default="kis")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    stock = relationship("Stock", back_populates="minute_prices")

    # 인덱스 (복합 인덱스)
    __table_args__ = (
        Index("idx_minute_stock_datetime", "stock_code", "datetime"),
        UniqueConstraint("stock_code", "datetime", name="uk_stock_datetime"),
    )
```

**Stock 모델 업데이트**:
```python
class Stock(Base):
    # ... 기존 코드 ...

    # 관계 추가
    minute_prices = relationship("StockPriceMinute", back_populates="stock")
```

---

### Task 3: KIS API 1분봉 조회 구현 (1일)

**목표**: `KISClient.get_minute_prices()` 메서드 추가

**파일**: `backend/crawlers/kis_client.py` (확장)

---

## ⏱️ Estimated Timeline

| Task | Estimated | Status |
|------|-----------|--------|
| Task 1: DB Migration | 0.5일 | ✅ Done |
| Task 2: ORM 모델 추가 | 0.5일 | ✅ Done |
| Task 3: KIS API 1분봉 조회 | 1일 | ✅ Done |
| Task 4: 1분봉 수집기 구현 | 2일 | ✅ Done |
| Task 5: APScheduler 통합 | 0.5일 | ✅ Done |
| Task 6: Pandas Resample 유틸 | 0.5일 | ✅ Done |
| Task 7: 테스트 & 검증 | 1일 | 📋 Ready |
| **Total** | **6일** | |

---

## ✅ Definition of Done

- [x] `stock_prices_minute` 테이블 생성 및 인덱스 확인 ✅
- [x] `StockPriceMinute` ORM 모델 추가 ✅
- [x] `KISClient.get_minute_prices()` 구현 및 테스트 ✅
- [x] `MinutePriceCollector` 구현 ✅
- [x] APScheduler 통합 (장중 1분마다 실행) ✅
- [x] Pandas resample 유틸 함수 작성 및 테스트 ✅
- [x] SK하이닉스 1분봉 데이터 수집 성공 ✅
- [ ] 50개 종목 × 390분 = 19,500건 수집 성공 (1일 기준) - 장중 테스트 대기
- [ ] 수집 성공률 ≥98% 검증 - 장중 테스트 대기
- [x] 통합 테스트 통과 ✅

**추가 구현 사항**:
- [x] 일별 1분봉 API (`get_daily_minute_prices()`) ✅
- [x] 시장 시간 체크 유틸 (`market_hours.py`) ✅

---

## 📝 Implementation Log

### 2025-11-09: Story 003.3 작업 시작

**Task 1: DB Migration ✅ 완료**
- `backend/db/migrations/add_minute_table.py` 생성
- `stock_prices_minute` 테이블 생성 완료
- 5개 인덱스 생성: Primary Key, Unique Constraint, 3개 복합 인덱스
- Foreign Key 제약 추가 (`stocks.code` 참조)

**Task 2: ORM 모델 추가 ✅ 완료**
- `backend/db/models/stock.py`에 `StockPriceMinute` 클래스 추가
- `BigInteger` import 추가 (volume 컬럼용)
- `backend/db/models/__init__.py`에서 export
- 모델 import 및 동작 검증 완료

**Task 3: KIS API 1분봉 조회 구현 ✅ 완료**
- `KISClient.get_minute_prices()` 메서드 추가 완료
- TR ID: `FHKST03010200` (국내주식 분봉 조회)
- 엔드포인트: `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice`
- ✅ **API 정상 동작 확인**
  - 실전투자 API로 30건의 1분봉 데이터 수신 성공
  - 필수 파라미터: `FID_ETC_CLS_CODE`, `FID_PW_DATA_INCU_YN=Y`
  - Response 필드: `stck_bsop_date`, `stck_cntg_hour`, `stck_prpr`, `stck_oprc`, `stck_hgpr`, `stck_lwpr`, `cntg_vol`
- **중요 개선사항**: Redis 토큰 저장소 구현 완료
  - 토큰을 Redis에 저장하여 프로세스 간 공유
  - 24시간 동안 토큰 재사용, 만료 5분 전 자동 갱신
  - 1분당 1회 토큰 발급 Rate Limit 완벽 회피
  - 프로세스 재시작 후에도 기존 토큰 활용

**Task 4: 1분봉 수집기 구현 ✅ 완료**
- `MinutePriceCollector` 클래스 구현 완료
- 배치 처리 (10개씩 병렬 수집) 구현
- DB 저장 및 중복 체크 완료
- 테스트 성공: 5개 종목 × 30건 = 150건 수집 (0.9초)
- Rate Limiting 및 에러 핸들링 완료

**Task 5: APScheduler 통합 ✅ 완료**
- `backend/utils/market_hours.py` 구현
  - `is_market_open()`: 장 시간 체크 (09:00-15:30, 주말/공휴일 제외)
  - `is_trading_day()`: 거래일 확인
  - `get_next_market_open()`: 다음 장 시작 시간
  - 2025년 한국 공휴일 데이터 포함
- `backend/scheduler/crawler_scheduler.py` 수정
  - `_collect_kis_minute_prices()` 메서드 추가
  - 1분봉 수집 통계 변수 추가 (`kis_minute_total_*`)
  - IntervalTrigger(minutes=1) 등록 - 매 1분마다 실행
  - `get_stats()`에 1분봉 통계 포함
- 테스트 성공: 스케줄러 정상 동작, 장 시간 체크 검증

**Task 6: Pandas Resample 유틸 ✅ 완료**
- `backend/utils/resample.py` 구현
  - `resample_ohlcv()`: 1분봉 → 3/5/10/30/60분봉 변환
  - `fetch_and_resample()`: DB 조회 + Resample 통합
  - `resample_to_multiple_timeframes()`: 여러 시간대 한 번에 변환
  - `get_common_timeframes()`: 일반 timeframe 매핑
  - `validate_timeframe()`: Timeframe 유효성 검사
- 테스트 성공: 5개 테스트 모두 통과
  - 기본 Resample (10분 → 5분봉: 2개)
  - 여러 시간대 (60분 → 3/5/10/30/60분봉)
  - Timeframe 매핑 및 유효성 검사
  - DB 조회 및 Resample 통합

**Task 7: 테스트 & 검증 ✅ 완료**
- `scripts/test_integration_minute_collector.py` 작성
- SK하이닉스(000660) 통합 테스트 성공
  - ✅ API 조회: 30건 (0.1초)
  - ✅ DB 저장: 중복 방지 정상 동작
  - ✅ DB 조회: 정상 동작
  - ✅ Resample: 3T/5T/10T 변환 성공
  - ✅ 테이블 통계: 49개 종목 × 30건 = 1,470건 저장 확인
- **일별 1분봉 API 추가 구현** (선택사항)
  - `KISClient.get_daily_minute_prices()` 메서드 추가
  - TR_ID: `FHKST03010230` (과거 일자 조회)
  - 최대 120건/회, 1년치 데이터 조회 가능
  - 실전투자 전용 (모의투자 미지원)

**전체 시스템 통합 검증**:
- ✅ DB Migration → ORM 모델 → API → 수집기 → 스케줄러 → Resample 전 과정 정상 동작
- ✅ 49개 종목 1분봉 데이터 수집 및 저장 성공
- ✅ 중복 방지 (UNIQUE 제약) 정상 작동
- ✅ 장 시간 체크 정상 작동 (주말/공휴일 스킵)
- ✅ Pandas Resample 유틸 정상 작동 (1분봉 → 3/5/10/30/60분봉)

**📌 장중 실전 테스트 체크리스트** (다음 거래일 09:00-15:30):
- [ ] 스케줄러 실행 확인 (매 1분마다)
- [ ] 50개 종목 자동 수집 확인
- [ ] 1일 수집 목표: 50개 종목 × 390분 = 19,500건
- [ ] 수집 성공률 ≥98% 검증
- [ ] 에러 로그 확인 및 모니터링
- [ ] DB 용량 및 성능 확인
- [ ] 완료 후 Story 003.3 ✅ Done 처리

**다음 작업**:
- Epic 003의 다른 Story 진행 또는
- 새로운 Epic/Story 시작
