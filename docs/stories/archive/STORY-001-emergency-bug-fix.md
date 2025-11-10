---
story_id: STORY-001
epic_id: EPIC-001
title: 긴급 버그 수정 - 업데이트 스킵 로직 제거
status: ready
priority: critical
assignee: Backend Developer
created: 2025-11-04
estimated: 4 hours
---

# Story: 긴급 버그 수정 - 업데이트 스킵 로직 제거

## 🎯 User Story

**As a** 투자자
**I want** 종합 리포트가 새 뉴스 추가 시 즉시 업데이트되도록
**So that** 최신 AI 예측 기반으로 투자 의사결정을 할 수 있다

## 📊 Current State

### 버그 위치
`backend/services/stock_analysis_service.py:88-97`

### 버그 코드
```python
# 4. 업데이트 필요 여부 확인
if not force_update and existing_summary:
    # 최신 예측과 비교
    latest_prediction_count = len(predictions)  # ← 항상 20 (limit(20))
    if existing_summary.based_on_prediction_count >= latest_prediction_count:
        logger.info(f"종목 {stock_code}의 분석 요약이 최신 상태입니다.")
        return existing_summary  # ← 여기서 스킵 (버그)
```

### 문제점
1. `predictions` 쿼리에 `limit(20)` 하드코딩
2. 총 72개 예측 있어도 20개만 조회
3. `20 >= 20` 조건 → 항상 참 → 항상 스킵
4. 24시간 경과해도 업데이트 안 됨

### 실제 피해 사례
**SK하이닉스 (034730)**:
- 마지막 업데이트: 2025-11-03 15:09:02
- 경과 시간: 21시간+
- 리포트 통계: 상승 11, 하락 1, 보합 8 (매수 추천)
- 실제 최신 20건: 상승 5, 하락 1, 보합 14 (중립)

## ✅ Acceptance Criteria

### AC1: 총 예측 개수 정확히 조회
- [ ] `limit(20)` 없이 총 예측 개수 조회
- [ ] `func.count(Prediction.id)` 사용
- [ ] 로그에 정확한 예측 개수 출력

### AC2: 24시간 TTL 추가
- [ ] `last_updated` 타임스탬프 기반 경과 시간 계산
- [ ] 24시간 이상 경과 시 업데이트
- [ ] 로그에 경과 시간 출력

### AC3: SK하이닉스 리포트 즉시 재생성
- [ ] `--force` 플래그로 강제 업데이트
- [ ] 최신 예측 20건 기반 리포트 생성
- [ ] 추천: "매수 추천" → "중립 관망" 변경 확인

### AC4: 단위 테스트 통과
- [ ] 새 예측 추가 시 업데이트 테스트
- [ ] 24시간 경과 시 업데이트 테스트
- [ ] 예측 개수 변화 없고 24시간 미만 시 스킵 테스트

## 📝 Tasks

### Task 1.1: 버그 수정 코드 구현
**파일**: `backend/services/stock_analysis_service.py`
**예상 시간**: 1시간

```python
from sqlalchemy import func

# 4. 업데이트 필요 여부 확인
if not force_update and existing_summary:
    # 총 예측 개수 조회 (limit 없이)
    total_prediction_count = (
        db.query(func.count(Prediction.id))
        .filter(Prediction.stock_code == stock_code)
        .scalar()
    )

    # 예측 개수 증가 또는 24시간 경과 시 업데이트
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

**체크리스트**:
- [ ] `sqlalchemy.func` import 추가
- [ ] `total_prediction_count` 쿼리 구현
- [ ] `staleness_hours` 계산 로직 추가
- [ ] 업데이트 조건 수정
- [ ] 로깅 메시지 개선

---

### Task 1.2: SK하이닉스 리포트 재생성
**명령어**:
```bash
uv run python scripts/update_all_stock_analysis.py --force --stocks 034730
```

**예상 시간**: 10분

**검증**:
- [ ] 리포트 `last_updated` 타임스탬프 업데이트
- [ ] 통계: 상승 5, 하락 1, 보합 14 반영
- [ ] 추천: "중립 관망" 또는 "긍정적 관망"

---

### Task 1.3: 단위 테스트 작성
**파일**: `tests/services/test_stock_analysis_service.py` (신규)
**예상 시간**: 2시간

```python
import pytest
from datetime import datetime, timedelta
from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.prediction import Prediction


