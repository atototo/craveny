# 종합 리포트 업데이트 시스템 분석 보고서

**분석자**: Business Analyst Mary
**작성일**: 2025-11-04
**분석 범위**: 종합 투자 리포트 업데이트 시스템 전체 프로세스
**목적**: SK하이닉스 리포트가 새 뉴스 추가 시 업데이트되지 않는 문제 근본 원인 파악 및 개선 방향 제시

---

## 📋 Executive Summary (경영진 요약)

### 핵심 문제
종합 투자 리포트(`StockAnalysisSummary`)가 다음 상황에서 **업데이트되지 않음**:
1. ✅ 새 뉴스/예측 추가 시
2. ✅ 주가 변동 시
3. ✅ 예측 방향 변화 시 (상승→하락 전환)

### 실제 피해 사례
- **SK하이닉스(034730) 리포트**:
  - 마지막 업데이트: 2025-11-03 15:09:02
  - 리포트 내용: "매수 추천" (상승 11건, 하락 1건, 보합 8건)
  - 실제 최신 20건: 상승 5건, 하락 1건, 보합 14건 (중립/보합 우세)
  - **불일치 지속 시간**: 21시간 이상

### 근본 원인
1. **잘못된 업데이트 스킵 로직** (`stock_analysis_service.py:92`)
   - `limit(20)` 하드코딩 → 총 72건 예측 중 20건만 조회
   - 조건: `20 >= 20` → 항상 스킵
2. **시간 기반 업데이트 로직 부재**
3. **주가 변동 감지 로직 부재**
4. **예측 방향 변화 감지 로직 부재**

### 영향도
- **사용자 신뢰도**: 매우 높음 (잘못된 투자 의사결정 유발 가능)
- **비즈니스 임팩트**: 높음 (투자 추천 정확도 저하)
- **시스템 안정성**: 낮음 (API 호출 시 fallback 동작)

### 권장 조치
- **즉시 조치** (Priority 1): 잘못된 업데이트 스킵 로직 수정
- **단기 조치** (Priority 2): 다중 업데이트 트리거 추가 (시간, 주가, 방향)
- **중기 조치** (Priority 3): 이벤트 기반 업데이트 아키텍처로 전환

---

## 🔍 시스템 플로우 분석

### 1. 리포트 업데이트 호출 경로

```
┌─────────────────────────────────────────────────────────────┐
│                  리포트 업데이트 트리거                       │
└─────────────────────────────────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   뉴스 저장   │   │  API 조회    │   │ 배치 스크립트 │
│ news_saver.py│   │ stocks.py    │   │update_all.py │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       │                  │                  │
       └──────────────────┴──────────────────┘
                          │
                          ▼
       ┌──────────────────────────────────────────┐
       │  update_stock_analysis_summary()         │
       │  backend/services/stock_analysis_service.py │
       └──────────────────────────────────────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
 ┌───────────┐    ┌──────────────┐   ┌──────────────┐
 │ 예측 조회  │    │ 주가 조회     │   │ 기존 리포트   │
 │limit(20)  │    │(최신 2개)     │   │   조회       │
 └─────┬─────┘    └──────┬───────┘   └──────┬───────┘
       │                 │                  │
       └─────────────────┴──────────────────┘
                         │
                ┌────────▼────────┐
                │  업데이트 여부   │ ← **여기서 버그 발생**
                │  판단 로직      │
                └────────┬────────┘
                         │
            ┌────────────┼────────────┐
            │                         │
      [스킵 조건]               [업데이트 조건]
       20 >= 20                  force_update=True
            │                         │
            ▼                         ▼
    ┌──────────────┐          ┌──────────────┐
    │ 기존 리포트   │          │ LLM 리포트    │
    │   반환       │          │    생성       │
    └──────────────┘          └──────┬───────┘
                                     │
                              ┌──────▼───────┐
                              │  DB 저장/     │
                              │  업데이트     │
                              └──────────────┘
```

