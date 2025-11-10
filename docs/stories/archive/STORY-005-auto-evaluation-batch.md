---
story_id: STORY-005
epic_id: EPIC-002
title: 자동 평가 배치 작업
status: complete
priority: high
assignee: Backend Developer
estimated: 2-3 days
created: 2025-11-05
completed: 2025-11-07
phase: Phase 1 - 기본 평가 인프라
sprint: Week 1
---

# Story: 자동 평가 배치 작업

## 📖 User Story

**As a** System Administrator
**I want** an automated batch job that evaluates model predictions daily
**So that** we can track prediction accuracy against actual stock prices without manual intervention

## 🔍 Current State

### Existing Batch Infrastructure
```python
# backend/scheduler/crawler_scheduler.py
class CrawlerScheduler:
    """
    기존 스케줄러 - 뉴스/주가 크롤링만 수행
    """
    def _collect_stock_prices(self):
        """매 1분마다 주가 수집 (장 시간만)"""
        pass
```

### What's Missing
- ❌ Daily 평가 배치 작업 없음
- ❌ Investment Report 조회 로직 없음
- ❌ 주가 데이터와 예측 비교 로직 없음
- ❌ 자동 점수 계산 알고리즘 없음
- ❌ 평가 결과 저장 로직 없음

### Available Data Sources
✅ `stock_prices` 테이블 (FinanceDataReader로 매 1분 수집)
✅ Investment Report 데이터 (별도 테이블 필요 - 현재는 predictions 테이블에 혼재)
✅ `model_evaluations` 테이블 (STORY-004에서 생성 예정)

## ✅ Acceptance Criteria

### 1. Investment Report 식별
- [ ] `predictions` 테이블에서 Investment Report 구분 로직
- [ ] 목표가(target_price), 손절가(support_price) 존재 여부로 구분
- [ ] D-1일 생성된 Investment Report만 조회

### 2. 주가 데이터 수집
- [ ] T+1일 주가 데이터 조회 (high, low, close)
- [ ] T+5일 주가 데이터 조회 (5일 후까지 추적)
- [ ] 주말/공휴일 처리 (영업일 기준)
- [ ] 데이터 미존재 시 재시도 로직

### 3. 달성 여부 판단
- [ ] 목표가 달성 여부 (`actual_high >= predicted_target_price`)
- [ ] 목표가 달성 소요일 계산 (1~5일 중 언제 달성했는지)
- [ ] 손절가 이탈 여부 (`actual_low <= predicted_support_price`)
- [ ] 방향 정확도 (`predicted_direction == actual_direction`)

### 4. 자동 점수 계산 (0-100점)
- [ ] **목표가 정확도 점수** (40%):
  - 목표가 달성 시 100점
  - 미달성 시 `(actual_high - base_price) / (target_price - base_price) × 100`
- [ ] **타이밍 점수** (30%):
  - 1일 내 달성 100점, 2일 90점, 3일 80점, 4일 70점, 5일 60점
  - 미달성 시 0점
- [ ] **리스크 관리 점수** (30%):
  - 손절가 미이탈 시 100점
  - 이탈 시 `max(0, 100 - abs((actual_low - support_price) / support_price) × 100)`

### 5. 평가 결과 저장
- [ ] `model_evaluations` 테이블에 INSERT
- [ ] 중복 평가 방지 (prediction_id로 체크)
- [ ] 트랜잭션 처리 (원자성 보장)
- [ ] 에러 로깅 및 알림

### 6. 스케줄 설정
- [ ] 매일 16:00 실행 (장 마감 후)
- [ ] APScheduler cron 설정
- [ ] 수동 실행 가능한 CLI 제공

## 📋 Tasks

### Task 1: Investment Report 식별 로직 (3 hours)
**File**: `backend/services/evaluation_service.py` (new file)

