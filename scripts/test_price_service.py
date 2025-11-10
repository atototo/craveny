"""
가격 서비스 테스트 스크립트

시간대별 가격 조회 테스트
"""
import sys
from pathlib import Path
from datetime import datetime, time

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.db.session import SessionLocal
from backend.services.price_service import get_current_price, get_market_status


def test_market_status():
    """시장 상태 테스트"""
    print("\n" + "=" * 60)
    print("📊 시장 상태 테스트")
    print("=" * 60)

    test_times = [
        (datetime(2025, 11, 9, 8, 0), "08:00", "closed"),
        (datetime(2025, 11, 9, 8, 45), "08:45", "pre_market"),
        (datetime(2025, 11, 9, 9, 30), "09:30", "market"),
        (datetime(2025, 11, 9, 12, 0), "12:00", "market"),
        (datetime(2025, 11, 9, 15, 0), "15:00", "market"),
        (datetime(2025, 11, 9, 16, 0), "16:00", "post_market"),
        (datetime(2025, 11, 9, 17, 30), "17:30", "post_market"),
        (datetime(2025, 11, 9, 19, 0), "19:00", "closed"),
    ]

    for test_time, time_str, expected in test_times:
        status = get_market_status(test_time)
        emoji = "✅" if status == expected else "❌"
        print(f"{emoji} {time_str} → {status} (예상: {expected})")

    print()


def test_price_retrieval():
    """가격 조회 테스트"""
    print("=" * 60)
    print("💰 가격 조회 테스트")
    print("=" * 60)

    db = SessionLocal()

    try:
        # 테스트할 종목 (삼성전자)
        stock_code = "005930"

        # 다양한 시간대 테스트
        test_times = [
            (datetime(2025, 11, 9, 8, 45), "08:45 (장전 시간외)"),
            (datetime(2025, 11, 9, 10, 0), "10:00 (장중)"),
            (datetime(2025, 11, 9, 16, 30), "16:30 (장후 시간외)"),
            (datetime(2025, 11, 9, 20, 0), "20:00 (장마감)"),
        ]

        print(f"\n종목: {stock_code} (삼성전자)\n")

        for test_time, time_desc in test_times:
            price_info = get_current_price(stock_code, db, test_time)

            print(f"📍 {time_desc}")
            if price_info:
                print(f"   가격: {price_info.get('price'):,.0f}원")
                print(f"   전일대비: {price_info.get('change', 0):+,.0f}원 ({price_info.get('change_rate', 0):+.2f}%)")
                print(f"   출처: {price_info.get('source')}")
                print(f"   시장상태: {price_info.get('market_status')}")
                if price_info.get('volume'):
                    print(f"   거래량: {price_info.get('volume'):,}주")
            else:
                print("   ⚠️  가격 정보 없음")
            print()

    finally:
        db.close()


def test_current_time():
    """현재 시간 기준 테스트"""
    print("=" * 60)
    print("🕐 현재 시간 기준 테스트")
    print("=" * 60)

    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    market_status = get_market_status()

    status_text = {
        'market': '장중',
        'pre_market': '장전 시간외',
        'post_market': '장후 시간외',
        'closed': '장마감'
    }

    print(f"\n현재 시각: {current_time}")
    print(f"시장 상태: {status_text.get(market_status, market_status)}")

    db = SessionLocal()

    try:
        # 여러 종목 테스트
        test_stocks = [
            ("005930", "삼성전자"),
            ("000660", "SK하이닉스"),
            ("035720", "카카오"),
        ]

        print("\n종목별 현재가:")
        print("-" * 60)

        for stock_code, stock_name in test_stocks:
            price_info = get_current_price(stock_code, db)

            if price_info:
                print(f"{stock_name:10s} | {price_info.get('price'):>10,.0f}원 | "
                      f"{price_info.get('change_rate', 0):>+6.2f}% | "
                      f"{price_info.get('source'):>12s}")
            else:
                print(f"{stock_name:10s} | 가격 정보 없음")

        print()

    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 가격 서비스 테스트 시작")
    print("=" * 60)

    # 1. 시장 상태 테스트
    test_market_status()

    # 2. 가격 조회 테스트
    test_price_retrieval()

    # 3. 현재 시간 테스트
    test_current_time()

    print("=" * 60)
    print("✅ 테스트 완료")
    print("=" * 60)
    print()
