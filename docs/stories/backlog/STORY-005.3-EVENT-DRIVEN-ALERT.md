# Story 005.3: 장중 급변 감지 및 이벤트 기반 알림

**Epic**: Epic 005 | **Priority**: ⭐⭐⭐⭐⭐ | **Effort**: 4-6일 | **Dependencies**: Story 005.1, 005.2

---

## Overview

급변 감지 → Redis Pub/Sub → LLM 긴급 분석 → 텔레그램 알림 (3초 이내)

---

## Acceptance Criteria

1. ✅ Redis Pub/Sub 이벤트 시스템
2. ✅ 급변 감지 (1분 내 5% 이상, 매수 압력 0.8 이상)
3. ✅ LLM 긴급 분석 (최대 300 tokens)
4. ✅ 텔레그램 알림 (평균 3초 이내)
5. ✅ 중복 알림 방지 (5분 내 동일 종목 1회)

---

## Key Implementation

```python
# backend/events/market_events.py

async def publish_sudden_change(stock_code: str, change_rate: float):
    """급변 이벤트 발행"""
    event = {
        "type": "sudden_change",
        "stock_code": stock_code,
        "change_rate": change_rate,
        "timestamp": datetime.now().isoformat()
    }
    await redis_client.publish("market_events", json.dumps(event))


async def handle_market_event(event: dict):
    """이벤트 처리"""
    if event["type"] == "sudden_change":
        # LLM 긴급 분석
        analysis = await analyze_sudden_change(
            event["stock_code"],
            event["change_rate"]
        )

        # 텔레그램 알림
        await send_telegram_alert(
            title=f"🚨 급변 감지: {event['stock_code']}",
            message=f"{event['change_rate']:+.1f}%\n\n{analysis}"
        )
```

---

## Definition of Done

- [ ] Redis Pub/Sub 구현
- [ ] 급변 감지 로직
- [ ] LLM 긴급 분석
- [ ] 텔레그램 알림 통합
- [ ] 평균 지연 <3초
- [ ] 중복 방지 테스트
- [ ] 코드 리뷰 및 머지