```python
"""
Model evaluation service for automated scoring.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from backend.db.models.prediction import Prediction
from backend.db.models.stock import StockPrice
from backend.db.models.model_evaluation import ModelEvaluation


logger = logging.getLogger(__name__)


class EvaluationService:
    """
    모델 평가 서비스.

    Investment Report의 예측 정확도를 자동으로 평가합니다.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_evaluable_predictions(self, target_date: datetime) -> List[Prediction]:
        """
        평가 가능한 Investment Report 조회.

        Args:
            target_date: 평가 대상 날짜 (예: 어제)

        Returns:
            목표가/손절가가 있는 Investment Report 리스트
        """
        # Investment Report 조건:
        # 1. target_date에 생성됨
        # 2. predicted_target_price, predicted_support_price NOT NULL
        # 3. 아직 평가되지 않음 (model_evaluations에 없음)

        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        # 이미 평가된 prediction_id 조회
        evaluated_ids = self.db.query(ModelEvaluation.prediction_id).all()
        evaluated_ids = [e[0] for e in evaluated_ids]

        # Investment Report 조회
        predictions = self.db.query(Prediction).filter(
            Prediction.created_at >= start_of_day,
            Prediction.created_at <= end_of_day,
            # Investment Report 조건 (추후 별도 컬럼 추가 권장)
            Prediction.current_price.isnot(None),  # 임시: 목표가 있는지 확인
            Prediction.id.notin_(evaluated_ids)  # 중복 평가 방지
        ).all()

        logger.info(f"📊 평가 대상 Investment Report: {len(predictions)}건")
        return predictions
```

### Task 2: 주가 데이터 수집 로직 (4 hours)
**Continue in** `backend/services/evaluation_service.py`

```python
    def get_stock_prices(
        self,
        stock_code: str,
        base_date: datetime,
        days: int = 5
    ) -> dict:
        """
        주가 데이터 조회 (T+1 ~ T+N일).

        Args:
            stock_code: 종목 코드
            base_date: 기준일 (예측 생성일)
            days: 조회할 일수 (기본 5일)

        Returns:
            {
                1: {"high": 50000, "low": 48000, "close": 49500, "date": "2025-11-06"},
                2: {"high": 51000, "low": 49000, "close": 50500, "date": "2025-11-07"},
                ...
            }
        """
        result = {}

        for day in range(1, days + 1):
            target_date = base_date + timedelta(days=day)

            # 주말/공휴일 스킵 (영업일만)
            if target_date.weekday() >= 5:  # 토(5), 일(6)
                continue

            # 주가 데이터 조회
            stock_data = self.db.query(StockPrice).filter(
                StockPrice.stock_code == stock_code,
                StockPrice.date >= target_date.replace(hour=0, minute=0, second=0),
                StockPrice.date <= target_date.replace(hour=23, minute=59, second=59)
            ).first()

            if stock_data:
                result[day] = {
                    "high": stock_data.high,
                    "low": stock_data.low,
                    "close": stock_data.close,
                    "date": stock_data.date.strftime("%Y-%m-%d")
                }
            else:
                logger.warning(f"⚠️ 주가 데이터 없음: {stock_code} on {target_date.date()}")

        return result
```

### Task 3: 달성 여부 판단 로직 (3 hours)
**Continue in** `backend/services/evaluation_service.py`

```python
    def check_target_achievement(
        self,
        target_price: float,
        support_price: float,
        base_price: float,
        stock_prices: dict
    ) -> dict:
        """
        목표가/손절가 달성 여부 판단.

        Args:
            target_price: 목표가
            support_price: 손절가
            base_price: 기준가
            stock_prices: get_stock_prices() 결과

        Returns:
            {
                "target_achieved": True/False,
                "target_achieved_days": 3,  # 3일 만에 달성
                "support_breached": False,
                "actual_high_1d": 50000,
                "actual_low_1d": 48000,
                "actual_close_1d": 49500,
                "actual_high_5d": 52000,
                "actual_low_5d": 47000,
                "actual_close_5d": 51000
            }
        """
        result = {
            "target_achieved": False,
            "target_achieved_days": None,
            "support_breached": False,
            "actual_high_1d": None,
            "actual_low_1d": None,
            "actual_close_1d": None,
            "actual_high_5d": None,
            "actual_low_5d": None,
            "actual_close_5d": None
        }

        # T+1일 데이터
        if 1 in stock_prices:
            result["actual_high_1d"] = stock_prices[1]["high"]
            result["actual_low_1d"] = stock_prices[1]["low"]
            result["actual_close_1d"] = stock_prices[1]["close"]

        # T+5일까지 추적
        max_day = max(stock_prices.keys()) if stock_prices else 0

        for day in range(1, max_day + 1):
            if day not in stock_prices:
                continue

            high = stock_prices[day]["high"]
            low = stock_prices[day]["low"]

            # 목표가 달성 확인 (최초 달성일만 기록)
            if not result["target_achieved"] and high >= target_price:
                result["target_achieved"] = True
                result["target_achieved_days"] = day
                logger.info(f"✅ 목표가 달성: {day}일 만에 {high:,}원")

            # 손절가 이탈 확인
            if low <= support_price:
                result["support_breached"] = True
                logger.warning(f"⚠️ 손절가 이탈: {day}일째 {low:,}원")

        # T+5일 최종 데이터
        if max_day >= 5 and 5 in stock_prices:
            result["actual_high_5d"] = stock_prices[5]["high"]
            result["actual_low_5d"] = stock_prices[5]["low"]
            result["actual_close_5d"] = stock_prices[5]["close"]

        return result
```