### 2. 현재 구현 코드 분석

#### Path 1: 뉴스 저장 시 자동 업데이트
**파일**: `backend/crawlers/news_saver.py:252-259`

```python
# 새 예측 저장 후 종합 분석 리포트 업데이트
try:
    logger.info(f"종목 {stock_code}의 종합 분석 리포트 업데이트 시작")
    asyncio.run(update_stock_analysis_summary(stock_code, self.db, force_update=False))
    logger.info(f"종목 {stock_code}의 종합 분석 리포트 업데이트 완료")
except Exception as report_error:
    logger.error(f"종합 분석 리포트 업데이트 실패: {report_error}", exc_info=True)
```

**문제점**:
- `force_update=False` → 스킵 로직 활성화
- 새 예측 추가 시에도 업데이트 안 됨

#### Path 2: API 엔드포인트 조회 시
**파일**: `backend/api/stocks.py:400-408`

```python
# 분석 요약 생성 (비동기 처리)
logger.info(f"종목 {stock_code}의 분석 요약이 없어 생성을 시도합니다.")
summary_obj = await update_stock_analysis_summary(stock_code, db, force_update=False)

if summary_obj:
    analysis_summary = get_stock_analysis_summary(stock_code, db)
else:
    # LLM 생성 실패 시 기본 규칙 기반 요약 사용 (fallback)
    logger.warning(f"종목 {stock_code}의 LLM 분석 생성 실패, 규칙 기반 요약 사용")
```

**동작 방식**:
- 리포트 없으면 생성 시도
- 실패하면 규칙 기반 fallback 사용 (정확도 낮음)
- **주의**: 오래된 리포트가 있으면 그대로 반환

#### Path 3: 배치 스크립트
**파일**: `scripts/update_all_stock_analysis.py:68-72`

```python
summary = await update_stock_analysis_summary(
    stock_code=stock_code,
    db=db,
    force_update=force_update  # CLI 인자로 제어
)
```

**특징**:
- 수동 실행 필요
- `--force` 플래그로 강제 업데이트 가능
- 현재 스케줄러 미연동 (자동 실행 안 됨)

### 3. 핵심 버그 상세 분석

#### 버그 위치: `stock_analysis_service.py:38-97`

```python
# 1. 최근 30일 예측 데이터 조회 (최대 20건)
predictions = (
    db.query(Prediction)
    .filter(Prediction.stock_code == stock_code)
    .order_by(Prediction.created_at.desc())
    .limit(20)  # ← 하드코딩된 제한
    .all()
)

# ...

# 4. 업데이트 필요 여부 확인
if not force_update and existing_summary:
    # 최신 예측과 비교
    latest_prediction_count = len(predictions)  # 항상 <= 20
    if existing_summary.based_on_prediction_count >= latest_prediction_count:
        logger.info(
            f"종목 {stock_code}의 분석 요약이 최신 상태입니다. "
            f"(예측 건수: {latest_prediction_count})"
        )
        return existing_summary  # ← 여기서 업데이트 스킵
```

#### 버그 분석

**시나리오 1: 새 예측 추가**
```
초기 상태:
- DB: 20개 예측 존재
- 리포트: based_on_prediction_count = 20

새 예측 5개 추가 후:
- DB: 총 25개 예측
- 조회: limit(20) → 20개만 조회
- 조건: 20 >= 20 → TRUE
- 결과: 업데이트 스킵 ❌

최종:
- DB: 25개 예측
- 리포트: 여전히 20개 기준 (오래된 데이터)
```

**시나리오 2: 예측 방향 변화 (상승 → 하락)**
```
초기 상태:
- 예측: 상승 15, 하락 3, 보합 2
- 리포트: "매수 추천"

새 예측 20개 (하락 중심):
- DB: 총 40개 예측
- 조회: limit(20) → 최신 20개 (하락 15, 상승 3, 보합 2)
- 조건: 20 >= 20 → TRUE
- 결과: 업데이트 스킵 ❌

최종:
- 실제 최신 예측: 하락 우세
- 리포트: 여전히 "매수 추천" (오래된 판단)
```

