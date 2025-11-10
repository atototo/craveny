# Story 005.2: 실시간 호가 데이터 수집

**Epic**: Epic 005 | **Priority**: ⭐⭐⭐ | **Effort**: 3-5일 | **Dependencies**: Story 005.1

---

## Overview

실시간 호가창 (매수/매도 1~10호가) 수집으로 매수/매도 압력을 분석합니다.

---

## Acceptance Criteria

1. ✅ `stock_orderbook` 테이블 생성 (매수/매도 1~10호가, 잔량)
2. ✅ WebSocket 호가 구독 구현
3. ✅ 매수 압력 비율 계산
4. ✅ 저장 성공률 ≥98%

---

## Key Implementation

```python
# backend/models/orderbook.py

class StockOrderbook(Base):
    __tablename__ = "stock_orderbook"

    # 매수 호가 1~10
    bid_price_1 = Column(Float)
    bid_volume_1 = Column(BigInteger)
    # ... bid_price_10, bid_volume_10

    # 매도 호가 1~10
    ask_price_1 = Column(Float)
    ask_volume_1 = Column(BigInteger)
    # ... ask_price_10, ask_volume_10

    # 파생 지표
    total_bid_volume = Column(BigInteger)
    total_ask_volume = Column(BigInteger)
    buy_pressure_ratio = Column(Float)  # 매수압력 비율
```

---

## Definition of Done

- [ ] `stock_orderbook` 테이블 생성
- [ ] WebSocket 호가 구독
- [ ] 매수 압력 비율 계산
- [ ] 저장 성공률 ≥98%
- [ ] 코드 리뷰 및 머지
