"""
개선된 LLM 예측 시스템 테스트 스크립트

Phase 1 개선사항 검증:
1. 프롬프트 개선 (공시 정보 포함)
2. 신뢰도 계산 로직 투명화 (confidence_breakdown)
3. 예측 근거 구체화 (pattern_analysis)
4. JSON 응답 스키마 확장
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.llm.predictor import get_predictor
from backend.llm.vector_search import NewsVectorSearch


def print_section(title: str):
    """섹션 헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_single_news(news_id: int, db: Session):
    """
    단일 뉴스로 개선된 예측 시스템 테스트

    Args:
        news_id: 테스트할 뉴스 ID
        db: DB 세션
    """
    # 1. 뉴스 조회
    news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()

    if not news:
        print(f"❌ 뉴스 ID {news_id}를 찾을 수 없습니다.")
        return

    print_section(f"테스트 뉴스 #{news_id}")
    print(f"제목: {news.title}")
    print(f"종목: {news.stock_code}")
    print(f"발표일: {news.published_at}")
    print(f"출처: {news.source}")
    print(f"\n내용 (처음 200자):\n{news.content[:200]}...")

    # 2. 유사 뉴스 검색
    print_section("유사 뉴스 검색")
    vector_search = NewsVectorSearch()
    similar_news = vector_search.search_similar_news(
        news_text=f"{news.title}\n{news.content}",
        stock_code=news.stock_code,
        top_k=5
    )

    print(f"✅ 유사 뉴스 {len(similar_news)}건 검색 완료")
    for i, sim_news in enumerate(similar_news, 1):
        print(f"\n{i}. (유사도: {sim_news.get('similarity', 0):.2%}) {sim_news.get('news_title', 'N/A')[:50]}...")

    # 3. 예측 수행
    print_section("LLM 예측 수행")
    predictor = get_predictor()

    current_news = {
        "title": news.title,
        "content": news.content,
        "stock_code": news.stock_code,
    }

    try:
        prediction_result = predictor.predict(
            current_news=current_news,
            similar_news=similar_news,
            news_id=news_id,
            use_cache=False  # 테스트이므로 캐시 미사용
        )

        # 4. 결과 출력
        print_section("📊 예측 결과")

        print(f"🔮 예측 방향: {prediction_result.get('prediction', 'N/A')}")
        print(f"📈 신뢰도: {prediction_result.get('confidence', 0)}%")

        # 🆕 신뢰도 breakdown (Phase 1.2)
        breakdown = prediction_result.get("confidence_breakdown", {})
        if breakdown:
            print(f"\n💡 신뢰도 구성 요소:")
            print(f"  - 유사 뉴스 품질: {breakdown.get('similar_news_quality', 'N/A')}점")
            print(f"  - 패턴 일관성: {breakdown.get('pattern_consistency', 'N/A')}점")
            print(f"  - 공시 영향: {breakdown.get('disclosure_impact', 'N/A')}점")
            print(f"  - 설명: {breakdown.get('explanation', 'N/A')}")

        # 🆕 패턴 분석 (Phase 1.3)
        pattern = prediction_result.get("pattern_analysis", {})
        if pattern and pattern.get('avg_1d') is not None:
            print(f"\n📊 유사 패턴 통계:")
            print(f"  - T+1일 평균: {pattern.get('avg_1d', 'N/A')}%")
            print(f"  - T+3일 평균: {pattern.get('avg_3d', 'N/A')}%")
            print(f"  - T+5일 평균: {pattern.get('avg_5d', 'N/A')}%")
            if 'max_1d' in pattern:
                print(f"  - T+1일 최대/최소: {pattern.get('max_1d', 'N/A')}% / {pattern.get('min_1d', 'N/A')}%")

        print(f"\n📅 기간별 예측:")
        print(f"  - 단기 (T+1일): {prediction_result.get('short_term', 'N/A')}")
        print(f"  - 중기 (T+3일): {prediction_result.get('medium_term', 'N/A')}")
        print(f"  - 장기 (T+5일): {prediction_result.get('long_term', 'N/A')}")

        print(f"\n💭 예측 근거:")
        reasoning = prediction_result.get("reasoning", "N/A")
        # 여러 줄일 경우 들여쓰기
        for line in reasoning.split('\n'):
            print(f"  {line}")

        print(f"\n📌 참고 정보:")
        print(f"  - 유사 뉴스 수: {prediction_result.get('similar_count', 0)}건")
        print(f"  - 사용 모델: {prediction_result.get('model', 'N/A')}")
        print(f"  - 예측 시각: {prediction_result.get('timestamp', 'N/A')}")

        # 5. JSON 전체 출력 (디버깅용)
        print_section("🔍 전체 JSON 응답 (디버깅)")
        print(json.dumps(prediction_result, ensure_ascii=False, indent=2))

        # 6. 품질 평가
        print_section("✅ Phase 1 개선사항 검증")
        checks = []

        # Check 1: confidence_breakdown 존재
        if "confidence_breakdown" in prediction_result:
            checks.append("✅ 신뢰도 breakdown 제공")
        else:
            checks.append("❌ 신뢰도 breakdown 누락")

        # Check 2: pattern_analysis 존재
        if "pattern_analysis" in prediction_result:
            checks.append("✅ 패턴 분석 통계 제공")
        else:
            checks.append("❌ 패턴 분석 통계 누락")

        # Check 3: reasoning에 구체적 수치 포함 여부
        if reasoning and any(char.isdigit() for char in reasoning):
            checks.append("✅ 예측 근거에 구체적 수치 포함")
        else:
            checks.append("⚠️  예측 근거에 수치 부족")

        # Check 4: 기간별 예측 모두 존재
        if all(key in prediction_result for key in ['short_term', 'medium_term', 'long_term']):
            checks.append("✅ 기간별 예측 모두 제공")
        else:
            checks.append("❌ 기간별 예측 일부 누락")

        for check in checks:
            print(check)

        return prediction_result

    except Exception as e:
        print(f"\n❌ 예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """메인 함수"""
    print_section("🚀 개선된 LLM 예측 시스템 테스트")
    print(f"테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    db = SessionLocal()

    try:
        # 최근 뉴스 10건 조회 (종목코드가 있는 것만)
        recent_news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .order_by(NewsArticle.published_at.desc())
            .limit(10)
            .all()
        )

        if not recent_news:
            print("❌ 테스트할 뉴스가 없습니다.")
            return

        print(f"\n✅ 테스트 대상 뉴스 {len(recent_news)}건 발견")

        # 사용자에게 선택 옵션 제공
        print("\n테스트 옵션:")
        print("1. 첫 번째 뉴스만 테스트 (빠름)")
        print("2. 모든 뉴스 테스트 (느림, 비용 주의)")

        choice = input("\n선택 (1 또는 2): ").strip()

        if choice == "2":
            # 전체 테스트
            results = []
            for i, news in enumerate(recent_news, 1):
                print(f"\n\n{'*' * 80}")
                print(f"테스트 {i}/{len(recent_news)}")
                print('*' * 80)

                result = test_single_news(news.id, db)
                if result:
                    results.append({
                        "news_id": news.id,
                        "title": news.title[:50],
                        "prediction": result.get("prediction"),
                        "confidence": result.get("confidence"),
                        "has_breakdown": "confidence_breakdown" in result,
                        "has_pattern": "pattern_analysis" in result,
                    })

            # 전체 결과 요약
            print_section("📊 전체 테스트 결과 요약")
            print(f"\n총 테스트: {len(results)}건")
            print(f"신뢰도 breakdown 제공: {sum(1 for r in results if r['has_breakdown'])}건")
            print(f"패턴 분석 제공: {sum(1 for r in results if r['has_pattern'])}건")

            print("\n\n예측 결과 분포:")
            for result in results:
                print(f"  [{result['news_id']}] {result['title']}: {result['prediction']} ({result['confidence']}%)")

        else:
            # 첫 번째 뉴스만 테스트
            test_single_news(recent_news[0].id, db)

    finally:
        db.close()

    print_section("✅ 테스트 완료")


if __name__ == "__main__":
    main()