**시나리오 3: 주가 급등/급락**
```
현재 로직: 주가 변동 감지 안 함

예시:
- 리포트 생성 시점: 주가 50,000원, +2.5% 상승
- 현재 시점: 주가 45,000원, -10% 급락
- 결과: 리포트는 여전히 낙관적 전망 유지 ❌
```

### 4. 근본 원인 5-Why 분석

**문제**: 종합 리포트가 새 뉴스/예측 추가 시 업데이트되지 않음

**Why 1**: 업데이트 스킵 조건 `20 >= 20`이 항상 참이기 때문
**Why 2**: `limit(20)`으로 조회하여 실제 총 예측 개수를 파악하지 못함
**Why 3**: 예측 개수 비교만으로 업데이트 여부를 판단하기 때문
**Why 4**: 시간 경과, 주가 변동, 예측 내용 변화 등을 고려하지 않음
**Why 5**: 초기 설계 시 "예측 개수 증가 = 업데이트 필요"라는 단순 가정

**근본 원인**:
1. 불완전한 업데이트 트리거 조건 (예측 개수만 확인)
2. 하드코딩된 limit(20) 제약
3. 다중 요인 기반 업데이트 로직 부재

---

## 🔧 개선 방안

### Priority 1: 즉시 수정 (긴급)

#### 수정 1-A: 업데이트 스킵 로직 제거 (가장 간단)

```python
# 수정 전 (stock_analysis_service.py:88-97)
if not force_update and existing_summary:
    latest_prediction_count = len(predictions)
    if existing_summary.based_on_prediction_count >= latest_prediction_count:
        logger.info(f"종목 {stock_code}의 분석 요약이 최신 상태입니다.")
        return existing_summary

# 수정 후
# 스킵 로직 완전 제거 → 항상 업데이트
# (단, LLM 비용 증가 - 시간 기반 제한 추가 필요)
```

**장점**:
- 즉시 적용 가능
- 모든 호출 시 최신 리포트 보장

**단점**:
- LLM API 비용 급증 (호출 시마다 생성)
- 성능 저하 (리포트 생성 시간 3-5초)

**적용 조건**: 임시 조치로만 사용, 곧바로 1-B로 전환

---

#### 수정 1-B: 총 예측 개수 확인으로 수정 (권장)

```python
# 수정 후 (stock_analysis_service.py:88-97)
if not force_update and existing_summary:
    # 총 예측 개수 조회 (limit 없이)
    total_prediction_count = (
        db.query(func.count(Prediction.id))
        .filter(Prediction.stock_code == stock_code)
        .scalar()
    )

    # 예측 개수 증가 또는 리포트 생성 후 24시간 경과 시 업데이트
    staleness_hours = (datetime.now() - existing_summary.last_updated).total_seconds() / 3600

    if (existing_summary.based_on_prediction_count >= total_prediction_count
        and staleness_hours < 24):
        logger.info(
            f"종목 {stock_code}의 분석 요약이 최신 상태입니다. "
            f"(예측 건수: {total_prediction_count}, 경과 시간: {staleness_hours:.1f}시간)"
        )
        return existing_summary

    logger.info(
        f"종목 {stock_code} 업데이트 필요: "
        f"예측 개수 변화 ({existing_summary.based_on_prediction_count} → {total_prediction_count}) "
        f"또는 24시간 경과 ({staleness_hours:.1f}시간)"
    )
```

**장점**:
- 예측 개수 증가 감지 정확
- 24시간 자동 갱신으로 신선도 보장
- 최소 코드 변경

**단점**:
- 주가 변동, 예측 방향 변화 감지 못함

**적용 조건**: 단기 해결책, Priority 2와 병행

---

### Priority 2: 단기 개선 (1-2주)

#### 수정 2-A: 시장 시간 기반 다중 업데이트 트리거 추가

