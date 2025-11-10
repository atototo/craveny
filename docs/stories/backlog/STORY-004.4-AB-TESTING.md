# Story 004.4: A/B 테스트 및 정확도 검증

**Epic**: Epic 004 | **Priority**: ⭐⭐⭐⭐ | **Effort**: 5-7일 | **Dependencies**: Story 004.3

---

## 📋 Overview

기존 시스템(뉴스+주가) vs 신규 시스템(뉴스+주가+투자자+재무)를 A/B 테스트하여 예측 정확도 개선 효과를 정량적으로 검증합니다.

**목표**: 방향 정확도 +15%p 이상, MAE -20% 이상

---

## 🎯 Acceptance Criteria

1. ✅ A/B 테스트 프레임워크 설계
2. ✅ 200건 뉴스 샘플 준비
3. ✅ 그룹 A/B 분석 실행
4. ✅ 통계적 유의성 검정 (p < 0.05)
5. ✅ 결과 리포트 작성
6. ✅ 방향 정확도 +15%p, MAE -20% 달성

---

## 🔧 Implementation

### A/B 테스트 서비스

```python
# backend/services/ab_test_service.py

class ABTestService:
    async def run_ab_test(
        self,
        news_ids: List[int],
        split: str = "50-50"
    ) -> dict:
        """
        A/B 테스트 실행

        Args:
            news_ids: 테스트할 뉴스 ID 리스트
            split: 분할 비율 (기본: 50-50)

        Returns:
            {
                "group_a": [...],  # 기존 시스템
                "group_b": [...],  # 신규 시스템
                "metrics": {...}
            }
        """
        # 그룹 분할
        group_a_ids, group_b_ids = self._split_groups(news_ids, split)

        results = {
            "group_a": [],
            "group_b": []
        }

        # 그룹 A: 기존 프롬프트 (뉴스 + 주가만)
        for news_id in group_a_ids:
            result = await self._analyze_basic(news_id)
            results["group_a"].append(result)

        # 그룹 B: 신규 프롬프트 (뉴스 + 주가 + 투자자 + 재무)
        for news_id in group_b_ids:
            result = await self._analyze_enhanced(news_id)
            results["group_b"].append(result)

        # 실제 변동률 수집 (T+5일 후)
        await self._collect_actual_changes(news_ids)

        # 메트릭 계산
        metrics = self._calculate_metrics(results)

        return {
            **results,
            "metrics": metrics
        }

    def _calculate_metrics(self, results: dict) -> dict:
        """정확도 메트릭 계산"""

        metrics_a = self._calculate_group_metrics(results["group_a"])
        metrics_b = self._calculate_group_metrics(results["group_b"])

        # 통계적 유의성 검정
        from scipy.stats import ttest_ind

        t_stat, p_value = ttest_ind(
            [r["direction_correct"] for r in results["group_a"]],
            [r["direction_correct"] for r in results["group_b"]]
        )

        return {
            "group_a": metrics_a,
            "group_b": metrics_b,
            "improvement": {
                "direction_accuracy": metrics_b["direction_accuracy"] - metrics_a["direction_accuracy"],
                "mae": ((metrics_a["mae"] - metrics_b["mae"]) / metrics_a["mae"] * 100)  # % 감소
            },
            "statistical_significance": {
                "t_statistic": t_stat,
                "p_value": p_value,
                "is_significant": p_value < 0.05
            }
        }

    def _calculate_group_metrics(self, group_results: List[dict]) -> dict:
        """그룹별 메트릭"""
        direction_correct = sum(1 for r in group_results if r["direction_correct"])
        mae = sum(r["mae"] for r in group_results) / len(group_results)

        return {
            "sample_size": len(group_results),
            "direction_accuracy": direction_correct / len(group_results) * 100,
            "mae": mae,
            "hit_rate": sum(1 for r in group_results if r["within_ci"]) / len(group_results) * 100
        }
```

### 테스트 실행 스크립트

```python
# scripts/run_ab_test.py

async def main():
    # 최근 200건 뉴스 샘플링
    news_ids = get_recent_news_sample(days=30, sample_size=200)

    logger.info(f"A/B 테스트 시작: {len(news_ids)}건")

    # A/B 테스트 실행
    ab_service = ABTestService()
    results = await ab_service.run_ab_test(news_ids)

    # 결과 출력
    print("\n" + "="*80)
    print("A/B 테스트 결과")
    print("="*80)

    metrics = results["metrics"]

    print(f"\n그룹 A (기존 시스템):")
    print(f"  - 방향 정확도: {metrics['group_a']['direction_accuracy']:.2f}%")
    print(f"  - MAE: {metrics['group_a']['mae']:.2f}%")

    print(f"\n그룹 B (신규 시스템):")
    print(f"  - 방향 정확도: {metrics['group_b']['direction_accuracy']:.2f}%")
    print(f"  - MAE: {metrics['group_b']['mae']:.2f}%")

    print(f"\n개선 효과:")
    print(f"  - 방향 정확도: +{metrics['improvement']['direction_accuracy']:.2f}%p")
    print(f"  - MAE: -{metrics['improvement']['mae']:.2f}%")

    print(f"\n통계적 유의성:")
    print(f"  - p-value: {metrics['statistical_significance']['p_value']:.4f}")
    print(f"  - 유의함: {'✅ YES' if metrics['statistical_significance']['is_significant'] else '❌ NO'}")

    # 리포트 저장
    save_ab_test_report(results)

    # 승인 기준 체크
    criteria = {
        "방향 정확도 +15%p": metrics['improvement']['direction_accuracy'] >= 15,
        "MAE -20%": metrics['improvement']['mae'] >= 20,
        "p < 0.05": metrics['statistical_significance']['is_significant']
    }

    print("\n승인 기준:")
    for criterion, passed in criteria.items():
        print(f"  - {criterion}: {'✅ PASS' if passed else '❌ FAIL'}")

    if all(criteria.values()):
        print("\n🎉 모든 기준 통과! 신규 시스템 배포 승인.")
    else:
        print("\n⚠️  일부 기준 미달. 추가 개선 필요.")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📊 Expected Results

```
A/B 테스트 결과
================================================================================

그룹 A (기존 시스템):
  - 방향 정확도: 65.0%
  - MAE: 3.2%

그룹 B (신규 시스템):
  - 방향 정확도: 82.0%
  - MAE: 2.1%

개선 효과:
  - 방향 정확도: +17.0%p
  - MAE: -34.4%

통계적 유의성:
  - p-value: 0.0028
  - 유의함: ✅ YES

승인 기준:
  - 방향 정확도 +15%p: ✅ PASS
  - MAE -20%: ✅ PASS
  - p < 0.05: ✅ PASS

🎉 모든 기준 통과! 신규 시스템 배포 승인.
```

---

## ✅ Definition of Done

- [ ] ABTestService 구현
- [ ] 200건 뉴스 샘플 준비
- [ ] A/B 테스트 실행
- [ ] 결과 리포트 작성 (`docs/reports/ab_test_results.md`)
- [ ] 방향 정확도 +15%p 달성
- [ ] MAE -20% 달성
- [ ] p < 0.05 확인
- [ ] 코드 리뷰 및 머지
