# Story 006.3: 데이터 품질 모니터링 시스템

**Epic**: Epic 006 | **Priority**: ⭐⭐⭐⭐ | **Effort**: 4-6일 | **Dependencies**: Story 006.1

---

## Overview

데이터 수집 품질을 실시간 모니터링하고 이상 징후를 자동 감지합니다.

**핵심**: 이상 감지 + 자동 알림 + 대시보드

---

## Acceptance Criteria

1. ✅ 품질 메트릭 정의 (5가지)
2. ✅ 실시간 모니터링 시스템
3. ✅ 이상 감지 알고리즘
4. ✅ 텔레그램 알림 통합
5. ✅ 품질 대시보드 (Grafana/간단한 API)

---

## Quality Metrics

### 1. 수집 성공률

```python
# backend/monitoring/metrics.py

from datetime import datetime, timedelta


class QualityMetrics:
    """데이터 품질 메트릭"""

    def __init__(self):
        self.db = SessionLocal()

    def calculate_collection_success_rate(
        self,
        hours: int = 24
    ) -> dict:
        """수집 성공률"""

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # 기대 수집 건수
        stock_codes = get_active_stocks()
        if hours <= 24:
            # 일봉: 1일 = 50개
            expected_count = len(stock_codes)
        else:
            # 분봉: 1일 = 50개 × 390분 = 19,500건
            trading_minutes = 390 * (hours // 24)
            expected_count = len(stock_codes) * trading_minutes

        # 실제 수집 건수
        actual_count = self.db.query(StockPrice).filter(
            StockPrice.created_at >= start_time,
            StockPrice.created_at <= end_time
        ).count()

        # 성공률
        success_rate = (actual_count / expected_count) * 100 if expected_count > 0 else 0

        return {
            "metric": "collection_success_rate",
            "period_hours": hours,
            "expected": expected_count,
            "actual": actual_count,
            "success_rate": success_rate,
            "threshold": 98.0,
            "status": "✅" if success_rate >= 98 else "⚠️"
        }

    def calculate_data_freshness(self) -> dict:
        """데이터 신선도 (마지막 수집 이후 경과 시간)"""

        latest = self.db.query(
            func.max(StockPrice.created_at)
        ).scalar()

        if not latest:
            return {
                "metric": "data_freshness",
                "status": "❌",
                "message": "데이터 없음"
            }

        elapsed = (datetime.now() - latest).total_seconds() / 60  # 분

        return {
            "metric": "data_freshness",
            "last_collection": latest.isoformat(),
            "elapsed_minutes": elapsed,
            "threshold_minutes": 5,
            "status": "✅" if elapsed <= 5 else "⚠️"
        }

    def calculate_price_anomaly_rate(self, days: int = 7) -> dict:
        """가격 이상치 비율"""

        start_date = datetime.now().date() - timedelta(days=days)

        # 전체 데이터
        total_count = self.db.query(StockPrice).filter(
            StockPrice.date >= start_date
        ).count()

        # 이상치 (일일 변동률 ±30% 이상)
        anomaly_count = self.db.query(StockPrice).filter(
            StockPrice.date >= start_date,
            or_(
                StockPrice.change_pct > 30,
                StockPrice.change_pct < -30
            )
        ).count()

        anomaly_rate = (anomaly_count / total_count) * 100 if total_count > 0 else 0

        return {
            "metric": "price_anomaly_rate",
            "period_days": days,
            "total": total_count,
            "anomalies": anomaly_count,
            "anomaly_rate": anomaly_rate,
            "threshold": 1.0,  # 1% 이하
            "status": "✅" if anomaly_rate <= 1 else "⚠️"
        }

    def calculate_api_error_rate(self, hours: int = 24) -> dict:
        """API 에러율"""

        start_time = datetime.now() - timedelta(hours=hours)

        # Redis에서 API 호출 로그 조회 (가정)
        total_calls = redis_client.get(f"api_calls:{hours}h") or 0
        error_calls = redis_client.get(f"api_errors:{hours}h") or 0

        total_calls = int(total_calls)
        error_calls = int(error_calls)

        error_rate = (error_calls / total_calls) * 100 if total_calls > 0 else 0

        return {
            "metric": "api_error_rate",
            "period_hours": hours,
            "total_calls": total_calls,
            "error_calls": error_calls,
            "error_rate": error_rate,
            "threshold": 1.0,  # 1% 이하
            "status": "✅" if error_rate <= 1 else "⚠️"
        }

    def calculate_data_completeness(self, date: datetime.date = None) -> dict:
        """데이터 완전성 (OHLCV 필드 누락 여부)"""

        if not date:
            date = datetime.now().date()

        # 해당 날짜 데이터
        records = self.db.query(StockPrice).filter(
            StockPrice.date == date
        ).all()

        # 완전성 체크
        incomplete_count = 0
        for record in records:
            if any([
                record.open is None,
                record.high is None,
                record.low is None,
                record.close is None,
                record.volume is None
            ]):
                incomplete_count += 1

        completeness_rate = ((len(records) - incomplete_count) / len(records)) * 100 if records else 0

        return {
            "metric": "data_completeness",
            "date": date.isoformat(),
            "total": len(records),
            "incomplete": incomplete_count,
            "completeness_rate": completeness_rate,
            "threshold": 99.0,
            "status": "✅" if completeness_rate >= 99 else "⚠️"
        }
```

---

## Monitoring System

### 1. 실시간 모니터링 서비스