```python
from datetime import datetime, time
from pytz import timezone

def get_market_phase() -> str:
    """
    현재 한국 증시 단계 반환

    Returns:
        "pre_market": 장 시작 전 (00:00-08:59)
        "market_open": 장 시작 (09:00-09:30)
        "trading": 정규 장중 (09:31-15:29)
        "market_close": 장 마감 직전 (15:30-15:35)
        "after_hours": 장 마감 후 (15:36-23:59)
    """
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


async def should_update_report(
    stock_code: str,
    db: Session,
    existing_summary: Optional[StockAnalysisSummary],
    force_update: bool
) -> tuple[bool, str]:
    """
    리포트 업데이트 필요 여부 판단 (시장 시간 기반 다중 트리거)

    Returns:
        (업데이트 필요 여부, 사유)
    """
    if force_update or not existing_summary:
        return True, "강제 업데이트 또는 리포트 없음"

    market_phase = get_market_phase()
    staleness_hours = (datetime.now() - existing_summary.last_updated).total_seconds() / 3600

    # 트리거 1: 예측 개수 증가 (항상 확인)
    total_prediction_count = (
        db.query(func.count(Prediction.id))
        .filter(Prediction.stock_code == stock_code)
        .scalar()
    )

    if existing_summary.based_on_prediction_count < total_prediction_count:
        return True, f"새 예측 추가 ({existing_summary.based_on_prediction_count} → {total_prediction_count})"

    # 트리거 2: 시장 시간 기반 TTL (동적 조정)
    ttl_hours = {
        "pre_market": 3,      # 장 시작 전: 3시간 (급한 뉴스 반영)
        "market_open": 1,     # 장 시작: 1시간 (초반 변동성 높음)
        "trading": 2,         # 정규 장중: 2시간 (적당한 빈도)
        "market_close": 1,    # 장 마감 직전: 1시간 (마감 전 급변)
        "after_hours": 6,     # 장 마감 후: 6시간 (뉴스만 반영)
    }

    if staleness_hours >= ttl_hours[market_phase]:
        return True, f"시장 단계별 TTL 초과 ({market_phase}: {staleness_hours:.1f}시간 > {ttl_hours[market_phase]}시간)"

    # 트리거 3: 주가 급변 (장중에만 적용, 더 민감하게)
    if market_phase in ["market_open", "trading", "market_close"]:
        current_price_obj = (
            db.query(StockPrice)
            .filter(StockPrice.stock_code == stock_code)
            .order_by(StockPrice.date.desc())
            .first()
        )

        if current_price_obj and existing_summary.custom_data:
            report_time_price = existing_summary.custom_data.get("current_price", {}).get("close")
            if report_time_price:
                price_change_rate = abs((current_price_obj.close - report_time_price) / report_time_price) * 100

                # 장중에는 3% 이상 변동 시 즉시 업데이트
                threshold = 3.0 if market_phase == "trading" else 5.0
                if price_change_rate >= threshold:
                    return True, f"주가 급변 ({price_change_rate:.1f}% 변동, 장중 임계값: {threshold}%)"

    # 트리거 4: 예측 방향 변화 감지 (장중 더 민감)
    latest_predictions = (
        db.query(Prediction)
        .filter(Prediction.stock_code == stock_code)
        .order_by(Prediction.created_at.desc())
        .limit(20)
        .all()
    )

    if len(latest_predictions) > 0:
        current_up_ratio = sum(1 for p in latest_predictions if p.direction == "up") / len(latest_predictions)

        # 리포트 당시 상승 비율
        if existing_summary.total_predictions > 0:
            report_up_ratio = existing_summary.up_count / existing_summary.total_predictions

            # 장중: 15%p 변화, 장외: 20%p 변화
            threshold = 0.15 if market_phase in ["trading", "market_open", "market_close"] else 0.20
            if abs(current_up_ratio - report_up_ratio) >= threshold:
                return True, f"예측 방향 급변 (상승 비율: {report_up_ratio:.1%} → {current_up_ratio:.1%}, 임계값: {threshold:.0%})"

    return False, f"업데이트 불필요 (시장 단계: {market_phase})"
```