@pytest.mark.asyncio
async def test_update_on_new_predictions(db_session, sample_stock_code):
    """새 예측 추가 시 리포트 업데이트 확인"""
    # Given: 20개 예측 기반 리포트 생성
    create_predictions(db_session, sample_stock_code, count=20)
    summary1 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=True)
    assert summary1.based_on_prediction_count == 20

    # When: 새 예측 5개 추가
    create_predictions(db_session, sample_stock_code, count=5)

    # Then: 리포트 자동 업데이트
    summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)
    assert summary2.based_on_prediction_count == 25
    assert summary2.last_updated > summary1.last_updated


@pytest.mark.asyncio
async def test_update_on_24h_staleness(db_session, sample_stock_code):
    """24시간 경과 시 리포트 업데이트 확인"""
    # Given: 25시간 전 리포트 생성
    old_time = datetime.now() - timedelta(hours=25)
    summary1 = StockAnalysisSummary(
        stock_code=sample_stock_code,
        last_updated=old_time,
        based_on_prediction_count=20
    )
    db_session.add(summary1)
    db_session.commit()

    # When: 리포트 업데이트 시도
    summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

    # Then: 리포트 자동 업데이트
    assert summary2.last_updated > old_time


@pytest.mark.asyncio
async def test_no_update_when_fresh(db_session, sample_stock_code):
    """예측 변화 없고 24시간 미만 시 업데이트 안 함"""
    # Given: 2시간 전 리포트 생성 (20개 예측)
    create_predictions(db_session, sample_stock_code, count=20)
    summary1 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=True)

    # When: 리포트 업데이트 시도 (예측 변화 없음)
    summary2 = await update_stock_analysis_summary(sample_stock_code, db_session, force_update=False)

    # Then: 업데이트 스킵 (기존 리포트 반환)
    assert summary2.id == summary1.id
    assert summary2.last_updated == summary1.last_updated
```

**체크리스트**:
- [ ] `pytest-asyncio` 의존성 확인
- [ ] Fixture 함수 작성 (`db_session`, `sample_stock_code`, `create_predictions`)
- [ ] 3개 테스트 케이스 작성
- [ ] `pytest tests/services/test_stock_analysis_service.py` 통과

---

### Task 1.4: 프로덕션 배포 및 검증
**예상 시간**: 1시간

**배포 절차**:
1. [ ] Git commit: "fix: 종합 리포트 업데이트 스킵 버그 수정"
2. [ ] Pull Request 생성 및 코드 리뷰
3. [ ] 프로덕션 배포
4. [ ] SK하이닉스 리포트 수동 재생성

**검증 시나리오**:
1. [ ] 새 뉴스 크롤링 → 예측 생성 → 리포트 자동 업데이트 확인
2. [ ] 24시간 후 자동 갱신 확인 (스케줄러 또는 API 조회)
3. [ ] 로그 확인: "업데이트 필요: 예측 개수 변화..." 또는 "24시간 경과..."

---

## 📋 Definition of Done

- [x] 버그 수정 코드 구현 및 커밋
- [x] SK하이닉스 리포트 최신화 확인
- [x] 단위 테스트 3개 통과
- [x] 프로덕션 배포 완료
- [x] 새 뉴스 추가 시 자동 업데이트 검증
- [x] 24시간 후 자동 갱신 검증

## 🔗 Dependencies

**Blocks**:
- STORY-002 (시장 시간 기반 시스템)

**References**:
- `docs/STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md` (분석 리포트)
- EPIC-001 (부모 Epic)

---

**Last Updated**: 2025-11-04
**Status**: Ready for Development
