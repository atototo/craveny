# Story 004.1: 외국인/기관/개인 매매 데이터 수집기 구현

**Epic**: Epic 004 - 한국투자증권 API Phase 2 보조 지표
**Status**: 📋 Ready
**Priority**: ⭐⭐⭐⭐⭐ (Critical - 예측 정확도 핵심)
**Estimated Effort**: 5-7일
**Dependencies**: Epic 003 완료 필수
**Assignee**: TBD
**Sprint**: TBD

---

## 📋 Story Overview

**As a** 주식 분석 시스템,
**I want** 외국인, 기관, 개인 투자자의 일별 매매 데이터를 수집하여,
**so that** LLM이 "스마트 머니" 흐름을 분석하고 예측 정확도를 높일 수 있다.

### 💡 핵심 가치

- 🧠 **스마트 머니 추종**: 외국인/기관의 매수세 분석으로 신뢰도 높은 신호 확보
- 📊 **다차원 분석**: 뉴스 + 주가 + 투자자 매매 → LLM 분석 품질 향상
- 🎯 **예측 정확도**: +15~25%p 개선 목표

---

## 🎯 Acceptance Criteria

### 필수 기준 (Must Have)

1. ✅ **KIS API 투자자 매매 조회 구현**
   - 일별 외국인/기관/개인 매수/매도/순매수 데이터 조회
   - 50개 우선 종목 대상
   - 응답 파싱 및 DataFrame 변환

2. ✅ **PostgreSQL 테이블 생성**
   - `investor_trading` 테이블 생성
   - 컬럼: stock_code, date, foreign_buy/sell/net, institution_buy/sell/net, individual_buy/sell/net
   - UNIQUE: (stock_code, date)
   - 인덱스: idx_investor_stock_date

3. ✅ **투자자 매매 수집기 구현**
   - 매일 장 마감 후(16:00) 자동 수집
   - 수집 성공률 ≥98%
   - DB 저장 및 중복 방지

4. ✅ **과거 데이터 백필**
   - 과거 90일 데이터 일괄 수집
   - 최소 4,500건 저장 (50종목 × 90일)

5. ✅ **APScheduler 작업 등록**
   - Cron: 매일 16:00
   - 에러 핸들링 및 알림

### 선택 기준 (Nice to Have)

- 🔹 투자자별 누적 매매 추이 분석
- 🔹 이상 매매 감지 (급격한 순매수 변화)
- 🔹 Grafana 대시보드

---

## 📐 Technical Design

### 1. 데이터 모델

#### 1.1 InvestorTrading Model

```python
# backend/db/models/investor_trading.py

from sqlalchemy import Column, Integer, String, Date, BigInteger, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func

from backend.db.base import Base


class InvestorTrading(Base):
    """투자자 매매 데이터 모델"""

    __tablename__ = "investor_trading"

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)

    # 외국인 매매
    foreign_buy = Column(BigInteger, comment="외국인 매수량")
    foreign_sell = Column(BigInteger, comment="외국인 매도량")
    foreign_net = Column(BigInteger, comment="외국인 순매수 (매수-매도)")

    # 기관 매매
    institution_buy = Column(BigInteger, comment="기관 매수량")
    institution_sell = Column(BigInteger, comment="기관 매도량")
    institution_net = Column(BigInteger, comment="기관 순매수")

    # 개인 매매
    individual_buy = Column(BigInteger, comment="개인 매수량")
    individual_sell = Column(BigInteger, comment="개인 매도량")
    individual_net = Column(BigInteger, comment="개인 순매수")

    # 메타데이터
    created_at = Column(DateTime, default=func.now())

    # 제약 조건
    __table_args__ = (
        UniqueConstraint('stock_code', 'date', name='uk_investor_stock_date'),
        Index('idx_investor_stock_date', 'stock_code', 'date'),
    )
```

### 2. KIS API 스펙

#### 2.1 투자자별 매매 동향 조회