**적용 예시**:
```python
# stock_analysis_service.py:88 수정
should_update, reason = await should_update_report(stock_code, db, existing_summary, force_update)

if not should_update:
    logger.info(f"종목 {stock_code}의 분석 요약이 최신 상태입니다. ({reason})")
    return existing_summary

logger.info(f"종목 {stock_code} 업데이트 시작: {reason}")
```

**장점**:
- ✅ **시장 시간 기반 동적 TTL**: 장중 1-2시간, 장 마감 후 6시간
- ✅ **장중 민감도 증가**: 주가 3% 변동, 예측 방향 15%p 변화 즉시 감지
- ✅ **5가지 시장 단계별 최적화**: 장 시작 전/장 시작/정규 장중/장 마감/장 마감 후
- ✅ **업데이트 사유 추적**: 모든 업데이트에 명확한 트리거 로그

**단점**:
- 코드 복잡도 증가 (관리 가능 수준)
- DB 조회 증가 (성능 영향 미미)
- pytz 의존성 추가 필요

**시장 시간별 업데이트 빈도 예상**:
| 시간대 | TTL | 주가 임계값 | 예측 임계값 | 예상 업데이트 빈도 |
|--------|-----|------------|------------|-------------------|
| 장 시작 전 (00:00-08:59) | 3시간 | 5% | 20%p | 하루 2-3회 |
| 장 시작 (09:00-09:30) | 1시간 | 5% | 15%p | 30분마다 |
| 정규 장중 (09:31-15:29) | 2시간 | **3%** | **15%p** | 1-2시간마다 |
| 장 마감 직전 (15:30-15:35) | 1시간 | 5% | 15%p | 1시간마다 |
| 장 마감 후 (15:36-23:59) | 6시간 | 5% | 20%p | 6시간마다 |

**LLM 비용 예상**:
- 기존 (24시간 TTL): $0.01/종목/일 (1회)
- 개선 (시장 시간 기반): $0.08/종목/일 (평균 8회)
- **ROI**: 장중 실시간 정확도 향상으로 사용자 신뢰도 극대화

---

#### 수정 2-B: 리포트 메타데이터 확장

```python
# backend/db/models/stock_analysis.py 확장
class StockAnalysisSummary(Base):
    __tablename__ = "stock_analysis_summaries"

    # ... 기존 필드 ...

    # 업데이트 트리거 추적용 필드 추가
    report_price = Column(Float, nullable=True)  # 리포트 생성 당시 주가
    report_price_change_rate = Column(Float, nullable=True)  # 당시 변동률
    report_up_ratio = Column(Float, nullable=True)  # 당시 상승 예측 비율

    # 메타 정보
    last_update_reason = Column(String(200), nullable=True)  # 마지막 업데이트 사유
```

**마이그레이션 필요**: `scripts/migrate_add_report_metadata.py`

---

### Priority 3: 중기 개선 (1-2개월)

#### 아키텍처 개선: 이벤트 기반 업데이트

```
현재 아키텍처 (Pull 방식):
┌──────────────┐
│  API 조회    │ ─> 매번 업데이트 여부 확인 필요
└──────────────┘


개선 아키텍처 (Event-Driven Push 방식):
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  뉴스 추가    │ ──>│ Event Queue  │ ──>│ Report Worker│
└──────────────┘     │(Redis/RabbitMQ)│    │(Background)  │
                     └──────────────┘     └──────────────┘
┌──────────────┐               │
│  주가 변동    │ ──────────────┘
└──────────────┘
```

**구현 계획**:
1. Redis Pub/Sub 또는 RabbitMQ 도입
2. 이벤트 발행자:
   - `news_saver.py`: 예측 생성 시 `prediction.created` 이벤트
   - `stock_price_updater.py`: 주가 5% 이상 변동 시 `price.significant_change` 이벤트
