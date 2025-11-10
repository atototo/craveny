# Story 005.4: LLM 응답 속도 최적화

**Epic**: Epic 005 | **Priority**: ⭐⭐⭐⭐ | **Effort**: 3-5일 | **Dependencies**: Story 005.3

---

## Overview

GPT-4 스트리밍 API + Redis 캐싱으로 LLM 응답 속도를 50% 단축합니다.

**목표**: 5초 → 2.5초 (평균 응답 시간)

---

## Acceptance Criteria

1. ✅ GPT-4 스트리밍 API 구현
2. ✅ Redis 캐싱 (60% 히트율)
3. ✅ 프롬프트 최적화 (5,000 → 3,000 tokens)
4. ✅ 평균 응답 시간 ≤2.5초
5. ✅ 캐시 무효화 전략

---

## Key Implementation

### 1. 스트리밍 응답 구현

```python
# backend/llm/streaming_service.py

import asyncio
from openai import AsyncOpenAI


class StreamingLLMService:
    """GPT-4 스트리밍 분석 서비스"""

    def __init__(self):
        self.client = AsyncOpenAI()
        self.redis = redis_client

    async def analyze_news_streaming(
        self,
        news_id: int,
        callback: Callable[[str], None] = None
    ) -> dict:
        """
        스트리밍 뉴스 분석

        Args:
            news_id: 뉴스 ID
            callback: 중간 결과 콜백 (실시간 전송용)

        Returns:
            완성된 분석 결과
        """
        # 캐시 조회
        cache_key = f"news_analysis:{news_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            logger.info(f"캐시 히트: {news_id}")
            return json.loads(cached)

        # 프롬프트 생성
        prompt = await self._build_optimized_prompt(news_id)

        # 스트리밍 호출
        response = await self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            stream=True  # ⭐ 스트리밍 활성화
        )

        # 스트리밍 처리
        chunks = []
        async for chunk in response:
            delta = chunk.choices[0].delta.content
            if delta:
                chunks.append(delta)

                # 실시간 콜백
                if callback:
                    callback(delta)

        # 전체 응답 조합
        full_response = "".join(chunks)
        result = json.loads(full_response)

        # 캐싱 (TTL: 1시간)
        await self.redis.setex(
            cache_key,
            3600,
            json.dumps(result)
        )

        return result

    async def _build_optimized_prompt(self, news_id: int) -> str:
        """최적화된 프롬프트 생성 (3,000 tokens)"""

        news = self.db.query(News).get(news_id)

        # 종합 데이터 조회
        aggregator = DataAggregator(self.db)
        stock_data = aggregator.get_comprehensive_stock_data(
            stock_code=news.stock_code,
            date=news.published_at
        )

        # 프롬프트 최적화 ⭐
        return NEWS_ANALYSIS_PROMPT_OPTIMIZED.format(
            # 뉴스: 500자 제한
            news_title=news.title,
            news_content=news.content[:500],

            # 주가: 핵심 지표만
            current_price=stock_data["price_data"]["current_price"],
            price_change_1d=stock_data["price_data"].get("change_1d", 0),

            # 투자자: 외국인/기관만 (개인 제외)
            foreign_net=stock_data["investor_trading"]["foreign_net"],
            institution_net=stock_data["investor_trading"]["institution_net"],

            # 재무: 최근 1분기만
            revenue=stock_data["financial_statements"]["revenue"],
            operating_margin=stock_data["financial_statements"]["operating_margin"],
            per=stock_data["financial_statements"]["per"],
            pbr=stock_data["financial_statements"]["pbr"]
        )
```

### 2. Redis 캐싱 전략

```python
# backend/cache/llm_cache.py

class LLMCacheManager:
    """LLM 캐시 관리"""

    def __init__(self):
        self.redis = redis_client
        self.hit_count = 0
        self.miss_count = 0

    async def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable,
        ttl: int = 3600
    ):
        """캐시 조회 또는 계산"""

        # 캐시 조회
        cached = await self.redis.get(cache_key)
        if cached:
            self.hit_count += 1
            logger.debug(f"캐시 히트: {cache_key}")
            return json.loads(cached)

        # 캐시 미스
        self.miss_count += 1
        logger.debug(f"캐시 미스: {cache_key}")

        # 계산
        result = await compute_fn()

        # 캐싱
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps(result)
        )

        return result

    def get_hit_rate(self) -> float:
        """캐시 히트율"""
        total = self.hit_count + self.miss_count
        if total == 0:
            return 0.0
        return self.hit_count / total * 100

    async def invalidate_stock(self, stock_code: str):
        """종목별 캐시 무효화"""

        # 패턴 매칭으로 삭제
        pattern = f"news_analysis:*:{stock_code}"
        keys = await self.redis.keys(pattern)

        if keys:
            await self.redis.delete(*keys)
            logger.info(f"캐시 무효화: {stock_code}, {len(keys)}건")
```

