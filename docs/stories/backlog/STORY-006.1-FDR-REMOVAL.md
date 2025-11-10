# Story 006.1: FDR 제거 및 마이그레이션 검증

**Epic**: Epic 006 | **Priority**: ⭐⭐⭐⭐⭐ | **Effort**: 4-6일 | **Dependencies**: Epic 003, 004, 005

---

## Overview

KIS API 안정화 후 FDR 의존성을 완전히 제거하고 마이그레이션을 검증합니다.

**핵심**: 안전한 전환 + 롤백 계획 + 완전한 검증

---

## Acceptance Criteria

1. ✅ KIS API 안정성 검증 (30일 연속 99% 성공률)
2. ✅ FDR 수집기 비활성화
3. ✅ `stock_prices` 테이블 `source` 컬럼 검증
4. ✅ 롤백 계획 수립
5. ✅ 의존성 완전 제거 (`FinanceDataReader` 패키지)

---

## Implementation

### 1. 안정성 검증

```python
# scripts/verify_kis_stability.py

from datetime import datetime, timedelta
from backend.models import StockPrice


def verify_kis_stability(days: int = 30) -> dict:
    """
    KIS API 안정성 검증

    Args:
        days: 검증 기간 (기본 30일)

    Returns:
        안정성 리포트
    """
    db = SessionLocal()

    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        # 기대 데이터 수
        trading_days = count_trading_days(start_date, end_date)
        stock_codes = get_active_stocks()
        expected_count = trading_days * len(stock_codes)

        # 실제 KIS 데이터 수
        actual_count = db.query(StockPrice).filter(
            StockPrice.source == "kis",
            StockPrice.date >= start_date,
            StockPrice.date <= end_date
        ).count()

        # 성공률
        success_rate = (actual_count / expected_count) * 100

        # 일별 성공률
        daily_rates = []
        for i in range(trading_days):
            day = start_date + timedelta(days=i)
            if not is_trading_day(day):
                continue

            day_count = db.query(StockPrice).filter(
                StockPrice.source == "kis",
                StockPrice.date == day
            ).count()

            day_rate = (day_count / len(stock_codes)) * 100
            daily_rates.append({
                "date": day,
                "rate": day_rate,
                "status": "✅" if day_rate >= 99 else "⚠️"
            })

        # 연속 성공 일수
        consecutive_days = 0
        for rate_info in reversed(daily_rates):
            if rate_info["rate"] >= 99:
                consecutive_days += 1
            else:
                break

        return {
            "period": f"{start_date} ~ {end_date}",
            "trading_days": trading_days,
            "expected_count": expected_count,
            "actual_count": actual_count,
            "success_rate": success_rate,
            "consecutive_success_days": consecutive_days,
            "daily_rates": daily_rates,
            "is_stable": success_rate >= 99 and consecutive_days >= 30
        }

    finally:
        db.close()


if __name__ == "__main__":
    report = verify_kis_stability(days=30)

    print("\n" + "="*80)
    print("KIS API 안정성 검증")
    print("="*80)

    print(f"\n기간: {report['period']}")
    print(f"거래일: {report['trading_days']}일")
    print(f"기대 데이터: {report['expected_count']:,}건")
    print(f"실제 데이터: {report['actual_count']:,}건")
    print(f"성공률: {report['success_rate']:.2f}%")
    print(f"연속 성공: {report['consecutive_success_days']}일")

    print(f"\n안정성 승인: {'✅ PASS' if report['is_stable'] else '❌ FAIL'}")

    if not report['is_stable']:
        print("\n⚠️  안정성 기준 미달. FDR 제거를 보류합니다.")
        exit(1)
```

### 2. FDR 수집기 비활성화

```python
# backend/crawlers/daily_price_crawler.py

class DailyPriceCrawler:
    def __init__(self):
        self.kis_client = KISClient()
        # self.fdr_client = FDRClient()  # ⭐ 제거

    async def collect_daily_prices(
        self,
        stock_codes: List[str],
        target_date: datetime
    ):
        """일봉 수집 (KIS만)"""

        for stock_code in stock_codes:
            try:
                # KIS API 호출
                df = await self.kis_client.get_daily_prices(
                    stock_code=stock_code,
                    start_date=target_date,
                    end_date=target_date
                )

                # DB 저장
                self._save_to_db(stock_code, df, source="kis")

                logger.info(f"✅ {stock_code} 일봉 수집 성공")

            except Exception as e:
                logger.error(f"❌ {stock_code} 일봉 수집 실패: {e}")

                # ⚠️  FDR 폴백 제거됨
                # 실패 시 알림만 발송
                await self._send_failure_alert(stock_code, e)
```

