"""
FinanceDataReader 테스트 스크립트
"""
import FinanceDataReader as fdr
from datetime import datetime, timedelta

# 사용 가능한 지수 목록 확인
print("📊 FinanceDataReader 테스트\n")

# 다양한 심볼 시도
symbols_to_try = [
    ("KOSPI (KS11)", "KS11"),
    ("KOSPI (^KS11)", "^KS11"),
    ("KOSDAQ (KQ11)", "KQ11"),
    ("KOSDAQ (^KQ11)", "^KQ11"),
]

end_date = datetime.now()
start_date = end_date - timedelta(days=7)  # 짧은 기간으로 테스트

for name, symbol in symbols_to_try:
    print(f"\n시도: {name} ({symbol})")
    try:
        df = fdr.DataReader(symbol, start_date.strftime("%Y-%m-%d"))
        if df is not None and not df.empty:
            print(f"✅ 성공! {len(df)}건 조회")
            print(f"   최근 데이터: {df.tail(1)}")
        else:
            print("❌ 데이터 없음")
    except Exception as e:
        print(f"❌ 오류: {e}")

# StockListing으로 확인
print("\n\n📋 한국 주식 목록 확인:")
try:
    stocks = fdr.StockListing("KRX")
    print(f"✅ KRX 종목 {len(stocks)}개 조회 성공")
    print(f"   샘플 종목: {stocks.head(3)}")
except Exception as e:
    print(f"❌ 오류: {e}")