```http
GET /uapi/domestic-stock/v1/quotations/inquire-investor
Host: openapi.koreainvestment.com:9443

Headers:
  authorization: Bearer {access_token}
  appkey: {app_key}
  appsecret: {app_secret}
  tr_id: FHKST01010900        # 모의투자

Query Parameters:
  FID_COND_MRKT_DIV_CODE: J   # J: 주식
  FID_INPUT_ISCD: 005930      # 종목코드
  FID_INPUT_DATE_1: 20241108  # 조회 날짜 (YYYYMMDD)

Response:
{
  "rt_cd": "0",
  "msg1": "정상처리 되었습니다.",
  "output": {
    "stck_bsop_date": "20241108",
    "frgn_ntby_qty": "123456",       // 외국인 순매수량
    "frgn_buy_qty": "500000",        // 외국인 매수량
    "frgn_sell_qty": "376544",       // 외국인 매도량
    "orgn_ntby_qty": "-50000",       // 기관 순매수량
    "orgn_buy_qty": "200000",        // 기관 매수량
    "orgn_sell_qty": "250000",       // 기관 매도량
    "indv_ntby_qty": "-73456",       // 개인 순매수량
    "indv_buy_qty": "300000",        // 개인 매수량
    "indv_sell_qty": "373456"        // 개인 매도량
  }
}
```

---

## 🔧 Implementation Tasks

### Task 1: PostgreSQL 테이블 생성 (0.5일)

**Migration SQL**: `backend/db/migrations/create_investor_trading_table.sql`

```sql
-- 투자자 매매 테이블 생성
CREATE TABLE IF NOT EXISTS investor_trading (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    date DATE NOT NULL,

    -- 외국인 매매
    foreign_buy BIGINT,
    foreign_sell BIGINT,
    foreign_net BIGINT,

    -- 기관 매매
    institution_buy BIGINT,
    institution_sell BIGINT,
    institution_net BIGINT,

    -- 개인 매매
    individual_buy BIGINT,
    individual_sell BIGINT,
    individual_net BIGINT,

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),

    -- 제약 조건
    CONSTRAINT uk_investor_stock_date UNIQUE (stock_code, date)
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_investor_stock_date
ON investor_trading (stock_code, date DESC);

-- 코멘트
COMMENT ON TABLE investor_trading IS '투자자별 매매 데이터';
COMMENT ON COLUMN investor_trading.foreign_net IS '외국인 순매수량 (매수-매도)';
COMMENT ON COLUMN investor_trading.institution_net IS '기관 순매수량';
COMMENT ON COLUMN investor_trading.individual_net IS '개인 순매수량';

-- 통계 업데이트
ANALYZE investor_trading;
```

**실행**:
```bash
psql -U postgres -d craveny -f backend/db/migrations/create_investor_trading_table.sql
```

---

### Task 2: KIS API 투자자 매매 조회 구현 (1일)

**Code**: `backend/kis/client.py` (확장)

```python
# ... 기존 KISClient 클래스에 추가

async def get_investor_trading(
    self,
    stock_code: str,
    trade_date: datetime = None
) -> dict:
    """
    투자자별 매매 동향 조회

    Args:
        stock_code: 종목 코드
        trade_date: 조회 날짜 (기본: 오늘)

    Returns:
        {
            "date": "2024-11-08",
            "foreign_buy": 500000,
            "foreign_sell": 376544,
            "foreign_net": 123456,
            "institution_buy": 200000,
            "institution_sell": 250000,
            "institution_net": -50000,
            "individual_buy": 300000,
            "individual_sell": 373456,
            "individual_net": -73456
        }
    """
    if trade_date is None:
        trade_date = datetime.now()

    # tr_id
    tr_id = "VHKST01010900" if self.config.is_mock else "FHKST01010900"

    # 요청 파라미터
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_INPUT_DATE_1": trade_date.strftime("%Y%m%d")
    }

    headers = {
        "tr_id": tr_id
    }

    # API 호출
    response = await self.get(
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-investor",
        headers=headers,
        params=params
    )

    # 응답 파싱
    output = response.get("output", {})

    if not output:
        logger.warning(f"No investor data for {stock_code} on {trade_date.date()}")
        return None

    # 데이터 변환
    result = {
        "date": output.get("stck_bsop_date"),
        "foreign_buy": int(output.get("frgn_buy_qty", 0)),
        "foreign_sell": int(output.get("frgn_sell_qty", 0)),
        "foreign_net": int(output.get("frgn_ntby_qty", 0)),
        "institution_buy": int(output.get("orgn_buy_qty", 0)),
        "institution_sell": int(output.get("orgn_sell_qty", 0)),
        "institution_net": int(output.get("orgn_ntby_qty", 0)),
        "individual_buy": int(output.get("indv_buy_qty", 0)),
        "individual_sell": int(output.get("indv_sell_qty", 0)),
        "individual_net": int(output.get("indv_ntby_qty", 0))
    }

    logger.debug(f"Investor data for {stock_code}: foreign_net={result['foreign_net']}")

    return result
```