```python
# backend/monitoring/monitor_service.py

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler


class MonitorService:
    """데이터 품질 모니터링 서비스"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.metrics = QualityMetrics()
        self.alert_service = AlertService()

    def start(self):
        """모니터링 시작"""

        # 매 5분마다 품질 체크
        self.scheduler.add_job(
            func=self.check_quality,
            trigger="interval",
            minutes=5,
            id="quality_check"
        )

        # 매 1시간마다 종합 리포트
        self.scheduler.add_job(
            func=self.generate_hourly_report,
            trigger="interval",
            hours=1,
            id="hourly_report"
        )

        self.scheduler.start()
        logger.info("✅ 품질 모니터링 시작")

    async def check_quality(self):
        """품질 체크 및 알림"""

        # 5가지 메트릭 계산
        metrics = [
            self.metrics.calculate_collection_success_rate(hours=1),
            self.metrics.calculate_data_freshness(),
            self.metrics.calculate_price_anomaly_rate(days=1),
            self.metrics.calculate_api_error_rate(hours=1),
            self.metrics.calculate_data_completeness()
        ]

        # 이상 감지
        alerts = []
        for metric in metrics:
            if metric.get("status") == "⚠️":
                alerts.append(metric)

        # 알림 발송
        if alerts:
            await self.alert_service.send_quality_alert(alerts)

        # Redis에 저장 (대시보드용)
        await self._save_metrics_to_redis(metrics)

    async def generate_hourly_report(self):
        """시간별 품질 리포트"""

        metrics = [
            self.metrics.calculate_collection_success_rate(hours=24),
            self.metrics.calculate_price_anomaly_rate(days=7),
            self.metrics.calculate_api_error_rate(hours=24)
        ]

        # Markdown 리포트
        report = self._format_report(metrics)

        # 텔레그램 발송
        await self.alert_service.send_telegram_message(
            title="📊 데이터 품질 리포트",
            message=report
        )

    def _format_report(self, metrics: List[dict]) -> str:
        """리포트 포맷팅"""

        lines = ["**데이터 품질 리포트**\n"]

        for metric in metrics:
            status_icon = metric.get("status", "")
            metric_name = metric.get("metric", "")

            if "success_rate" in metric:
                lines.append(
                    f"{status_icon} 수집 성공률: {metric['success_rate']:.2f}%"
                )
            elif "anomaly_rate" in metric:
                lines.append(
                    f"{status_icon} 이상치 비율: {metric['anomaly_rate']:.2f}%"
                )
            elif "error_rate" in metric:
                lines.append(
                    f"{status_icon} API 에러율: {metric['error_rate']:.2f}%"
                )

        return "\n".join(lines)
```

---

## Anomaly Detection

### 이상 감지 알고리즘

```python
# backend/monitoring/anomaly_detector.py

from scipy import stats
import numpy as np


class AnomalyDetector:
    """이상 징후 감지"""

    def detect_sudden_volume_spike(
        self,
        stock_code: str,
        threshold: float = 3.0
    ) -> dict:
        """거래량 급증 감지 (Z-score)"""

        # 최근 30일 거래량
        days_30_ago = datetime.now().date() - timedelta(days=30)
        prices = self.db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code,
            StockPrice.date >= days_30_ago
        ).order_by(StockPrice.date).all()

        if len(prices) < 20:
            return {"detected": False}

        volumes = [p.volume for p in prices]

        # Z-score 계산
        mean_volume = np.mean(volumes)
        std_volume = np.std(volumes)

        latest_volume = volumes[-1]
        z_score = (latest_volume - mean_volume) / std_volume if std_volume > 0 else 0

        return {
            "detected": abs(z_score) >= threshold,
            "stock_code": stock_code,
            "z_score": z_score,
            "latest_volume": latest_volume,
            "mean_volume": mean_volume,
            "threshold": threshold
        }

    def detect_price_gap(
        self,
        stock_code: str,
        gap_threshold: float = 5.0
    ) -> dict:
        """가격 갭 감지 (전일 대비 급변)"""

        # 최근 2일
        recent_prices = self.db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code
        ).order_by(StockPrice.date.desc()).limit(2).all()

        if len(recent_prices) < 2:
            return {"detected": False}

        today = recent_prices[0]
        yesterday = recent_prices[1]

        # 갭 비율
        gap_pct = ((today.open - yesterday.close) / yesterday.close) * 100

        return {
            "detected": abs(gap_pct) >= gap_threshold,
            "stock_code": stock_code,
            "gap_pct": gap_pct,
            "yesterday_close": yesterday.close,
            "today_open": today.open,
            "threshold": gap_threshold
        }
```

---

## Dashboard API

### 품질 메트릭 API

```python
# backend/api/monitoring.py

from fastapi import APIRouter

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/quality-metrics")
async def get_quality_metrics():
    """품질 메트릭 조회"""

    metrics_service = QualityMetrics()

    return {
        "collection_success_rate": metrics_service.calculate_collection_success_rate(hours=24),
        "data_freshness": metrics_service.calculate_data_freshness(),
        "price_anomaly_rate": metrics_service.calculate_price_anomaly_rate(days=7),
        "api_error_rate": metrics_service.calculate_api_error_rate(hours=24),
        "data_completeness": metrics_service.calculate_data_completeness()
    }


@router.get("/health")
async def health_check():
    """헬스 체크"""

    metrics = QualityMetrics()
    freshness = metrics.calculate_data_freshness()

    is_healthy = freshness.get("status") == "✅"

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "details": freshness
    }
```

---

## Definition of Done

- [ ] 5가지 품질 메트릭 구현
- [ ] 실시간 모니터링 서비스
- [ ] 이상 감지 알고리즘 (2가지)
- [ ] 텔레그램 알림 통합
- [ ] 품질 API 엔드포인트
- [ ] 7일 모니터링 테스트
- [ ] 코드 리뷰 및 머지