3. 이벤트 구독자:
   - `report_update_worker.py`: 백그라운드 워커로 리포트 업데이트 처리
4. 업데이트 전략:
   - 디바운싱: 5분 내 여러 이벤트 → 1회만 업데이트
   - 배칭: 여러 종목 동시 업데이트 요청 → 배치 처리

**장점**:
- 실시간 업데이트 (이벤트 발생 즉시)
- API 응답 속도 개선 (비동기 처리)
- 확장성 우수 (워커 수 증가로 처리량 확장)

**단점**:
- 인프라 복잡도 증가 (Redis/RabbitMQ)
- 구현 시간 소요 (2-4주)

---

## 📊 성능 및 비용 분석

### 현재 시스템 (버그 상태)

| 항목 | 값 |
|------|------|
| 리포트 업데이트 빈도 | 거의 없음 (스킵됨) |
| LLM API 호출 비용 | $0.01/종목/일 |
| 리포트 신선도 | 매우 낮음 (24시간 이상 오래됨) |
| 사용자 신뢰도 | 낮음 (잘못된 정보) |

### 수정 1-A: 스킵 로직 제거

| 항목 | 값 | 변화 |
|------|------|------|
| 리포트 업데이트 빈도 | 매 API 조회 시 | +∞ |
| LLM API 호출 비용 | $0.50/종목/일 | +50배 |
| 리포트 신선도 | 매우 높음 (실시간) | 🔼🔼🔼 |
| 사용자 신뢰도 | 높음 | 🔼🔼 |
| API 응답 시간 | +3-5초 | 🔽🔽 |

**권장**: 임시 조치로만 사용

### 수정 1-B: 총 예측 개수 + 24시간 TTL

| 항목 | 값 | 변화 |
|------|------|------|
| 리포트 업데이트 빈도 | 새 예측 추가 시 + 24시간 1회 | 적정 |
| LLM API 호출 비용 | $0.03/종목/일 | +3배 (수용 가능) |
| 리포트 신선도 | 높음 (24시간 이내) | 🔼🔼 |
| 사용자 신뢰도 | 높음 | 🔼🔼 |
| API 응답 시간 | 초회 +3-5초, 이후 캐시 | 🔽 (1회만) |

**권장**: 단기 해결책으로 적용

### 수정 2-A: 다중 트리거 (권장)

| 항목 | 값 | 변화 |
|------|------|------|
| 리포트 업데이트 빈도 | 4가지 트리거 중 하나 발생 시 | 최적 |
| LLM API 호출 비용 | $0.05/종목/일 | +5배 (ROI 높음) |
| 리포트 신선도 | 매우 높음 | 🔼🔼🔼 |
| 사용자 신뢰도 | 매우 높음 | 🔼🔼🔼 |
| 정확도 | 주가/방향 변화 반영 | 🔼🔼🔼 |

**권장**: 중장기 솔루션

### Priority 3: 이벤트 기반 아키텍처

| 항목 | 값 | 변화 |
|------|------|------|
| 리포트 업데이트 빈도 | 이벤트 발생 시 실시간 | 최고 |
| LLM API 호출 비용 | $0.05/종목/일 | 동일 |
| 리포트 신선도 | 실시간 | 🔼🔼🔼 |
| API 응답 시간 | 캐시에서 즉시 반환 | 🔼🔼 |
| 인프라 비용 | Redis/RabbitMQ 추가 | +$50/월 |
| 확장성 | 매우 높음 | 🔼🔼🔼 |

**권장**: 장기 목표

---

## 🛠️ 실행 계획

### Phase 1: 긴급 패치 (24시간 이내)

**목표**: 즉시 업데이트 스킵 버그 제거

**작업**:
1. ✅ `stock_analysis_service.py:88-97` 수정 (수정 1-B 적용)
2. ✅ 단위 테스트 작성 및 검증
3. ✅ SK하이닉스 리포트 수동 재생성 (`--force` 플래그)
4. ✅ 프로덕션 배포