---

### Task 3: 투자자 매매 수집기 구현 (2일)

**Code**: `backend/crawlers/investor_trading_crawler.py`

```python
"""
투자자 매매 데이터 수집기
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict

from sqlalchemy.orm import Session

from backend.kis.client import get_kis_client
from backend.db.models.investor_trading import InvestorTrading
from backend.db.session import SessionLocal
from backend.utils.stock_loader import load_target_stocks


logger = logging.getLogger(__name__)


class InvestorTradingCrawler:
    """투자자 매매 수집기"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self.should_close_db = db is None

    async def collect_investor_trading(
        self,
        stock_codes: List[str] = None,
        trade_date: datetime = None
    ) -> Dict[str, bool]:
        """
        투자자 매매 데이터 수집

        Args:
            stock_codes: 종목 코드 리스트 (None이면 전체 50개)
            trade_date: 조회 날짜 (기본: 어제)

        Returns:
            {stock_code: 성공 여부} 딕셔너리
        """
        if stock_codes is None:
            target_stocks = load_target_stocks()
            stock_codes = [stock["code"] for stock in target_stocks]

        if trade_date is None:
            # 어제 날짜 (당일은 데이터 미확정)
            trade_date = datetime.now() - timedelta(days=1)

        results = {}

        async with get_kis_client() as kis_client:
            for stock_code in stock_codes:
                try:
                    logger.debug(f"Collecting investor data for {stock_code}")

                    # KIS API 호출
                    data = await kis_client.get_investor_trading(
                        stock_code=stock_code,
                        trade_date=trade_date
                    )

                    if data is None:
                        logger.warning(f"No investor data for {stock_code}")
                        results[stock_code] = False
                        continue

                    # DB 저장
                    self._save_to_db(stock_code, trade_date.date(), data)
                    results[stock_code] = True

                    logger.debug(f"✅ {stock_code}: 투자자 매매 저장")

                except Exception as e:
                    logger.error(f"❌ {stock_code} 수집 실패: {e}")
                    results[stock_code] = False

        # 결과 요약
        success_count = sum(1 for success in results.values() if success)

        logger.info(
            f"투자자 매매 수집 완료: {success_count}/{len(stock_codes)}개 종목"
        )

        return results

    def _save_to_db(self, stock_code: str, trade_date, data: dict):
        """
        투자자 매매 데이터 DB 저장

        Args:
            stock_code: 종목 코드
            trade_date: 거래 날짜
            data: 투자자 매매 데이터
        """
        try:
            # 중복 체크
            existing = (
                self.db.query(InvestorTrading)
                .filter(
                    InvestorTrading.stock_code == stock_code,
                    InvestorTrading.date == trade_date
                )
                .first()
            )

            if existing:
                # 업데이트
                existing.foreign_buy = data["foreign_buy"]
                existing.foreign_sell = data["foreign_sell"]
                existing.foreign_net = data["foreign_net"]
                existing.institution_buy = data["institution_buy"]
                existing.institution_sell = data["institution_sell"]
                existing.institution_net = data["institution_net"]
                existing.individual_buy = data["individual_buy"]
                existing.individual_sell = data["individual_sell"]
                existing.individual_net = data["individual_net"]
                logger.debug(f"Updated investor data: {stock_code} {trade_date}")
            else:
                # 삽입
                investor_trading = InvestorTrading(
                    stock_code=stock_code,
                    date=trade_date,
                    foreign_buy=data["foreign_buy"],
                    foreign_sell=data["foreign_sell"],
                    foreign_net=data["foreign_net"],
                    institution_buy=data["institution_buy"],
                    institution_sell=data["institution_sell"],
                    institution_net=data["institution_net"],
                    individual_buy=data["individual_buy"],
                    individual_sell=data["individual_sell"],
                    individual_net=data["individual_net"]
                )
                self.db.add(investor_trading)
                logger.debug(f"Inserted investor data: {stock_code} {trade_date}")

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.error(f"DB 저장 실패: {stock_code}, {e}")
            raise

    def __del__(self):
        if self.should_close_db and self.db:
            self.db.close()


# 싱글톤 팩토리
def get_investor_trading_crawler(db: Session = None) -> InvestorTradingCrawler:
    return InvestorTradingCrawler(db)
```

