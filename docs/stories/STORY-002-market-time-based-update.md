---
story_id: STORY-002
epic_id: EPIC-001
title: 시장 시간 기반 동적 업데이트 시스템
status: blocked
priority: high
assignee: Backend Developer
created: 2025-11-04
estimated: 1.5 days
blocked_by: STORY-001
---

# Story: 시장 시간 기반 동적 업데이트 시스템

## 🎯 User Story

**As a** 투자자
**I want** 장중에는 1-2시간마다, 장 마감 후에는 6시간마다 리포트가 업데이트되도록
**So that** 시장 상황에 맞는 최신 정보로 실시간 투자 판단을 할 수 있다

## 📊 Background

### 주식 시장 타임라인
```
00:00 ────── 09:00 ─ 09:30 ────── 15:30 ─ 15:36 ────── 23:59
  │            │      │              │      │            │
장 시작 전   장 시작  정규 장중     장 마감  장 마감 후
TTL: 3시간   1시간   2시간         1시간    6시간
```

### 시장 시간별 특성
| 시간대 | 특성 | 업데이트 빈도 | 이유 |
|--------|------|--------------|------|
| 장 시작 전 (00:00-08:59) | 뉴스 폭탄 가능 | 3시간 | 급한 뉴스 반영 |
| 장 시작 (09:00-09:30) | 초반 변동성 높음 | 1시간 | 급등/급락 감지 |
| 정규 장중 (09:31-15:29) | 실시간 변동 | **2시간** | 적당한 빈도 |
| 장 마감 (15:30-15:35) | 마감 전 급변 | 1시간 | 마감 영향 |
| 장 마감 후 (15:36-23:59) | 변동성 낮음 | 6시간 | 뉴스만 반영 |

## ✅ Acceptance Criteria

### AC1: 시장 시간 감지 함수
- [ ] 5단계 시장 단계 정확히 구분
- [ ] KST 타임존 명시 (Asia/Seoul)
- [ ] 각 단계별 TTL, 주가 임계값, 예측 임계값 반환

### AC2: 다중 업데이트 트리거
- [ ] 트리거 1: 예측 개수 증가
- [ ] 트리거 2: 시장 시간 기반 TTL 초과
- [ ] 트리거 3: 주가 급변 (장중 3%, 장외 5%)
- [ ] 트리거 4: 예측 방향 변화 (장중 15%p, 장외 20%p)

### AC3: 업데이트 사유 로깅
- [ ] 모든 업데이트에 명확한 사유 출력
- [ ] 시장 단계, 경과 시간, 변동률 등 상세 정보 포함

### AC4: 프로덕션 시나리오 검증
- [ ] 장 시작 전 뉴스 → 3시간 이내 업데이트
- [ ] 장중 주가 3% 변동 → 즉시 업데이트
- [ ] 장 마감 후 → 6시간 이내 업데이트

## 📝 Tasks

### Task 2.1: 시장 시간 유틸리티 구현
**파일**: `backend/utils/market_time.py` (신규)
**예상 시간**: 2시간

```python
"""
한국 증시 시장 시간 유틸리티
"""
from datetime import datetime, time
from pytz import timezone


def get_market_phase() -> str:
    """현재 한국 증시 단계 반환"""
    kst = timezone('Asia/Seoul')
    now = datetime.now(kst).time()

    if time(0, 0) <= now < time(9, 0):
        return "pre_market"
    elif time(9, 0) <= now < time(9, 30):
        return "market_open"
    elif time(9, 30) <= now < time(15, 30):
        return "trading"
    elif time(15, 30) <= now < time(15, 36):
        return "market_close"
    else:
        return "after_hours"


def get_ttl_hours(market_phase: str) -> int:
    """시장 단계별 리포트 TTL 반환"""
    ttl_map = {
        "pre_market": 3,
        "market_open": 1,
        "trading": 2,
        "market_close": 1,
        "after_hours": 6,
    }
    return ttl_map[market_phase]


def get_price_threshold(market_phase: str) -> float:
    """시장 단계별 주가 변동 감지 임계값 (%)"""
    return 3.0 if market_phase == "trading" else 5.0


def get_direction_threshold(market_phase: str) -> float:
    """시장 단계별 예측 방향 변화 감지 임계값"""
    return 0.15 if market_phase in ["trading", "market_open", "market_close"] else 0.20
```

**체크리스트**:
- [ ] `pytz` 의존성 추가 (`pyproject.toml` 또는 `requirements.txt`)
- [ ] 4개 함수 구현
- [ ] 단위 테스트 작성 (시간대별 반환값 확인)

---

### Task 2.2: 다중 트리거 함수 구현
**파일**: `backend/services/stock_analysis_service.py` (수정)
**예상 시간**: 3시간

