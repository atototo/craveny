---
story_id: STORY-003
epic_id: EPIC-001
title: 모니터링 및 프로덕션 검증
status: blocked
priority: medium
assignee: Backend Developer
created: 2025-11-04
estimated: 0.5 days
blocked_by: STORY-002
---

# Story: 모니터링 및 프로덕션 검증

## 🎯 User Story

**As a** 시스템 관리자
**I want** 리포트 업데이트 통계와 LLM 비용을 실시간 모니터링할 수 있도록
**So that** 시스템이 의도대로 동작하는지 확인하고 비용을 추적할 수 있다

## 📊 Background

### 모니터링 목표
1. **업데이트 빈도 추적**: 시간대별, 사유별 업데이트 횟수
2. **LLM 비용 모니터링**: 일일 API 호출 횟수 및 비용
3. **성능 지표 측정**: 리포트 신선도, 업데이트 성공률
4. **이상 감지**: 과도한 업데이트, 업데이트 실패 급증

## ✅ Acceptance Criteria

### AC1: 업데이트 통계 API
- [ ] 업데이트 사유별 빈도 집계
- [ ] 시장 단계별 업데이트 횟수
- [ ] 평균 업데이트 간격
- [ ] 최근 7일/30일 통계 조회 가능

### AC2: LLM 비용 추적
- [ ] 일일 LLM API 호출 횟수 로깅
- [ ] 종목별 평균 업데이트 빈도
- [ ] 비용 예상치 계산 ($0.001/호출 기준)

### AC3: 대시보드 UI (선택)
- [ ] 업데이트 사유 파이 차트
- [ ] 시간대별 업데이트 히트맵
- [ ] 일일 LLM 비용 추이 그래프

## 📝 Tasks

### Task 3.1: 업데이트 통계 API 구현
**파일**: `backend/api/admin.py` (수정 또는 신규)
**예상 시간**: 2시간

```python
@router.get("/admin/report-updates/stats")
async def get_report_update_stats(
    days: int = Query(7, ge=1, le=30, description="조회 기간 (일)"),
    db: Session = Depends(get_db)
):
    """
    리포트 업데이트 통계 조회

    Returns:
        - update_reasons: 업데이트 사유별 빈도
        - market_phases: 시장 단계별 업데이트 횟수
        - avg_interval: 평균 업데이트 간격 (시간)
        - total_updates: 총 업데이트 횟수
    """
    # StockAnalysisSummary 테이블에서 통계 집계
    # (Task 3.2에서 last_update_reason 필드 추가 필요)

    cutoff_date = datetime.now() - timedelta(days=days)

    # 업데이트 사유별 집계
    update_reasons = db.query(
        StockAnalysisSummary.last_update_reason,
        func.count(StockAnalysisSummary.id).label("count")
    ).filter(
        StockAnalysisSummary.last_updated >= cutoff_date
    ).group_by(StockAnalysisSummary.last_update_reason).all()

    # 시장 단계 추출 및 집계
    # ...

    return {
        "period_days": days,
        "update_reasons": [
            {"reason": reason, "count": count}
            for reason, count in update_reasons
        ],
        "market_phases": {...},
        "avg_interval_hours": {...},
        "total_updates": sum(count for _, count in update_reasons)
    }
```

**체크리스트**:
- [ ] `/admin/report-updates/stats` 엔드포인트 구현
- [ ] 업데이트 사유별 집계 쿼리
- [ ] 시장 단계별 집계 로직
- [ ] API 문서화 (FastAPI 자동 문서)

---

### Task 3.2: DB 스키마 확장 (선택)
**파일**: `backend/db/models/stock_analysis.py` (수정)
**예상 시간**: 1시간