---

### Task 4: APScheduler 작업 등록 (0.5일)

**Code**: `backend/schedulers/stock_scheduler.py` (확장)

```python
# ... 기존 imports에 추가
from backend.crawlers.investor_trading_crawler import get_investor_trading_crawler


async def collect_investor_trading_job():
    """
    투자자 매매 수집 작업 (매일 16:00)
    """
    logger.info("투자자 매매 수집 시작")

    # 장 운영일 체크
    if not is_market_day():
        return

    try:
        crawler = get_investor_trading_crawler()
        results = await crawler.collect_investor_trading()

        total = len(results)
        success = sum(1 for s in results.values() if s)
        failed = total - success

        summary = (
            f"투자자 매매 수집 완료\n"
            f"성공: {success}/{total}개 종목\n"
            f"실패: {failed}개 종목"
        )

        logger.info(summary)

        # 알림
        await send_notification(
            title="📊 투자자 매매 수집 완료",
            message=summary,
            level="info" if failed == 0 else "warning"
        )

    except Exception as e:
        logger.error(f"투자자 매매 수집 실패: {e}", exc_info=True)
        await send_notification(
            title="❌ 투자자 매매 수집 실패",
            message=f"에러: {str(e)}",
            level="error"
        )


def start_scheduler():
    """스케줄러 시작"""
    # ... 기존 작업들 ...

    # 투자자 매매 수집: 매일 16:00
    scheduler.add_job(
        collect_investor_trading_job,
        trigger=CronTrigger(hour=16, minute=0),
        id="investor_trading_collector",
        replace_existing=True
    )

    scheduler.start()
    logger.info("✅ Investor Trading Scheduler started")
```

---

### Task 5: 과거 데이터 백필 스크립트 (1.5일)

**Code**: `scripts/backfill_investor_trading.py`

```python
"""
투자자 매매 과거 데이터 백필
"""
import asyncio
import logging
from datetime import datetime, timedelta
from tqdm import tqdm

from backend.crawlers.investor_trading_crawler import get_investor_trading_crawler
from backend.utils.stock_loader import load_target_stocks


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_investor_trading(days: int = 90):
    """
    과거 투자자 매매 데이터 백필

    Args:
        days: 과거 일수 (기본: 90일)
    """
    logger.info(f"과거 {days}일 투자자 매매 백필 시작")

    # 종목 리스트
    target_stocks = load_target_stocks()
    stock_codes = [stock["code"] for stock in target_stocks]

    logger.info(f"대상 종목: {len(stock_codes)}개")

    crawler = get_investor_trading_crawler()

    # 날짜 범위 (과거 → 현재)
    end_date = datetime.now() - timedelta(days=1)  # 어제
    start_date = end_date - timedelta(days=days)

    total_days = (end_date - start_date).days + 1

    logger.info(f"기간: {start_date.date()} ~ {end_date.date()} ({total_days}일)")

    # 날짜별 수집
    success_count = 0
    total_count = 0

    with tqdm(total=total_days, desc="백필 진행") as pbar:
        current_date = start_date

        while current_date <= end_date:
            # 주말 skip
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                pbar.update(1)
                continue

            logger.info(f"수집 날짜: {current_date.date()}")

            results = await crawler.collect_investor_trading(
                stock_codes=stock_codes,
                trade_date=current_date
            )

            success = sum(1 for s in results.values() if s)
            success_count += success
            total_count += len(results)

            current_date += timedelta(days=1)
            pbar.update(1)

            # Rate limit 준수
            await asyncio.sleep(1)

    # 결과 요약
    logger.info("=" * 50)
    logger.info("백필 완료")
    logger.info(f"총 성공: {success_count}/{total_count}건")
    logger.info(f"성공률: {success_count / total_count * 100:.2f}%")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(backfill_investor_trading(days=90))
```