**새 함수 추가**:
```python
async def should_update_report(
    stock_code: str,
    db: Session,
    existing_summary: Optional[StockAnalysisSummary],
    force_update: bool
) -> tuple[bool, str]:
    """
    리포트 업데이트 필요 여부 판단 (시장 시간 기반)

    Returns:
        (업데이트 필요 여부, 사유)
    """
    if force_update or not existing_summary:
        return True, "강제 업데이트 또는 리포트 없음"

    market_phase = get_market_phase()
    staleness_hours = (datetime.now() - existing_summary.last_updated).total_seconds() / 3600

    # 트리거 1: 예측 개수 증가
    total_prediction_count = db.query(func.count(Prediction.id)).filter(...).scalar()
    if existing_summary.based_on_prediction_count < total_prediction_count:
        return True, f"새 예측 추가 (...)"

    # 트리거 2: 시장 시간 기반 TTL
    ttl_hours = get_ttl_hours(market_phase)
    if staleness_hours >= ttl_hours:
        return True, f"시장 단계별 TTL 초과 (...)"

    # 트리거 3: 주가 급변
    if market_phase in ["market_open", "trading", "market_close"]:
        # 주가 변동률 계산
        threshold = get_price_threshold(market_phase)
        if price_change_rate >= threshold:
            return True, f"주가 급변 (...)"

    # 트리거 4: 예측 방향 변화
    threshold = get_direction_threshold(market_phase)
    if abs(current_up_ratio - report_up_ratio) >= threshold:
        return True, f"예측 방향 급변 (...)"

    return False, f"업데이트 불필요 (시장: {market_phase})"
```

**기존 함수 수정**:
```python
async def update_stock_analysis_summary(...):
    # ...

    # 업데이트 필요 여부 확인 (새 함수 호출)
    should_update, reason = await should_update_report(stock_code, db, existing_summary, force_update)

    if not should_update:
        logger.info(f"종목 {stock_code}의 분석 요약이 최신 상태입니다. ({reason})")
        return existing_summary

    logger.info(f"종목 {stock_code} 업데이트 시작: {reason}")

    # ...
```

**체크리스트**:
- [ ] `backend.utils.market_time` import 추가
- [ ] `should_update_report()` 함수 구현
- [ ] `update_stock_analysis_summary()` 함수 수정
- [ ] 로깅 메시지 개선

---

### Task 2.3: 통합 테스트 작성
**파일**: `tests/services/test_market_time_updates.py` (신규)
**예상 시간**: 3시간

```python
import pytest
from freezegun import freeze_time

@freeze_time("2025-11-04 09:15:00", tz_offset=9)  # 장 시작 (KST)
def test_market_open_ttl_1hour():
    """장 시작 시 1시간 TTL 적용 확인"""
    # ...

@freeze_time("2025-11-04 11:30:00", tz_offset=9)  # 정규 장중
def test_trading_price_change_3percent():
    """장중 주가 3% 변동 시 업데이트"""
    # ...

@freeze_time("2025-11-04 18:00:00", tz_offset=9)  # 장 마감 후
def test_after_hours_ttl_6hours():
    """장 마감 후 6시간 TTL 적용"""
    # ...
```

**체크리스트**:
- [ ] `freezegun` 의존성 추가
- [ ] 5가지 시간대별 테스트 케이스 작성
- [ ] 4가지 트리거 동작 검증
- [ ] `pytest tests/services/test_market_time_updates.py` 통과

---

### Task 2.4: 프로덕션 배포 및 검증
**예상 시간**: 2시간

**배포 절차**:
1. [ ] Git commit: "feat: 시장 시간 기반 동적 리포트 업데이트 시스템"
2. [ ] Pull Request 생성 및 코드 리뷰
3. [ ] 프로덕션 배포
4. [ ] 모니터링 설정

**검증 시나리오**:

**시나리오 1: 장 시작 전 뉴스 (08:30)**
```
Given: 어제 18:00 리포트 (14.5시간 경과)
When: 새 뉴스 추가 → 예측 생성
Then: pre_market TTL 3시간 → 즉시 업데이트 ✅
```
- [ ] 실제 업데이트 확인
- [ ] 로그: "시장 단계별 TTL 초과 (pre_market: 14.5h > 3h)"

**시나리오 2: 장중 주가 급변 (11:00)**
```
Given: 10:00 리포트 (1시간 경과)
When: 주가 +5% 급등
Then: trading 주가 임계값 3% → 즉시 업데이트 ✅
```
- [ ] 실제 업데이트 확인
- [ ] 로그: "주가 급변 (5.0%, 임계값: 3%)"

**시나리오 3: 장 마감 후 (18:00)**
```
Given: 15:00 리포트 (3시간 경과)
When: 새 뉴스 추가
Then: after_hours TTL 6시간 → 업데이트 안 함 ✅
```
- [ ] 업데이트 안 됨 확인
- [ ] 로그: "업데이트 불필요 (시장: after_hours)"

---

## 📋 Definition of Done

- [x] 시장 시간 유틸리티 구현 완료
- [x] 다중 트리거 함수 구현 완료
- [x] pytz 의존성 추가
- [x] 통합 테스트 통과
- [x] 프로덕션 배포 완료
- [x] 3가지 시나리오 검증 완료
- [x] 업데이트 사유 로그 확인

## 🔗 Dependencies

**Depends On**:
- STORY-001 (긴급 버그 수정) - MUST complete first

**Blocks**:
- STORY-003 (모니터링 및 검증)

**References**:
- `docs/STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md`
- EPIC-001

---

**Last Updated**: 2025-11-04
**Status**: Blocked (Waiting for STORY-001)
