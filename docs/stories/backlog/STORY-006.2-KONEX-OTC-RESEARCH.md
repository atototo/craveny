# Story 006.2: KONEX/OTC/프리마켓 데이터 수집 조사

**Epic**: Epic 006 | **Priority**: ⭐⭐ | **Effort**: 3-4일 | **Dependencies**: Story 006.1

---

## Overview

KOSPI/KOSDAQ 외 추가 시장(KONEX, OTC, 프리마켓)의 데이터 수집 가능성을 조사합니다.

**목표**: 기술적 실현 가능성 평가 + 비용/효과 분석

---

## Acceptance Criteria

1. ✅ KIS API 지원 시장 조사
2. ✅ KONEX 데이터 샘플 수집
3. ✅ OTC/프리마켓 데이터 가능성 평가
4. ✅ 비용/효과 분석
5. ✅ 구현 권고사항 문서화

---

## Research Scope

### 1. KONEX (코넥스 시장)

**개요**:
- 중소·벤처기업 전용 시장
- 종목 수: ~150개
- 거래 시간: 9:00~15:30 (KOSDAQ 동일)

**조사 항목**:
```python
# scripts/research_konex.py

async def research_konex_data():
    """KONEX 데이터 조사"""

    kis_client = KISClient()

    # 1. KONEX 종목 리스트 조회 가능 여부
    try:
        konex_stocks = await kis_client.get_stock_list(market="KONEX")
        print(f"✅ KONEX 종목 수: {len(konex_stocks)}개")

        # 샘플 종목 (상위 5개)
        sample_stocks = konex_stocks[:5]

        for stock in sample_stocks:
            print(f"  - {stock['code']}: {stock['name']}")

    except Exception as e:
        print(f"❌ KONEX 종목 리스트 조회 실패: {e}")
        return

    # 2. 일봉 데이터 조회 가능 여부
    sample_code = konex_stocks[0]["code"]
    try:
        df = await kis_client.get_daily_prices(
            stock_code=sample_code,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )

        print(f"\n✅ KONEX 일봉 데이터 수집 가능")
        print(f"  - 종목: {sample_code}")
        print(f"  - 데이터: {len(df)}건")
        print(df.head())

    except Exception as e:
        print(f"❌ KONEX 일봉 데이터 조회 실패: {e}")

    # 3. 분봉 데이터 조회 가능 여부
    try:
        df_min = await kis_client.get_minute_prices(
            stock_code=sample_code,
            date=datetime.now()
        )

        print(f"\n✅ KONEX 분봉 데이터 수집 가능")
        print(f"  - 데이터: {len(df_min)}건")

    except Exception as e:
        print(f"❌ KONEX 분봉 데이터 조회 실패: {e}")

    # 4. WebSocket 실시간 데이터 가능 여부
    try:
        ws_client = RealtimePriceCrawler()
        # KONEX 종목 구독 시도
        # (실제 테스트 필요)

        print(f"\n⏳ KONEX 실시간 데이터: 추가 테스트 필요")

    except Exception as e:
        print(f"❌ KONEX 실시간 데이터 조회 실패: {e}")
```

### 2. OTC (장외시장)

**개요**:
- K-OTC 시장 (한국금융투자협회)
- 종목 수: ~500개
- 거래 시간: 9:00~15:30

**조사 항목**:
```python
# scripts/research_otc.py

async def research_otc_data():
    """OTC 데이터 조사"""

    # KIS API OTC 지원 여부 확인
    kis_client = KISClient()

    try:
        # OTC 종목 리스트 조회 시도
        otc_stocks = await kis_client.get_stock_list(market="OTC")
        print(f"✅ OTC 종목 조회 가능: {len(otc_stocks)}개")

    except Exception as e:
        print(f"❌ KIS API OTC 미지원: {e}")

        # 대안: 한국금융투자협회 API 조사
        print("\n🔍 대안 조사: 한국금융투자협회 API")
        print("  - URL: https://freesis.kofia.or.kr")
        print("  - 무료 여부: 조사 필요")
        print("  - API 제공 여부: 조사 필요")

        return None

    # 샘플 데이터 수집
    sample_code = otc_stocks[0]["code"]
    try:
        df = await kis_client.get_daily_prices(
            stock_code=sample_code,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )

        print(f"\n✅ OTC 일봉 데이터 수집 가능")
        print(f"  - 종목: {sample_code}")
        print(f"  - 데이터: {len(df)}건")

    except Exception as e:
        print(f"❌ OTC 일봉 데이터 조회 실패: {e}")
```

### 3. 프리마켓 (Pre-Market)

**개요**:
- 상장 전 기업 정보
- 공모주 정보, 기업공개(IPO) 예정

