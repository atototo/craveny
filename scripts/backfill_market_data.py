"""
과거 시장 데이터 수집 스크립트 (10/27 ~ 11/7)

수집 가능 데이터:
- 투자자별 매매동향 (일별)
- 종목 기본정보 (현재 스냅샷)
- 업종 지수 (현재 스냅샷)

수집 불가 데이터 (실시간만 제공):
- 호가 데이터
- 현재가 데이터
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.crawlers.kis_market_data_collector import (
    InvestorTradingCollector,
    StockInfoCollector,
    SectorIndexCollector,
)
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock


async def backfill_investor_trading(start_date: str, end_date: str):
    """
    투자자별 매매동향 과거 데이터 수집

    Args:
        start_date: YYYYMMDD
        end_date: YYYYMMDD
    """
    print("=" * 60)
    print("💼 투자자별 매매동향 과거 데이터 수집 시작")
    print(f"📅 기간: {start_date} ~ {end_date}")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 활성화된 종목 조회
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        stock_codes = [s.code for s in stocks]

        print(f"📊 대상 종목: {len(stock_codes)}개")
        print()

        # 각 종목별로 수집
        collector = InvestorTradingCollector(batch_size=5)

        success_count = 0
        fail_count = 0

        for i, stock_code in enumerate(stock_codes, 1):
            stock = next(s for s in stocks if s.code == stock_code)
            print(f"[{i}/{len(stock_codes)}] {stock.name} ({stock_code})")

            try:
                result = await collector.collect_investor_trading(
                    stock_code=stock_code,
                    start_date=start_date,
                    end_date=end_date
                )

                if result["status"] == "success":
                    print(f"  ✅ {result.get('saved', 0)}건 저장")
                    success_count += 1
                else:
                    print(f"  ⚠️  데이터 없음")

            except Exception as e:
                print(f"  ❌ 실패: {e}")
                fail_count += 1

            # Rate limiting
            await asyncio.sleep(1.0)

        print()
        print("=" * 60)
        print(f"✅ 투자자별 매매동향 수집 완료")
        print(f"   성공: {success_count}개 종목")
        print(f"   실패: {fail_count}개 종목")
        print("=" * 60)

    finally:
        db.close()


async def collect_stock_info():
    """
    종목 기본정보 수집 (최신 스냅샷)
    """
    print("=" * 60)
    print("ℹ️  종목 기본정보 수집 시작")
    print("=" * 60)

    collector = StockInfoCollector(batch_size=10)
    result = await collector.collect_all()

    print()
    print("=" * 60)
    print(f"✅ 종목 기본정보 수집 완료")
    print(f"   성공: {result['collected']}건")
    print(f"   실패: {result['failed']}건")
    print("=" * 60)


async def collect_sector_indices():
    """
    업종 지수 수집 (최신 스냅샷)
    """
    print("=" * 60)
    print("📊 업종 지수 수집 시작")
    print("=" * 60)

    collector = SectorIndexCollector()
    result = await collector.collect_all()

    print()
    print("=" * 60)
    print(f"✅ 업종 지수 수집 완료")
    print(f"   성공: {result['collected']}건")
    print(f"   실패: {result['failed']}건")
    print("=" * 60)


async def main():
    """메인 실행 함수"""
    print("\n" + "=" * 60)
    print("📦 과거 시장 데이터 수집 시작")
    print("=" * 60)
    print()

    # 날짜 설정 (10/27 ~ 11/7)
    start_date = "20241027"
    end_date = "20241107"

    # 1. 투자자별 매매동향 (과거 데이터)
    await backfill_investor_trading(start_date, end_date)
    print("\n")

    # 2. 종목 기본정보 (최신 스냅샷)
    await collect_stock_info()
    print("\n")

    # 3. 업종 지수 (최신 스냅샷)
    await collect_sector_indices()
    print("\n")

    print("=" * 60)
    print("🎉 모든 수집 완료!")
    print("=" * 60)
    print()
    print("⚠️  참고사항:")
    print("   - 호가 데이터: 실시간만 제공 (과거 데이터 없음)")
    print("   - 현재가 데이터: 실시간만 제공 (과거 데이터 없음)")
    print("   → 앞으로 자동 수집됩니다 (5분마다)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