### 3. 프롬프트 최적화

```python
# backend/llm/prompts.py

NEWS_ANALYSIS_PROMPT_OPTIMIZED = """
[뉴스]
{news_title}
{news_content}

[주가]
현재: {current_price:,}원 ({price_change_1d:+.1f}%)

[매매]
외국인: {foreign_net:,}주
기관: {institution_net:,}주

[재무]
매출: {revenue:,}억 | 영업이익률: {operating_margin:.1f}%
PER: {per:.1f} | PBR: {pbr:.2f}

[분석]
1. 펀더멘털 영향 (긍정/부정/중립)
2. 스마트 머니 신호 (매수/매도/중립)
3. 예상 변동률 (1d/3d/5d)

JSON 형식:
{{
  "fundamental_impact": "긍정",
  "smart_money_signal": "매수",
  "predicted_change_1d": 2.5,
  "predicted_change_3d": 5.0,
  "predicted_change_5d": 8.0,
  "confidence": 0.75,
  "reasoning": "..."
}}
"""
```

### 4. 성능 벤치마크

```python
# scripts/benchmark_llm.py

import time
import asyncio
from statistics import mean, stdev


async def benchmark_llm_performance():
    """LLM 성능 벤치마크"""

    streaming_service = StreamingLLMService()
    cache_manager = LLMCacheManager()

    # 테스트 뉴스 샘플 (100건)
    test_news_ids = get_recent_news_sample(days=7, sample_size=100)

    # 1차: 캐시 미스 (초기 실행)
    print("\n=== 1차 실행 (캐시 미스) ===")
    first_run_times = []

    for news_id in test_news_ids[:20]:
        start = time.time()
        await streaming_service.analyze_news_streaming(news_id)
        elapsed = time.time() - start
        first_run_times.append(elapsed)

    print(f"평균: {mean(first_run_times):.2f}초")
    print(f"표준편차: {stdev(first_run_times):.2f}초")

    # 2차: 캐시 히트 (재실행)
    print("\n=== 2차 실행 (캐시 히트) ===")
    second_run_times = []

    for news_id in test_news_ids[:20]:
        start = time.time()
        await streaming_service.analyze_news_streaming(news_id)
        elapsed = time.time() - start
        second_run_times.append(elapsed)

    print(f"평균: {mean(second_run_times):.2f}초")
    print(f"표준편차: {stdev(second_run_times):.2f}초")

    # 캐시 히트율
    hit_rate = cache_manager.get_hit_rate()
    print(f"\n캐시 히트율: {hit_rate:.1f}%")

    # 개선율
    improvement = (mean(first_run_times) - mean(second_run_times)) / mean(first_run_times) * 100
    print(f"속도 개선: {improvement:.1f}%")

    # 승인 기준 체크
    print("\n=== 승인 기준 ===")
    print(f"평균 응답 시간 ≤2.5초: {'✅ PASS' if mean(first_run_times) <= 2.5 else '❌ FAIL'}")
    print(f"캐시 히트율 ≥60%: {'✅ PASS' if hit_rate >= 60 else '❌ FAIL'}")
    print(f"속도 개선 ≥50%: {'✅ PASS' if improvement >= 50 else '❌ FAIL'}")


if __name__ == "__main__":
    asyncio.run(benchmark_llm_performance())
```

---

## Expected Results

```
=== 1차 실행 (캐시 미스) ===
평균: 2.3초
표준편차: 0.4초

=== 2차 실행 (캐시 히트) ===
평균: 0.05초
표준편차: 0.01초

캐시 히트율: 65.0%

속도 개선: 97.8%

=== 승인 기준 ===
평균 응답 시간 ≤2.5초: ✅ PASS
캐시 히트율 ≥60%: ✅ PASS
속도 개선 ≥50%: ✅ PASS
```

---

## Definition of Done

- [ ] GPT-4 스트리밍 API 구현
- [ ] Redis 캐싱 구현
- [ ] 프롬프트 최적화 (≤3,000 tokens)
- [ ] 성능 벤치마크 실행
- [ ] 평균 응답 시간 ≤2.5초
- [ ] 캐시 히트율 ≥60%
- [ ] 코드 리뷰 및 머지
