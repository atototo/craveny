# Story 004.2: 재무제표 데이터 수집기 구현

**Epic**: Epic 004 - Phase 2 보조 지표
**Priority**: ⭐⭐⭐⭐ | **Effort**: 5-7일 | **Dependencies**: Epic 003, Story 004.1

---

## 📋 Overview

분기별 재무제표 (손익계산서, 재무상태표, 주요 지표)를 수집하여 LLM 펀더멘털 분석에 활용합니다.

**핵심 가치**: 뉴스의 실체 검증 + 기업 건전성 분석 → 예측 정확도 향상

---

## 🎯 Acceptance Criteria

1. ✅ `financial_statements` 테이블 생성 (매출, 영업이익, 당기순이익, EPS, PER, PBR, ROE, 부채비율)
2. ✅ KIS API 재무제표 조회 구현 (최근 8분기)
3. ✅ 분기별 자동 수집 (1월/4월/7월/10월 15일)
4. ✅ 과거 8분기 백필 (400건: 50종목 × 8분기)
5. ✅ 수집 성공률 ≥95%

---

## 📐 Data Model

```python
# backend/db/models/financial_statements.py

class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(10), nullable=False)
    quarter = Column(String(10), nullable=False)  # '2024Q3'

    # 손익계산서
    revenue = Column(BigInteger, comment="매출액")
    operating_profit = Column(BigInteger, comment="영업이익")
    net_income = Column(BigInteger, comment="당기순이익")

    # 재무상태표
    total_assets = Column(BigInteger)
    total_liabilities = Column(BigInteger)
    total_equity = Column(BigInteger)

    # 주요 지표
    eps = Column(Float, comment="주당순이익")
    per = Column(Float, comment="주가수익비율")
    pbr = Column(Float, comment="주가순자산비율")
    roe = Column(Float, comment="자기자본이익률")
    debt_ratio = Column(Float, comment="부채비율")

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('stock_code', 'quarter', name='uk_stock_quarter'),
    )
```

---

## 🔧 Key Implementation

### KIS API 재무제표 조회

```python
# backend/kis/client.py

async def get_financial_statements(
    self,
    stock_code: str,
    quarters: int = 8
) -> List[dict]:
    """
    재무제표 조회 (최근 N분기)

    Returns:
        [
            {
                "quarter": "2024Q3",
                "revenue": 75000000000000,
                "operating_profit": 10000000000000,
                "net_income": 8000000000000,
                ...
            },
            ...
        ]
    """
    tr_id = "VHKST03020100" if self.config.is_mock else "FHKST03020100"

    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_code,
        "FID_DIV_CLS_CODE": "0"  # 0: 분기, 1: 연간
    }

    response = await self.get(
        endpoint="/uapi/domestic-stock/v1/quotations/inquire-financial-ratio",
        headers={"tr_id": tr_id},
        params=params
    )

    output = response.get("output", [])
    results = []

    for item in output[:quarters]:
        results.append({
            "quarter": item["stac_yymm"],  # YYYYQQ
            "revenue": int(item.get("sale_account", 0)),
            "operating_profit": int(item.get("bsop_prti", 0)),
            "net_income": int(item.get("thtr_ntin", 0)),
            "total_assets": int(item.get("total_aset", 0)),
            "total_liabilities": int(item.get("total_lblt", 0)),
            "total_equity": int(item.get("cpfn", 0)),
            "eps": float(item.get("eps", 0)),
            "per": float(item.get("per", 0)),
            "pbr": float(item.get("pbr", 0)),
            "roe": float(item.get("roe", 0)),
            "debt_ratio": float(item.get("lblt_rate", 0))
        })

    return results
```

### 재무제표 수집기

```python
# backend/crawlers/financial_statements_crawler.py

class FinancialStatementsCrawler:
    async def collect_financial_statements(
        self,
        stock_codes: List[str] = None,
        quarters: int = 8
    ) -> Dict[str, int]:
        """분기별 재무제표 수집"""

        async with get_kis_client() as kis_client:
            for stock_code in stock_codes:
                try:
                    # KIS API 호출
                    statements = await kis_client.get_financial_statements(
                        stock_code, quarters
                    )

                    # DB 저장
                    saved_count = self._save_to_db(stock_code, statements)
                    results[stock_code] = saved_count

                except Exception as e:
                    logger.error(f"❌ {stock_code}: {e}")
                    results[stock_code] = 0

        return results

    def _save_to_db(self, stock_code: str, statements: List[dict]) -> int:
        saved_count = 0

        for stmt in statements:
            # 중복 체크
            existing = self.db.query(FinancialStatement).filter(
                FinancialStatement.stock_code == stock_code,
                FinancialStatement.quarter == stmt["quarter"]
            ).first()

            if existing:
                # 업데이트
                for key, value in stmt.items():
                    if key != "quarter":
                        setattr(existing, key, value)
            else:
                # 삽입
                fs = FinancialStatement(
                    stock_code=stock_code,
                    **stmt
                )
                self.db.add(fs)

            saved_count += 1

        self.db.commit()
        return saved_count
```

### Scheduler 작업

```python
# backend/schedulers/stock_scheduler.py

async def collect_financial_statements_job():
    """
    재무제표 수집 (분기별: 1월/4월/7월/10월 15일)
    """
    crawler = get_financial_statements_crawler()
    results = await crawler.collect_financial_statements()

    summary = f"재무제표 수집: {sum(results.values())}건"
    await send_notification("📊 재무제표 수집", summary)


def start_scheduler():
    # ... 기존 작업들 ...

    # 분기별 재무제표 수집
    scheduler.add_job(
        collect_financial_statements_job,
        trigger=CronTrigger(month='1,4,7,10', day=15, hour=18),
        id="financial_statements_collector"
    )
```

### 백필 스크립트

```python
# scripts/backfill_financial_statements.py

async def backfill_financial_statements(quarters: int = 8):
    """과거 8분기 재무제표 백필"""

    target_stocks = load_target_stocks()
    stock_codes = [stock["code"] for stock in target_stocks]

    crawler = get_financial_statements_crawler()

    results = await crawler.collect_financial_statements(
        stock_codes=stock_codes,
        quarters=quarters
    )

    total_saved = sum(results.values())
    logger.info(f"백필 완료: {total_saved}건 (목표: 400건)")
```

---

## ✅ Definition of Done

- [ ] `financial_statements` 테이블 생성
- [ ] KIS API 재무제표 조회 구현
- [ ] 재무제표 수집기 구현
- [ ] 분기별 스케줄러 작업 등록
- [ ] 과거 8분기 백필 완료 (≥400건)
- [ ] 수집 성공률 ≥95%
- [ ] 테스트 통과
- [ ] 코드 리뷰 및 머지
