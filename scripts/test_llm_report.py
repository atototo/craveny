"""
LLM 기반 투자 리포트 생성 테스트 스크립트
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.services.stock_analysis_service import update_stock_analysis_summary, get_stock_analysis_summary
import asyncio
import json


async def test_llm_report():
    """LLM 리포트 생성 테스트"""
    db = SessionLocal()

    try:
        # 테스트 종목: 삼성전자
        stock_code = "005930"

        print(f"\n{'='*60}")
        print(f"📊 종목 {stock_code}에 대한 LLM 투자 리포트 생성 테스트")
        print(f"{'='*60}\n")

        # 1. 기존 캐시 조회
        print("1️⃣  기존 캐시 조회...")
        existing_summary = get_stock_analysis_summary(stock_code, db)

        if existing_summary:
            print("✅ 기존 캐시 발견:")
            print(f"   - 마지막 업데이트: {existing_summary['meta']['last_updated']}")
            print(f"   - 분석 예측 건수: {existing_summary['meta']['based_on_prediction_count']}")
        else:
            print("❌ 기존 캐시 없음\n")

        # 2. LLM 리포트 생성 (강제 업데이트)
        print("\n2️⃣  LLM 리포트 생성 중...")
        summary_obj = await update_stock_analysis_summary(stock_code, db, force_update=True)

        if not summary_obj:
            print("❌ 리포트 생성 실패!")
            return

        print("✅ 리포트 생성 완료!\n")

        # 3. 생성된 리포트 조회
        print("3️⃣  생성된 리포트 내용:")
        print(f"{'='*60}\n")

        new_summary = get_stock_analysis_summary(stock_code, db)

        if new_summary:
            print(f"📈 종합 의견:")
            print(f"   {new_summary['overall_summary']}\n")

            if new_summary['short_term_scenario']:
                print(f"🔹 단기 시나리오 (1-3일):")
                print(f"   {new_summary['short_term_scenario']}\n")

            if new_summary['medium_term_scenario']:
                print(f"🔸 중기 시나리오 (5-10일):")
                print(f"   {new_summary['medium_term_scenario']}\n")

            if new_summary['long_term_scenario']:
                print(f"🔶 장기 시나리오 (20일+):")
                print(f"   {new_summary['long_term_scenario']}\n")

            if new_summary['risk_factors']:
                print(f"⚠️  리스크 요인:")
                for i, risk in enumerate(new_summary['risk_factors'], 1):
                    print(f"   {i}. {risk}")
                print()

            if new_summary['opportunity_factors']:
                print(f"💡 기회 요인:")
                for i, opp in enumerate(new_summary['opportunity_factors'], 1):
                    print(f"   {i}. {opp}")
                print()

            if new_summary['recommendation']:
                print(f"🎯 최종 추천:")
                print(f"   {new_summary['recommendation']}\n")

            print(f"{'='*60}")
            print(f"📊 통계:")
            stats = new_summary['statistics']
            print(f"   - 총 예측: {stats['total_predictions']}건")
            print(f"   - 상승/하락/보합: {stats['up_count']}/{stats['down_count']}/{stats['hold_count']}")
            print(f"   - 평균 신뢰도: {stats['avg_confidence']}%")
            print(f"{'='*60}\n")

            # JSON 형식으로도 출력
            print("📄 JSON 응답:")
            print(json.dumps(new_summary, ensure_ascii=False, indent=2))

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_llm_report())