```python
class StockAnalysisSummary(Base):
    __tablename__ = "stock_analysis_summaries"

    # ... 기존 필드 ...

    # 업데이트 트리거 추적용 필드 추가
    last_update_reason = Column(String(200), nullable=True)  # "새 예측 추가", "시장 단계별 TTL 초과", etc.
    last_market_phase = Column(String(20), nullable=True)   # "trading", "pre_market", etc.
```

**마이그레이션**:
```bash
# scripts/migrate_add_update_tracking.py
uv run python scripts/migrate_add_update_tracking.py
```

**수정 코드** (`stock_analysis_service.py`):
```python
# 리포트 업데이트 시
if settings.AB_TEST_ENABLED:
    existing_summary.last_update_reason = reason
    existing_summary.last_market_phase = get_market_phase()
    # ...
```

**체크리스트**:
- [ ] `last_update_reason`, `last_market_phase` 필드 추가
- [ ] 마이그레이션 스크립트 작성
- [ ] `update_stock_analysis_summary()` 함수 수정
- [ ] 프로덕션 DB 마이그레이션 실행

---

### Task 3.3: LLM 비용 로깅
**파일**: `backend/services/stock_analysis_service.py` (수정)
**예상 시간**: 30분

```python
# 리포트 생성 시 로깅 추가
logger.info(
    f"[LLM_COST] 리포트 생성: "
    f"종목={stock_code}, "
    f"시장단계={market_phase}, "
    f"사유={reason}, "
    f"예측개수={len(predictions)}, "
    f"비용예상=$0.001"
)
```

**로그 집계 스크립트** (선택):
```bash
# scripts/analyze_llm_costs.sh
grep "LLM_COST" /var/log/craveny/backend.log | \
  awk '{print $3}' | \
  sort | uniq -c
```

**체크리스트**:
- [ ] `[LLM_COST]` 태그로 로깅 추가
- [ ] 로그에 종목, 시장단계, 사유, 비용 포함
- [ ] 로그 집계 방법 문서화

---

### Task 3.4: 프로덕션 검증
**예상 시간**: 1시간

**검증 체크리스트**:

**Day 1 검증** (STORY-002 배포 직후):
- [ ] 장 시작 전 (08:30) - 새 뉴스 → 리포트 업데이트 확인
- [ ] 장 시작 (09:15) - 리포트 1시간 이내 업데이트 확인
- [ ] 정규 장중 (11:00) - 주가 3% 변동 → 리포트 업데이트 확인
- [ ] 정규 장중 (13:00) - 2시간 경과 → 자동 업데이트 확인
- [ ] 장 마감 후 (18:00) - 6시간 이내 업데이트 안 함 확인

**Day 2-7 검증**:
- [ ] 일일 업데이트 횟수: 5-10회 (예상 범위)
- [ ] 업데이트 성공률: > 95%
- [ ] LLM API 호출 횟수: 50-100회/일 (종목 10개 기준)
- [ ] 리포트 신선도: 평균 < 3시간

**로그 확인**:
```bash
# 업데이트 사유 통계
grep "업데이트 시작" /var/log/craveny/backend.log | \
  grep -oP '사유=\K[^,]+' | \
  sort | uniq -c | sort -rn

# 시장 단계별 업데이트 횟수
grep "LLM_COST" /var/log/craveny/backend.log | \
  grep -oP '시장단계=\K[^,]+' | \
  sort | uniq -c
```

---

## 📋 Definition of Done

- [x] 업데이트 통계 API 구현 완료
- [x] (선택) DB 스키마 확장 및 마이그레이션
- [x] LLM 비용 로깅 추가
- [x] Day 1 검증 완료 (5가지 시나리오)
- [x] Day 2-7 검증 완료 (4가지 지표)
- [x] 로그 분석 및 문서화

## 🔗 Dependencies

**Depends On**:
- STORY-002 (시장 시간 기반 시스템) - MUST complete first

**References**:
- `docs/STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md`
- EPIC-001

---

**Last Updated**: 2025-11-04
**Status**: Blocked (Waiting for STORY-002)