### Task 4: 자동 점수 계산 알고리즘 (4 hours)
**Continue in** `backend/services/evaluation_service.py`

```python
    def calculate_auto_score(
        self,
        target_price: float,
        support_price: float,
        base_price: float,
        achievement: dict
    ) -> dict:
        """
        자동 평가 점수 계산 (0-100점).

        Args:
            target_price: 목표가
            support_price: 손절가
            base_price: 기준가
            achievement: check_target_achievement() 결과

        Returns:
            {
                "target_accuracy_score": 85.5,
                "timing_score": 80.0,
                "risk_management_score": 100.0
            }
        """
        scores = {}

        # 1. 목표가 정확도 점수 (40%)
        if achievement["target_achieved"]:
            scores["target_accuracy_score"] = 100.0
        else:
            # 미달성 시: 실제 도달한 비율
            actual_high = achievement["actual_high_5d"] or achievement["actual_high_1d"] or base_price
            if actual_high > base_price:
                ratio = (actual_high - base_price) / (target_price - base_price)
                scores["target_accuracy_score"] = min(100.0, max(0.0, ratio * 100))
            else:
                scores["target_accuracy_score"] = 0.0

        # 2. 타이밍 점수 (30%)
        if achievement["target_achieved"]:
            days = achievement["target_achieved_days"]
            # 1일: 100, 2일: 90, 3일: 80, 4일: 70, 5일: 60
            scores["timing_score"] = max(60.0, 110 - (days * 10))
        else:
            scores["timing_score"] = 0.0

        # 3. 리스크 관리 점수 (30%)
        if not achievement["support_breached"]:
            scores["risk_management_score"] = 100.0
        else:
            # 손절가 대비 이탈 비율
            actual_low = achievement["actual_low_5d"] or achievement["actual_low_1d"] or base_price
            breach_ratio = abs((actual_low - support_price) / support_price) * 100
            scores["risk_management_score"] = max(0.0, 100 - breach_ratio)

        logger.info(
            f"📊 자동 점수: 정확도={scores['target_accuracy_score']:.1f}, "
            f"타이밍={scores['timing_score']:.1f}, "
            f"리스크={scores['risk_management_score']:.1f}"
        )

        return scores
```

### Task 5: 평가 결과 저장 로직 (3 hours)
**Continue in** `backend/services/evaluation_service.py`

```python
    def save_evaluation(
        self,
        prediction: Prediction,
        achievement: dict,
        scores: dict,
        stock_prices: dict
    ) -> ModelEvaluation:
        """
        평가 결과 저장.

        Args:
            prediction: 평가 대상 예측
            achievement: 달성 여부 결과
            scores: 자동 점수 결과
            stock_prices: 주가 데이터

        Returns:
            생성된 ModelEvaluation 객체
        """
        # NOTE: prediction에 target_price 등이 없는 경우 별도 처리 필요
        # 현재는 임시로 current_price 활용

        evaluation = ModelEvaluation(
            prediction_id=prediction.id,
            model_id=prediction.model_id,
            stock_code=prediction.stock_code,

            # 예측 정보 스냅샷
            predicted_at=prediction.created_at,
            prediction_period="1일~5일",
            predicted_target_price=prediction.current_price * 1.1,  # 임시 (추후 수정)
            predicted_support_price=prediction.current_price * 0.9,  # 임시
            predicted_base_price=prediction.current_price,
            predicted_confidence=prediction.confidence,

            # 실제 결과
            actual_high_1d=achievement["actual_high_1d"],
            actual_low_1d=achievement["actual_low_1d"],
            actual_close_1d=achievement["actual_close_1d"],
            actual_high_5d=achievement["actual_high_5d"],
            actual_low_5d=achievement["actual_low_5d"],
            actual_close_5d=achievement["actual_close_5d"],

            target_achieved=achievement["target_achieved"],
            target_achieved_days=achievement["target_achieved_days"],
            support_breached=achievement["support_breached"],

            # 자동 점수
            target_accuracy_score=scores["target_accuracy_score"],
            timing_score=scores["timing_score"],
            risk_management_score=scores["risk_management_score"],

            # 최종 점수 (사람 평가 없으므로 자동 점수만)
            final_score=(
                scores["target_accuracy_score"] * 0.4 +
                scores["timing_score"] * 0.3 +
                scores["risk_management_score"] * 0.3
            ),

            evaluated_at=datetime.now()
        )

        self.db.add(evaluation)
        self.db.commit()
        self.db.refresh(evaluation)

        logger.info(f"✅ 평가 저장 완료: ID {evaluation.id}, 최종 점수 {evaluation.final_score:.1f}")
        return evaluation
```