**조사 항목**:
```python
# scripts/research_pre_market.py

def research_pre_market_data():
    """프리마켓 데이터 조사"""

    # KIS API 프리마켓 지원 여부
    print("🔍 프리마켓 데이터 조사")
    print("\n1. KIS API 지원 여부:")
    print("  ❌ 프리마켓 전용 API 미제공 (예상)")

    # 대안 조사
    print("\n2. 대안 데이터 소스:")
    print("  - 금융감독원 전자공시시스템 (DART)")
    print("    - URL: https://opendart.fss.or.kr")
    print("    - 제공: IPO 공시, 증권신고서")
    print("    - 무료 여부: ✅ 완전 무료")

    print("\n  - 한국거래소 상장공시")
    print("    - URL: https://kind.krx.co.kr")
    print("    - 제공: 신규상장 정보")
    print("    - 무료 여부: ✅ 완전 무료")

    # 권고사항
    print("\n3. 권고사항:")
    print("  - DART API 연동 우선 검토")
    print("  - IPO 공시 크롤링")
    print("  - 예상 소요: 5-7일")
```

---

## Cost-Benefit Analysis

```python
# scripts/cost_benefit_analysis.py

def analyze_konex_cost_benefit():
    """KONEX 비용/효과 분석"""

    analysis = {
        "market": "KONEX",
        "implementation_cost": {
            "development_days": 3,
            "daily_rate": 0,  # KIS API 무료
            "total_cost": 0
        },
        "benefits": {
            "additional_stocks": 150,
            "market_coverage": "+15%",  # 기존 대비
            "user_value": "중소/벤처 투자자 유입"
        },
        "risks": {
            "data_quality": "KOSPI/KOSDAQ 대비 낮음",
            "liquidity": "거래량 적음",
            "user_demand": "불확실"
        },
        "recommendation": "DEFER"  # 사용자 요청 시 구현
    }

    return analysis


def analyze_otc_cost_benefit():
    """OTC 비용/효과 분석"""

    analysis = {
        "market": "OTC",
        "implementation_cost": {
            "development_days": 5,
            "api_cost": "조사 필요",
            "total_cost": "TBD"
        },
        "benefits": {
            "additional_stocks": 500,
            "market_coverage": "+50%",
            "user_value": "비상장 기업 투자자"
        },
        "risks": {
            "data_availability": "KIS 미지원 가능성 높음",
            "alternative_api_cost": "유료 가능성",
            "user_demand": "매우 불확실"
        },
        "recommendation": "NO-GO"  # 비용 대비 효과 낮음
    }

    return analysis


def analyze_pre_market_cost_benefit():
    """프리마켓 비용/효과 분석"""

    analysis = {
        "market": "프리마켓",
        "implementation_cost": {
            "development_days": 7,
            "dart_api_cost": 0,  # 무료
            "total_cost": 0
        },
        "benefits": {
            "ipo_insights": "공모주 정보 제공",
            "user_value": "IPO 투자자 유입",
            "differentiation": "경쟁사 대비 차별화"
        },
        "risks": {
            "data_processing": "공시 문서 파싱 복잡",
            "update_frequency": "비정기적",
            "user_demand": "중간"
        },
        "recommendation": "CONSIDER"  # Phase 5 고려
    }

    return analysis


if __name__ == "__main__":
    print("\n" + "="*80)
    print("KONEX/OTC/프리마켓 비용/효과 분석")
    print("="*80)

    konex = analyze_konex_cost_benefit()
    otc = analyze_otc_cost_benefit()
    pre_market = analyze_pre_market_cost_benefit()

    for analysis in [konex, otc, pre_market]:
        print(f"\n### {analysis['market']}")
        print(f"구현 비용: {analysis['implementation_cost']['development_days']}일")
        print(f"권고: {analysis['recommendation']}")
```

---

## Documentation

### Research Report Template

```markdown
# KONEX/OTC/프리마켓 데이터 수집 조사 보고서

## 요약

- **조사 기간**: 2024-XX-XX ~ 2024-XX-XX
- **조사자**: [이름]

## 1. KONEX

### 기술적 실현 가능성
- KIS API 지원: ✅ / ❌
- 일봉 데이터: ✅ / ❌
- 분봉 데이터: ✅ / ❌
- 실시간 데이터: ✅ / ❌

### 비용/효과
- 구현 비용: X일
- 추가 종목: 150개
- 권고: GO / DEFER / NO-GO

## 2. OTC

(동일 구조)

## 3. 프리마켓

(동일 구조)

## 최종 권고사항

1. **KONEX**: [권고 + 근거]
2. **OTC**: [권고 + 근거]
3. **프리마켓**: [권고 + 근거]
```

---

## Definition of Done

- [ ] KONEX 데이터 수집 가능성 검증
- [ ] OTC 데이터 수집 가능성 검증
- [ ] 프리마켓 데이터 소스 조사
- [ ] 비용/효과 분석 완료
- [ ] 조사 보고서 작성 (`docs/reports/additional_markets_research.md`)
- [ ] 구현 권고사항 문서화
- [ ] 코드 리뷰 및 머지