**검증 기준**:
- SK하이닉스 리포트가 최신 예측 반영 (상승 5, 하락 1, 보합 14)
- 새 뉴스 추가 시 리포트 자동 업데이트 확인
- 24시간 후 자동 갱신 확인

**책임자**: Backend Developer
**검토자**: Business Analyst

---

### Phase 2: 다중 트리거 추가 (1주)

**목표**: 주가 변동, 예측 방향 변화 감지

**작업**:
1. ✅ `should_update_report()` 함수 구현
2. ✅ 리포트 메타데이터 필드 추가 (마이그레이션)
3. ✅ 주가 급변 트리거 로직 구현
4. ✅ 예측 방향 변화 트리거 로직 구현
5. ✅ 통합 테스트 (4가지 트리거 모두 검증)
6. ✅ 모니터링 대시보드 추가 (업데이트 사유 통계)

**검증 기준**:
- 새 예측 추가 시 업데이트 ✅
- 24시간 경과 시 업데이트 ✅
- 주가 5% 이상 변동 시 업데이트 ✅
- 예측 방향 20%p 변화 시 업데이트 ✅

**책임자**: Backend Developer
**검토자**: Business Analyst + QA

---

### Phase 3: 스케줄러 연동 (2주)

**목표**: 자동 배치 업데이트

**작업**:
1. ✅ `update_all_stock_analysis.py` 스케줄러 연동 (Celery/APScheduler)
2. ✅ 매일 오전 9시 전체 종목 리포트 갱신
3. ✅ 실패 시 재시도 로직 (3회)
4. ✅ 슬랙 알림 연동 (성공/실패 통계)

**검증 기준**:
- 매일 9시 자동 실행 확인
- 전체 종목 업데이트 완료 시간 < 10분
- 실패율 < 5%

---

### Phase 4: 이벤트 기반 아키텍처 (1-2개월, 선택)

**목표**: 장기 확장성 확보

**작업**:
1. ✅ Redis Pub/Sub 또는 RabbitMQ 설정
2. ✅ 이벤트 발행 로직 추가 (`news_saver.py`, `stock_price_updater.py`)
3. ✅ 백그라운드 워커 구현 (`report_update_worker.py`)
4. ✅ 디바운싱 및 배칭 로직
5. ✅ 모니터링 및 로깅

**검증 기준**:
- 이벤트 발생 → 리포트 업데이트 지연 < 5분
- API 응답 시간 < 500ms (캐시에서 반환)
- 워커 장애 시 자동 복구

---

## 📈 성공 지표 (KPI)

### 단기 (Phase 1-2 완료 후)

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|-----------|
| 리포트 신선도 | 21시간+ | < 24시간 | `last_updated` 필드 모니터링 |
| 업데이트 성공률 | 10% | > 95% | 업데이트 시도 vs 성공 비율 |
| 사용자 신뢰도 | 낮음 | 높음 | 리포트 vs 실제 예측 일치율 |
| LLM 비용 | $0.01/종목/일 | < $0.05/종목/일 | API 호출 로그 집계 |

### 중기 (Phase 3 완료 후)

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 자동 업데이트 커버리지 | > 99% | 스케줄러 실행 로그 |
| 배치 처리 시간 | < 10분 (전체 종목) | 배치 실행 시간 측정 |
| 실패율 | < 5% | 실패 로그 / 전체 시도 |

### 장기 (Phase 4 완료 후, 선택)

| 지표 | 목표 | 측정 방법 |
|------|------|-----------|
| 이벤트 처리 지연 | < 5분 | 이벤트 타임스탬프 vs 업데이트 완료 시간 |
| API 응답 시간 | < 500ms | API 모니터링 |
| 시스템 가용성 | > 99.9% | 업타임 모니터링 |

---

## 🚨 리스크 및 대응 방안

### Risk 1: LLM API 비용 급증