**실행**:
```bash
uv run python scripts/backfill_investor_trading.py
```

---

### Task 6: 헬스체크 및 테스트 (1.5일)

**헬스체크 API**: `backend/api/endpoints/kis_health.py` (확장)

```python
from pydantic import BaseModel


class InvestorTradingStatus(BaseModel):
    """투자자 매매 수집 현황"""
    total_records: int
    latest_date: str | None
    stock_count: int
    avg_foreign_net: float
    avg_institution_net: float


@router.get("/investor-status", response_model=InvestorTradingStatus)
async def get_investor_trading_status():
    """투자자 매매 수집 현황"""
    from backend.db.session import SessionLocal
    from backend.db.models.investor_trading import InvestorTrading
    from sqlalchemy import func

    db = SessionLocal()

    try:
        # 총 레코드 수
        total_records = db.query(func.count(InvestorTrading.id)).scalar()

        # 최근 날짜
        latest_date = db.query(func.max(InvestorTrading.date)).scalar()

        # 종목 수
        stock_count = db.query(
            func.count(func.distinct(InvestorTrading.stock_code))
        ).scalar()

        # 평균 순매수 (최근 7일)
        if latest_date:
            recent_data = (
                db.query(
                    func.avg(InvestorTrading.foreign_net),
                    func.avg(InvestorTrading.institution_net)
                )
                .filter(InvestorTrading.date >= latest_date - timedelta(days=7))
                .first()
            )

            avg_foreign_net = recent_data[0] or 0
            avg_institution_net = recent_data[1] or 0
        else:
            avg_foreign_net = 0
            avg_institution_net = 0

        return InvestorTradingStatus(
            total_records=total_records,
            latest_date=latest_date.isoformat() if latest_date else None,
            stock_count=stock_count,
            avg_foreign_net=round(avg_foreign_net, 2),
            avg_institution_net=round(avg_institution_net, 2)
        )

    finally:
        db.close()
```

**Unit Test**: `tests/crawlers/test_investor_trading_crawler.py`

```python
import pytest
from datetime import datetime, timedelta

from backend.crawlers.investor_trading_crawler import InvestorTradingCrawler


@pytest.mark.asyncio
async def test_collect_single_stock():
    """단일 종목 투자자 매매 수집"""
    crawler = InvestorTradingCrawler()

    yesterday = datetime.now() - timedelta(days=1)

    results = await crawler.collect_investor_trading(
        stock_codes=["005930"],
        trade_date=yesterday
    )

    assert "005930" in results
    assert results["005930"] is True
```

---

## ✅ Definition of Done

- [ ] `investor_trading` 테이블 생성
- [ ] `backend/kis/client.py`에 `get_investor_trading()` 구현
- [ ] `backend/crawlers/investor_trading_crawler.py` 구현
- [ ] `backend/schedulers/stock_scheduler.py`에 16:00 작업 등록
- [ ] `scripts/backfill_investor_trading.py` 구현
- [ ] 과거 90일 데이터 백필 완료 (최소 4,500건)
- [ ] 수집 성공률 ≥98% 검증
- [ ] `/api/kis/investor-status` 엔드포인트 구현
- [ ] 모든 테스트 통과
- [ ] 코드 리뷰 완료
- [ ] main 브랜치 머지

---

**작성자**: PM Agent (John)
**최종 수정**: 2024-11-08
