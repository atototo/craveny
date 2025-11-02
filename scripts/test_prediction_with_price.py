"""
현재 주가 정보가 포함된 예측 테스트
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.llm.predictor import get_predictor

# 테스트용 뉴스 데이터 (종목코드가 있는 것)
test_news = {
    "stock_code": "035720",  # 카카오 (주가 데이터가 있는 종목)
    "title": "카카오, 신규 AI 서비스 출시로 실적 개선 기대",
    "content": """
    카카오가 새로운 인공지능 기반 서비스를 출시하며 실적 개선이 기대되고 있다.
    시장 전문가들은 이번 서비스가 카카오의 매출 증대에 기여할 것으로 전망했다.
    특히 AI 기술을 활용한 맞춤형 서비스가 사용자 경험을 크게 향상시킬 것으로 보인다.
    """,
}

# 유사 뉴스 (과거 예시)
similar_news = [
    {
        "news_title": "카카오, 신규 플랫폼 서비스 론칭",
        "news_content": "카카오가 새로운 플랫폼 서비스를 출시했다...",
        "published_at": "2024-10-15",
        "similarity": 0.85,
        "price_changes": {
            "1d": 2.3,
            "3d": 5.1,
            "5d": 7.8,
        },
    }
]

print("=" * 70)
print("🧪 현재 주가 정보 포함 예측 테스트")
print("=" * 70)
print()

# 예측 수행
predictor = get_predictor()

print(f"📰 테스트 뉴스: {test_news['title']}")
print(f"🏢 종목 코드: {test_news['stock_code']}")
print()

print("🔮 예측 수행 중...")
result = predictor.predict(
    current_news=test_news,
    similar_news=similar_news,
    use_cache=False,  # 테스트용이므로 캐시 사용 안 함
)

print()
print("=" * 70)
print("📊 예측 결과")
print("=" * 70)
print(f"예측 방향: {result.get('prediction', 'N/A')}")
print(f"신뢰도: {result.get('confidence', 0)}%")
print()
print(f"📅 기간별 예측:")
print(f"  • T+1일: {result.get('short_term', 'N/A')}")
print(f"  • T+3일: {result.get('medium_term', 'N/A')}")
print(f"  • T+5일: {result.get('long_term', 'N/A')}")
print()
print(f"💡 예측 근거:")
print(f"{result.get('reasoning', 'N/A')}")
print()
print(f"📌 참고 정보:")
print(f"  • 유사 뉴스: {result.get('similar_count', 0)}건")
print(f"  • 모델: {result.get('model', 'N/A')}")
print(f"  • 캐시 사용: {result.get('cached', False)}")
print("=" * 70)