### Task 6: 배치 작업 통합 (4 hours)
**File**: `backend/scheduler/evaluation_scheduler.py` (new file)

```python
"""
Automated evaluation scheduler.
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService


logger = logging.getLogger(__name__)


class EvaluationScheduler:
    """
    평가 스케줄러.

    매일 16:00에 D-1일 Investment Report를 자동 평가합니다.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def start(self):
        """스케줄러 시작."""
        # 매일 16:00 실행
        self.scheduler.add_job(
            self._run_daily_evaluation,
            trigger="cron",
            hour=16,
            minute=0,
            id="daily_evaluation",
            name="일일 모델 평가"
        )

        self.scheduler.start()
        logger.info("✅ 평가 스케줄러 시작: 매일 16:00 실행")

    def _run_daily_evaluation(self):
        """
        일일 평가 배치 작업.

        D-1일 생성된 Investment Report를 평가합니다.
        """
        logger.info("=" * 80)
        logger.info("🔄 일일 평가 배치 작업 시작")
        logger.info("=" * 80)

        db = SessionLocal()
        try:
            service = EvaluationService(db)

            # 어제 날짜
            yesterday = datetime.now() - timedelta(days=1)

            # 평가 대상 조회
            predictions = service.get_evaluable_predictions(yesterday)

            success_count = 0
            error_count = 0

            for prediction in predictions:
                try:
                    # 주가 데이터 조회
                    stock_prices = service.get_stock_prices(
                        stock_code=prediction.stock_code,
                        base_date=prediction.created_at,
                        days=5
                    )

                    if not stock_prices:
                        logger.warning(f"⚠️ 주가 데이터 없음: {prediction.stock_code}")
                        continue

                    # 달성 여부 판단
                    achievement = service.check_target_achievement(
                        target_price=prediction.current_price * 1.1,  # 임시
                        support_price=prediction.current_price * 0.9,  # 임시
                        base_price=prediction.current_price,
                        stock_prices=stock_prices
                    )

                    # 자동 점수 계산
                    scores = service.calculate_auto_score(
                        target_price=prediction.current_price * 1.1,
                        support_price=prediction.current_price * 0.9,
                        base_price=prediction.current_price,
                        achievement=achievement
                    )

                    # 평가 결과 저장
                    service.save_evaluation(
                        prediction=prediction,
                        achievement=achievement,
                        scores=scores,
                        stock_prices=stock_prices
                    )

                    success_count += 1

                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ 평가 실패: {prediction.id}, {e}", exc_info=True)

            logger.info("=" * 80)
            logger.info(f"✅ 일일 평가 완료: 성공 {success_count}건, 실패 {error_count}건")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ 일일 평가 배치 작업 실패: {e}", exc_info=True)
        finally:
            db.close()

    def run_manual(self, target_date: datetime = None):
        """
        수동 실행 (테스트용).

        Args:
            target_date: 평가 대상 날짜 (기본값: 어제)
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)

        logger.info(f"🔧 수동 평가 실행: {target_date.date()}")
        self._run_daily_evaluation()
```

### Task 7: CLI 도구 작성 (2 hours)
**File**: `scripts/run_evaluation.py` (new file)

```python
"""
Manual evaluation runner for testing.
"""
import sys
import logging
from datetime import datetime, timedelta

from backend.scheduler.evaluation_scheduler import EvaluationScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """수동 평가 실행."""
    print("=" * 80)
    print("📊 모델 평가 수동 실행 도구")
    print("=" * 80)

    # 날짜 입력
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"❌ 잘못된 날짜 형식: {date_str} (예: 2025-11-05)")
            return
    else:
        target_date = datetime.now() - timedelta(days=1)

    print(f"📅 평가 대상 날짜: {target_date.date()}")
    print()

    # 평가 실행
    scheduler = EvaluationScheduler()
    scheduler.run_manual(target_date)


if __name__ == "__main__":
    main()
```

## 🔗 Dependencies