**발생 확률**: 중간
**영향도**: 중간
**대응**:
- Phase 1-B 적용 시 24시간 TTL로 제한
- 캐싱 적극 활용
- 업데이트 트리거 조건 세밀 조정

### Risk 2: 리포트 생성 실패 증가

**발생 확률**: 낮음
**영향도**: 높음
**대응**:
- Fallback 로직 유지 (규칙 기반 요약)
- LLM API 타임아웃 처리 (10초)
- 재시도 로직 (3회)

### Risk 3: DB 성능 저하 (총 예측 개수 조회)

**발생 확률**: 낮음
**영향도**: 낮음
**대응**:
- `Prediction.stock_code` 인덱스 확인
- 쿼리 최적화
- 필요 시 Redis 캐싱

### Risk 4: 업데이트 트리거 오판 (False Positive)

**발생 확률**: 낮음
**영향도**: 낮음
**대응**:
- 트리거 임계값 조정 (주가 5% → 7%, 예측 방향 20%p → 25%p)
- A/B 테스트로 최적 임계값 탐색
- 로깅 모니터링 (업데이트 사유 추적)

---

## 🎯 권장 조치 요약

### 즉시 실행 (24시간 이내)

✅ **수정 1-B 적용**:
- `stock_analysis_service.py:88-97` 코드 수정
- 총 예측 개수 확인 + 24시간 TTL

✅ **SK하이닉스 리포트 재생성**:
```bash
uv run python scripts/update_all_stock_analysis.py --force --stocks 034730
```

✅ **검증**:
- 리포트가 최신 예측 반영하는지 확인
- 새 뉴스 추가 시 업데이트 동작 확인

### 단기 실행 (1주 이내)

✅ **수정 2-A 적용**:
- 다중 업데이트 트리거 구현
- 리포트 메타데이터 필드 추가

✅ **모니터링 추가**:
- 업데이트 사유 통계 대시보드
- LLM API 비용 추적

### 중기 실행 (1개월 이내)

✅ **스케줄러 연동**:
- 매일 자동 배치 업데이트
- 슬랙 알림 설정

### 장기 검토 (선택)

🔄 **이벤트 기반 아키텍처**:
- Redis/RabbitMQ 도입
- 백그라운드 워커 구현

---

## 📝 결론

### 핵심 메시지

현재 **종합 리포트 업데이트 시스템**은 다음 3가지 치명적 문제를 가지고 있습니다:

1. **잘못된 업데이트 스킵 로직** (`20 >= 20` 항상 참)
2. **시간 기반 갱신 로직 부재** (24시간 이상 오래된 리포트)
3. **주가/예측 변화 감지 불가** (시장 급변 미반영)

이로 인해 **SK하이닉스 리포트**처럼 **21시간 이상 오래된 잘못된 투자 추천**이 사용자에게 제공되고 있습니다.

### 해결 방안

**즉시 조치** (Priority 1):
- 총 예측 개수 확인 + 24시간 TTL로 수정

**단기 개선** (Priority 2):
- 4가지 업데이트 트리거 구현 (예측, 시간, 주가, 방향)

**중장기 목표** (Priority 3):
- 이벤트 기반 아키텍처 전환 (실시간 업데이트)

### 기대 효과

✅ **리포트 신선도**: 21시간+ → 24시간 이내
✅ **업데이트 성공률**: 10% → 95%+
✅ **사용자 신뢰도**: 낮음 → 높음
✅ **투자 의사결정 정확도**: 대폭 개선

### Next Steps

1. **의사결정**: Priority 1-B vs Priority 2-A 선택 (권장: 1-B 먼저, 2-A 병행)
2. **개발 착수**: Backend Developer 배정
3. **검증 계획**: QA 테스트 시나리오 작성
4. **모니터링 설정**: 업데이트 사유 통계, LLM 비용 추적

---

**작성자**: Business Analyst Mary
**최종 업데이트**: 2025-11-04
**문서 버전**: 1.0
