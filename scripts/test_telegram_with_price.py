"""
현재 주가 정보가 포함된 텔레그램 알림 테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.notifications.telegram import get_telegram_notifier

# 테스트용 예측 결과
test_prediction = {
    "prediction": "상승",
    "confidence": 80,
    "reasoning": "카카오의 신규 AI 서비스 출시는 과거 유사 사례와 유사한 긍정적 영향을 미칠 가능성이 높습니다.",
    "short_term": "T+1일: 2.5% 상승 예상",
    "medium_term": "T+3일: 5.3% 상승 예상",
    "long_term": "T+5일: 7.8% 상승 예상",
    "similar_count": 1,
    "model": "gpt-4o",
    "timestamp": "2025-11-01 16:30:00",
}

test_news_title = "카카오, 신규 AI 서비스 출시로 실적 개선 기대"
test_stock_code = "035720"  # 카카오

print("=" * 70)
print("📱 텔레그램 알림 테스트 (현재 주가 포함)")
print("=" * 70)
print()

notifier = get_telegram_notifier()

print(f"📰 뉴스: {test_news_title}")
print(f"🏢 종목: {test_stock_code}")
print()

print("📤 텔레그램 알림 전송 중...")
success = notifier.send_prediction(
    news_title=test_news_title,
    stock_code=test_stock_code,
    prediction=test_prediction,
)

print()
if success:
    print("✅ 텔레그램 알림 전송 성공!")
    print()
    print("💡 확인 사항:")
    print("  1. 종목명이 표시되는가? (예: 카카오 (035720))")
    print("  2. 현재 주가가 표시되는가? (예: 💰 현재 주가: 65,100원)")
    print("  3. 거래량이 표시되는가?")
    print("  4. 퍼센트 예측이 표시되는가? (예: T+1일: 2.5% 상승 예상)")
else:
    print("❌ 텔레그램 알림 전송 실패")

print("=" * 70)
