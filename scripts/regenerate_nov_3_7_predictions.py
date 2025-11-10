"""
11월 3-7일 Prediction 재생성 스크립트

새 프롬프트(KIS API 데이터 포함)로 모든 활성 모델의 예측을 재생성합니다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datetime import datetime, timedelta
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.model import Model
from backend.db.models.prediction import Prediction
from backend.llm.predictor import get_predictor
from backend.llm.vector_search import get_vector_search
from sqlalchemy import and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def regenerate_predictions():
    """11월 3-7일 Prediction 재생성"""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("🔄 11월 3-7일 Prediction 재생성 시작")
        print("=" * 80)

        # 1. 활성 모델 조회
        models = db.query(Model).filter(Model.is_active == True).all()
        if not models:
            print("❌ 활성 모델이 없습니다.")
            return

        print(f"\n📊 활성 모델: {len(models)}개")
        for model in models:
            print(f"   - Model {model.id}: {model.name} ({model.provider}/{model.model_identifier})")

        # 2. 11월 3-7일 뉴스 조회
        start_date = datetime(2025, 11, 3)
        end_date = datetime(2025, 11, 8)

        news_articles = db.query(NewsArticle).filter(
            and_(
                NewsArticle.published_at >= start_date,
                NewsArticle.published_at < end_date,
                NewsArticle.stock_code.isnot(None)
            )
        ).order_by(NewsArticle.published_at.asc()).all()

        print(f"\n📰 11월 3-7일 뉴스: {len(news_articles)}개")

        if not news_articles:
            print("⚠️  재생성할 뉴스가 없습니다.")
            return

        # 3. Predictor와 VectorSearch 초기화
        predictor = get_predictor()
        vector_search = get_vector_search()
        print(f"\n🤖 StockPredictor 초기화 완료")
        print(f"   활성 모델 {len(predictor.active_models)}개 로드됨")

        # 4. 각 뉴스에 대해 모든 모델로 예측 생성
        total_predictions = 0
        success_count = 0
        error_count = 0

        from collections import defaultdict
        by_date = defaultdict(int)
        by_model = defaultdict(int)

        for idx, news in enumerate(news_articles, 1):
            news_date = news.published_at.strftime("%Y-%m-%d")
            print(f"\n[{idx}/{len(news_articles)}] 뉴스 ID {news.id} ({news_date}) - {news.stock_code}")

            # 유사 뉴스 검색
            news_text = f"{news.title}\n{news.content}"
            similar_news = vector_search.get_news_with_price_changes(
                news_text=news_text,
                stock_code=news.stock_code,
                db=db,
                top_k=5,
                similarity_threshold=0.7,
            )

            # 현재 뉴스 데이터
            current_news_data = {
                "title": news.title,
                "content": news.content,
                "stock_code": news.stock_code,
            }

            for model_id, model_info in predictor.active_models.items():
                total_predictions += 1

                try:
                    # 모델별 클라이언트 사용
                    temp_client = predictor.client
                    temp_model = predictor.model

                    # 현재 모델로 전환
                    predictor.client = model_info["client"]
                    predictor.model = model_info["model_identifier"]

                    # 예측 수행
                    result = predictor.predict(
                        current_news=current_news_data,
                        similar_news=similar_news,
                        news_id=news.id,
                        use_cache=False,  # 재생성이므로 캐시 사용 안 함
                    )

                    # 원래 클라이언트 복원
                    predictor.client = temp_client
                    predictor.model = temp_model

                    if result:
                        # DB에 저장
                        prediction = Prediction(
                            news_id=news.id,
                            stock_code=news.stock_code,
                            model_id=model_id,
                            sentiment_direction=result.get("sentiment_direction"),
                            sentiment_score=result.get("sentiment_score"),
                            impact_level=result.get("impact_level"),
                            relevance_score=result.get("relevance_score"),
                            urgency_level=result.get("urgency_level"),
                            reasoning=result.get("reasoning"),
                            impact_analysis=result.get("impact_analysis"),
                            pattern_analysis=result.get("pattern_analysis"),
                            current_price=result.get("current_price"),
                            created_at=news.published_at,  # 뉴스 발행 시간 사용
                        )
                        db.add(prediction)
                        db.commit()

                        success_count += 1
                        by_date[news_date] += 1
                        by_model[model_id] += 1
                        print(f"   ✅ Model {model_id}: {result.get('sentiment_direction')} (impact: {result.get('impact_level')})")
                    else:
                        error_count += 1
                        print(f"   ❌ Model {model_id}: 예측 실패")

                except Exception as e:
                    error_count += 1
                    print(f"   ❌ Model {model_id}: {e}")
                    import traceback
                    traceback.print_exc()

        # 5. 최종 결과
        print("\n" + "=" * 80)
        print("🎯 재생성 완료 요약")
        print("=" * 80)
        print(f"   총 시도: {total_predictions}개")
        print(f"   성공: {success_count}개")
        print(f"   실패: {error_count}개")
        if total_predictions > 0:
            print(f"   성공률: {success_count / total_predictions * 100:.1f}%")
        else:
            print(f"   성공률: N/A")

        print(f"\n📅 날짜별 생성 현황:")
        for date in sorted(by_date.keys()):
            print(f"   {date}: {by_date[date]}개")

        print(f"\n🤖 모델별 생성 현황:")
        for model_id in sorted(by_model.keys()):
            model_name = predictor.active_models[model_id]['name']
            print(f"   Model {model_id} ({model_name}): {by_model[model_id]}개")

        print("\n✅ 11월 3-7일 Prediction 재생성 완료!")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n📢 11월 3-7일 모든 Prediction을 새 프롬프트로 재생성합니다.")
    print("   (KIS API 데이터 포함)")
    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        asyncio.run(regenerate_predictions())
    else:
        print("❌ 취소되었습니다.")
