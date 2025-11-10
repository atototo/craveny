"""
시간외 거래 가격 백필 스크립트

최근 30일의 시간외 거래 데이터를 수집합니다.
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.crawlers.kis_market_data_collector import OvertimePriceCollector


async def main():
    """메인 실행"""
    print("\n" + "=" * 60)
    print("🌙 시간외 거래 가격 백필 시작")
    print("=" * 60)
    print()

    try:
        # 전체 종목 수집 (최근 30일)
        collector = OvertimePriceCollector(batch_size=10)
        result = await collector.collect_all()

        print()
        print("=" * 60)
        print("✅ 시간외 거래 가격 백필 완료")
        print(f"   성공: {result['collected']}건")
        print(f"   실패: {result['failed']}건")
        print("=" * 60)
        print()

        return result['failed'] == 0

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 백필 실패: {e}")
        print("=" * 60)
        print()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
