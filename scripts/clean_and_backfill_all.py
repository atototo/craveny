"""
FDR 데이터 삭제 & KIS 데이터 백필 (10/27~11/7)

1. 기존 FDR 데이터 삭제 (stock_prices, stock_prices_minute)
2. KIS 일봉 데이터 백필 (10/27~11/7)
3. 투자자별 매매동향 백필 (10/27~11/7)
4. 종목 기본정보 수집 (최신)
5. 업종 지수 수집 (최신)

참고: 호가/현재가는 실시간만 제공되어 과거 데이터 없음
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import SessionLocal
from backend.db.models.stock import Stock, StockPrice, StockPriceMinute
from backend.crawlers.kis_daily_crawler import get_kis_daily_crawler
from backend.crawlers.kis_market_data_collector import (
    InvestorTradingCollector,
    StockInfoCollector,
    SectorIndexCollector,
)


def clean_fdr_data():
    """FDR 데이터 삭제"""
    print("=" * 60)
    print("🗑️  기존 FDR 데이터 삭제 시작")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 일봉 데이터 삭제
        daily_count = db.query(StockPrice).filter(StockPrice.source == "fdr").count()
        print(f"📊 일봉 데이터: {daily_count:,}건 삭제 중...")
        db.query(StockPrice).filter(StockPrice.source == "fdr").delete()

        # 1분봉 데이터는 KIS만 있을 것 (확인)
        minute_count = db.query(StockPriceMinute).count()
        print(f"📊 1분봉 데이터: {minute_count:,}건 (KIS 데이터 유지)")

        db.commit()

        print()
        print("✅ FDR 데이터 삭제 완료")
        print(f"   일봉: {daily_count:,}건 삭제")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"❌ 삭제 실패: {e}")
        raise
    finally:
        db.close()


async def backfill_kis_daily(start_date: str, end_date: str):
    """
    KIS 일봉 데이터 백필

    Args:
        start_date: YYYYMMDD
        end_date: YYYYMMDD
    """
    print("=" * 60)
    print("📈 KIS 일봉 데이터 백필 시작")
    print(f"📅 기간: {start_date} ~ {end_date}")
    print("=" * 60)

    # 날짜 문자열을 datetime으로 변환
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")
    days = (end_dt - start_dt).days + 1  # 시작일 포함

    print(f"📊 기간: {days}일")
    print()

    crawler = get_kis_daily_crawler()

    try:
        # backfill_historical_data 메서드 사용
        result = await crawler.backfill_historical_data(days=days)

        print()
        print("=" * 60)
        print(f"✅ KIS 일봉 백필 완료")
        print(f"   성공: {result['success_count']}개 종목")
        print(f"   실패: {result['failed_count']}개 종목")
        print(f"   총 {result['total_saved']:,}건 저장")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 백필 실패: {e}")
        raise


async def backfill_investor_trading(start_date: str, end_date: str):
    """투자자별 매매동향 백필"""
    print("=" * 60)
    print("💼 투자자별 매매동향 백필 시작")
    print(f"📅 기간: {start_date} ~ {end_date}")
    print("=" * 60)

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        stock_codes = [s.code for s in stocks]

        print(f"📊 대상 종목: {len(stock_codes)}개")
        print()

        collector = InvestorTradingCollector(batch_size=5)
        success_count = 0
        fail_count = 0

        for i, stock in enumerate(stocks, 1):
            print(f"[{i}/{len(stocks)}] {stock.name} ({stock.code})")

            try:
                result = await collector.collect_investor_trading(
                    stock_code=stock.code,
                    start_date=start_date,
                    end_date=end_date
                )

                if result["status"] == "success":
                    saved = result.get("saved", 0)
                    print(f"  ✅ {saved}건 저장")
                    success_count += 1
                else:
                    print(f"  ⚠️  데이터 없음")

            except Exception as e:
                print(f"  ❌ 실패: {e}")
                fail_count += 1

            await asyncio.sleep(1.0)

        print()
        print("=" * 60)
        print(f"✅ 투자자별 매매동향 백필 완료")
        print(f"   성공: {success_count}개 종목")
        print(f"   실패: {fail_count}개 종목")
        print("=" * 60)

    finally:
        db.close()


async def collect_stock_info():
    """종목 기본정보 수집"""
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
    """업종 지수 수집"""
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
    """메인 실행"""
    print("\n" + "=" * 60)
    print("🔄 FDR → KIS 데이터 마이그레이션")
    print("=" * 60)
    print()

    # 날짜 설정
    start_date = "20241027"
    end_date = "20241107"

    # 1. FDR 데이터 삭제
    clean_fdr_data()
    print("\n")

    # 2. KIS 일봉 백필
    await backfill_kis_daily(start_date, end_date)
    print("\n")

    # 3. 투자자별 매매동향 백필
    await backfill_investor_trading(start_date, end_date)
    print("\n")

    # 4. 종목 기본정보 수집
    await collect_stock_info()
    print("\n")

    # 5. 업종 지수 수집
    await collect_sector_indices()
    print("\n")

    print("=" * 60)
    print("🎉 모든 작업 완료!")
    print("=" * 60)
    print()
    print("📊 수집된 데이터:")
    print(f"   ✅ 일봉: 10/27~11/7 (KIS)")
    print(f"   ✅ 투자자별 매매동향: 10/27~11/7")
    print(f"   ✅ 종목 기본정보: 최신")
    print(f"   ✅ 업종 지수: 최신")
    print()
    print("⚠️  참고:")
    print("   - 1분봉: 기존 KIS 데이터 유지")
    print("   - 호가/현재가: 실시간만 제공 (앞으로 5분마다 자동 수집)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