### 3. 데이터 검증

```python
# scripts/verify_migration.py

def verify_data_migration():
    """마이그레이션 검증"""

    db = SessionLocal()

    try:
        # 1. source 컬럼 분포
        source_distribution = db.query(
            StockPrice.source,
            func.count(StockPrice.id)
        ).group_by(StockPrice.source).all()

        print("\n=== Source 컬럼 분포 ===")
        for source, count in source_distribution:
            print(f"{source}: {count:,}건")

        # 2. FDR 데이터 잔존 확인
        fdr_count = db.query(StockPrice).filter(
            StockPrice.source == "fdr"
        ).count()

        print(f"\nFDR 데이터 잔존: {fdr_count:,}건")

        # 3. 최근 30일 KIS 커버리지
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        recent_kis = db.query(StockPrice).filter(
            StockPrice.source == "kis",
            StockPrice.date >= thirty_days_ago
        ).count()

        print(f"최근 30일 KIS 데이터: {recent_kis:,}건")

        # 승인 기준
        criteria = {
            "FDR 데이터 0건": fdr_count == 0,
            "최근 30일 KIS 커버리지 100%": recent_kis >= 1500  # 50종목 × 30일
        }

        print("\n=== 승인 기준 ===")
        for criterion, passed in criteria.items():
            print(f"{criterion}: {'✅ PASS' if passed else '❌ FAIL'}")

        return all(criteria.values())

    finally:
        db.close()
```

### 4. 롤백 계획

```python
# scripts/rollback_to_fdr.py

def rollback_to_fdr():
    """
    KIS → FDR 롤백 (긴급 상황)

    1. FDR 수집기 재활성화
    2. KIS 수집기 비활성화
    3. 알림 발송
    """

    print("\n⚠️  긴급 롤백 시작...")

    # 1. FDR 수집기 재활성화
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=collect_daily_prices_fdr,
        trigger="cron",
        hour=15,
        minute=40,
        id="fdr_daily_collector"
    )
    scheduler.start()

    # 2. KIS 수집기 일시 중지
    scheduler.pause_job("kis_daily_collector")

    # 3. 알림
    send_admin_alert(
        title="🚨 FDR 롤백 실행",
        message="KIS API 장애로 FDR 수집기를 재활성화했습니다."
    )

    print("✅ 롤백 완료. FDR 수집기 활성화됨.")
```

### 5. 의존성 제거

```bash
# pyproject.toml 수정

# 제거할 의존성
# finance-datareader = "^0.9.50"

# 패키지 제거
uv pip uninstall finance-datareader

# 확인
uv pip list | grep finance
```

---

## Testing Strategy

### 1. 안정성 테스트
```bash
python scripts/verify_kis_stability.py
# 목표: 30일 연속 99% 성공률
```

### 2. 마이그레이션 검증
```bash
python scripts/verify_migration.py
# 목표: FDR 데이터 0건, KIS 100% 커버리지
```

### 3. 롤백 훈련
```bash
# 롤백 시뮬레이션
python scripts/rollback_to_fdr.py
# 복구 시간 <5분 목표
```

---

## Rollback Plan

### 롤백 조건
- KIS API 장애 (3일 연속 성공률 <95%)
- 데이터 품질 문제 (오차율 >1%)
- 프로덕션 장애

### 롤백 절차
1. FDR 수집기 재활성화 (자동)
2. KIS 수집기 일시 중지
3. 관리자 알림 발송
4. 문제 원인 분석
5. KIS 재시도 또는 FDR 유지

---

## Definition of Done

- [ ] KIS 안정성 검증 (30일 연속 99%)
- [ ] FDR 수집기 제거
- [ ] 마이그레이션 검증 완료
- [ ] 롤백 계획 수립 및 테스트
- [ ] `FinanceDataReader` 패키지 제거
- [ ] 프로덕션 모니터링 (7일)
- [ ] 코드 리뷰 및 머지