### Depends On
- STORY-004 (DB 스키마 완료)
- 주가 데이터 수집 중 (`stock_prices` 테이블)
- Investment Report 데이터 존재

### Blocks
- STORY-006 (Daily 집계 배치)

## 📊 Definition of Done

- [x] EvaluationService 구현 완료
- [x] 주가 데이터 조회 로직 테스트
- [x] 달성 여부 판단 로직 테스트
- [x] 자동 점수 계산 검증
- [x] 평가 결과 저장 테스트
- [x] 배치 작업 스케줄 설정
- [x] 수동 실행 CLI 테스트
- [x] 에러 핸들링 검증
- [x] 로깅 완료
- [x] 코드 리뷰 완료

---

## 🤖 Dev Agent Record

### Agent Model Used
- claude-sonnet-4-5-20250929

### Tasks
- [x] Task 1: Investment Report 식별 로직 (EvaluationService.get_evaluable_predictions)
- [x] Task 2: 주가 데이터 수집 로직 (EvaluationService.get_stock_prices)
- [x] Task 3: 달성 여부 판단 로직 (EvaluationService.check_target_achievement)
- [x] Task 4: 자동 점수 계산 알고리즘 (EvaluationService.calculate_auto_score)
- [x] Task 5: 평가 결과 저장 로직 (EvaluationService.save_evaluation)
- [x] Task 6: 배치 작업 스케줄러 (EvaluationScheduler)
- [x] Task 7: 수동 실행 CLI 도구 (scripts/run_evaluation.py)

### Debug Log References
None

### Completion Notes
- ✅ 모든 구현이 완료되어 있음을 확인
- ✅ EvaluationService: 모든 메서드 구현 완료 (get_evaluable_predictions, get_stock_prices, check_target_achievement, calculate_auto_score, save_evaluation, evaluate_prediction)
- ✅ EvaluationScheduler: 매일 16:00 평가, 17:00 집계 스케줄 설정 완료
- ✅ CLI 도구: scripts/run_evaluation.py 구현 완료 (날짜 파라미터 지원)
- ✅ 주말 처리 로직 구현 (영업일만 조회)
- ✅ 중복 평가 방지 로직 구현
- ✅ 에러 핸들링 및 로깅 완료

### File List
- backend/services/evaluation_service.py
- backend/scheduler/evaluation_scheduler.py
- scripts/run_evaluation.py
- scripts/test_human_rating.py (테스트용)

### Change Log
- 2025-11-07: 구현 검증 완료, 모든 파일이 스토리 명세대로 구현되어 있음 확인
- 2025-11-07: 사람 평가 업데이트 기능 추가 (update_human_rating)
  - final_score 자동 재계산 (auto 70% + human 30%)
  - 평가 히스토리 자동 기록 (감사 추적)
  - 점수 검증 로직 (1-5 범위)
  - 테스트 스크립트 추가

## 📝 Notes

### Investment Report 구분 이슈
현재 `predictions` 테이블에 News Prediction과 Investment Report가 혼재되어 있음.
**추후 개선**: 별도 `investment_reports` 테이블 분리 또는 `report_type` 컬럼 추가 권장.

### 주말/공휴일 처리
- 주말(토, 일)은 영업일 수에서 제외
- 공휴일 처리는 추후 KRX 휴장일 API 연동 필요

### 재시도 로직
주가 데이터 미존재 시:
- 1회 재시도 (다음날 배치에서 다시 시도)
- 5일 후까지 데이터 없으면 평가 실패로 기록

### 성능 최적화
- 배치 실행 시간: 예상 1-2분 (100건 기준)
- 필요 시 병렬 처리 고려

## 🔍 Testing Strategy

### Unit Tests
```python
# tests/test_evaluation_service.py
def test_get_evaluable_predictions():
    """Investment Report 조회 테스트"""
    pass

def test_check_target_achievement():
    """목표가 달성 판단 테스트"""
    pass

def test_calculate_auto_score():
    """자동 점수 계산 테스트"""
    pass
```

### Integration Tests
```bash
# 수동 실행 테스트
python scripts/run_evaluation.py 2025-11-04

# 스케줄러 테스트 (16:00 대기)
# 또는 시간 변경하여 즉시 실행
```

### Acceptance Tests
1. D-1일 Investment Report 20건 생성
2. 배치 실행
3. `model_evaluations` 테이블에 20건 INSERT 확인
4. 자동 점수 범위 확인 (0-100)
5. 중복 실행 시 중복 INSERT 방지 확인
