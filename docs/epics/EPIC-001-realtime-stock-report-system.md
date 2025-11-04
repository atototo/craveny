---
epic_id: EPIC-001
title: 실시간 종합 투자 리포트 시스템
status: in_progress
priority: high
created: 2025-11-04
analyst: Mary (Business Analyst)
estimated_duration: 3-4 days
---

# Epic: 실시간 종합 투자 리포트 시스템

## 📊 Business Context

### 현재 문제
- SK하이닉스 종합 리포트가 **21시간 이상 업데이트되지 않음**
- 실제 최신 예측과 리포트 내용 불일치
  - 실제: 상승 5, 하락 1, 보합 14 (중립 성향)
  - 리포트: "매수 추천" (상승 11, 하락 1, 보합 8 기반)
- 장중 주가 급변 시 리포트 미반영 → 사용자 신뢰도 하락

### Business Impact
- **사용자 신뢰도**: 매우 낮음 (잘못된 투자 추천)
- **투자 의사결정 정확도**: 낮음 (오래된 데이터 기반)
- **경쟁력**: 실시간 정보 제공 부족
- **리스크**: 사용자 손실 발생 가능

### 목표
**장중 실시간 종합 투자 리포트 업데이트 시스템 구축**
- 리포트 신선도: 21시간+ → **1-2시간 이내**
- 시장 시간 기반 동적 업데이트
- 주가/예측 변화 즉시 반영

## 🎯 Success Metrics

| Metric | Current | Target | Measure |
|--------|---------|--------|---------|
| 리포트 신선도 | 21시간+ | < 2시간 | `last_updated` 타임스탬프 |
| 업데이트 성공률 | 10% | > 95% | 업데이트 시도/성공 비율 |
| 장중 정확도 | 낮음 | 높음 | 리포트 vs 실제 예측 일치율 |
| 사용자 신뢰도 | 낮음 | 높음 | 사용자 피드백 |

## 📋 Stories

1. **[STORY-001] 긴급 버그 수정: 업데이트 스킵 로직 제거** (Priority: Critical)
2. **[STORY-002] 시장 시간 기반 동적 업데이트 시스템** (Priority: High)
3. **[STORY-003] 모니터링 및 프로덕션 검증** (Priority: Medium)

## 📈 Timeline

```
Day 1:     STORY-001 (긴급 버그 수정)
Day 2-3:   STORY-002 (시장 시간 기반 시스템)
Day 4:     STORY-003 (모니터링 및 검증)
```

## 💰 Cost Analysis

### LLM API 비용
- **현재**: $0.01/종목/일 (1회 업데이트)
- **개선 후**: $0.08/종목/일 (평균 8회 업데이트)
- **증가폭**: +$0.07/종목/일 (+700%)
- **ROI**: 장중 실시간 정확도로 사용자 이탈 방지

### 월간 비용 (종목 10개 기준)
- 현재: $3/월
- 개선 후: $24/월
- 추가 비용: $21/월

## 🚨 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM 비용 급증 | Medium | Medium | 시간대별 TTL 제어, 모니터링 |
| 리포트 생성 실패 증가 | Low | High | Fallback 로직, 재시도 3회 |
| 시간대 오판 | Low | Low | 단위 테스트, KST 타임존 명시 |

## 📚 References

- **분석 리포트**: `docs/STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md`
- **기존 코드**: `backend/services/stock_analysis_service.py`
- **DB 모델**: `backend/db/models/stock_analysis.py`

---

**Last Updated**: 2025-11-04
**Next Review**: STORY-001 완료 후
