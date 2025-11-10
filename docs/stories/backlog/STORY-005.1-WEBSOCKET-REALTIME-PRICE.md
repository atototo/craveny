# Story 005.1: WebSocket 실시간 체결가 수집

**Epic**: Epic 005 - Phase 3 실시간 데이터
**Priority**: ⭐⭐⭐⭐⭐ | **Effort**: 5-7일 | **Dependencies**: Epic 003, 004

---

## 📋 Overview

KIS API WebSocket을 통해 실시간 체결가를 수집하고 급변 감지의 기반을 마련합니다.

**핵심**: 장중 급변 즉시 감지 → 3초 이내 알림

---

## 🎯 Acceptance Criteria

1. ✅ `stock_prices_realtime` 테이블 생성
2. ✅ WebSocket 연결 구현 (KIS API)
3. ✅ 50개 종목 동시 구독
4. ✅ 데이터 저장 성공률 ≥99%
5. ✅ 지연 시간 <1초 (체결 → DB 저장)
6. ✅ 자동 재연결 (30초 이내)

---

## 🔧 Implementation

### WebSocket Realtime Crawler

```python
# backend/crawlers/realtime_price_crawler.py

import websockets
import json
import asyncio


class RealtimePriceCrawler:
    """WebSocket 실시간 체결가 수집기"""

    def __init__(self):
        self.ws_uri = "wss://openapi.koreainvestment.com:9443/ws"
        self.connections = {}
        self.is_running = False

    async def connect(self):
        """WebSocket 연결"""
        try:
            ws = await websockets.connect(self.ws_uri)

            # 인증
            auth_message = {
                "header": {
                    "approval_key": await self._get_approval_key()
                },
                "body": {
                    "input": {
                        "tr_type": "1",  # 등록
                        "tr_id": "H0STCNT0"
                    }
                }
            }

            await ws.send(json.dumps(auth_message))
            response = await ws.recv()
            logger.info(f"WebSocket 연결 성공: {response}")

            return ws

        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            raise

    async def subscribe_stocks(self, ws, stock_codes: List[str]):
        """종목 구독"""
        for stock_code in stock_codes:
            subscribe_msg = {
                "header": {"tr_type": "1"},
                "body": {
                    "input": {
                        "tr_id": "H0STCNT0",
                        "tr_key": stock_code
                    }
                }
            }

            await ws.send(json.dumps(subscribe_msg))
            logger.debug(f"구독: {stock_code}")

    async def start_collection(self, stock_codes: List[str]):
        """실시간 수집 시작 (장중 9:00~15:30)"""
        self.is_running = True

        while self.is_running:
            try:
                ws = await self.connect()
                await self.subscribe_stocks(ws, stock_codes)

                # 메시지 수신 루프
                async for message in ws:
                    await self._handle_message(message)

            except websockets.ConnectionClosed:
                logger.warning("WebSocket 연결 끊김. 재연결 중...")
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"WebSocket 에러: {e}")
                await asyncio.sleep(30)

    async def _handle_message(self, message: str):
        """메시지 처리 및 DB 저장"""
        try:
            data = json.loads(message)

            # 파싱
            stock_code = data["output"]["stock_code"]
            price = float(data["output"]["current_price"])
            volume = int(data["output"]["volume"])
            timestamp = datetime.fromisoformat(data["output"]["timestamp"])

            # DB 저장
            db = SessionLocal()
            try:
                realtime_price = StockPriceRealtime(
                    stock_code=stock_code,
                    timestamp=timestamp,
                    price=price,
                    volume=volume
                )
                db.add(realtime_price)
                db.commit()

                # 급변 감지
                await self._check_sudden_change(stock_code, price)

            finally:
                db.close()

        except Exception as e:
            logger.error(f"메시지 처리 실패: {e}")

    async def _check_sudden_change(self, stock_code: str, current_price: float):
        """급변 감지 (1분 내 5% 이상)"""
        # 1분 전 가격 조회
        one_min_ago = datetime.now() - timedelta(minutes=1)

        db = SessionLocal()
        try:
            prev_price = db.query(StockPriceRealtime.price).filter(
                StockPriceRealtime.stock_code == stock_code,
                StockPriceRealtime.timestamp >= one_min_ago
            ).order_by(StockPriceRealtime.timestamp).first()

            if prev_price:
                change_rate = (current_price - prev_price[0]) / prev_price[0] * 100

                if abs(change_rate) >= 5:
                    # Redis Pub/Sub 이벤트 발행
                    await self._publish_sudden_change(stock_code, change_rate)

        finally:
            db.close()
```

---

## ✅ Definition of Done

- [ ] WebSocket 연결 구현
- [ ] 50개 종목 동시 구독
- [ ] `stock_prices_realtime` 테이블 저장
- [ ] 데이터 저장 성공률 ≥99%
- [ ] 지연 시간 <1초
- [ ] 자동 재연결 테스트
- [ ] 급변 감지 이벤트 발행
- [ ] 코드 리뷰 및 머지
