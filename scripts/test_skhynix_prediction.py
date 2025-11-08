"""
SK하이닉스 최근 뉴스 5개 LLM 예측 생성 및 종합 리포트 테스트

Phase B: 실전 테스트 - 기술적 지표가 포함된 프롬프트로 실제 예측 생성
"""
import logging
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.prediction import Prediction
from backend.db.models.model import Model
from backend.llm.predictor import StockPredictor
from sqlalchemy import desc
import time

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_skhynix_predictions():
    """SK하이닉스 최근 뉴스 5개에 대해 예측 생성"""
    print("=" * 80)
    print("🔮 SK하이닉스 뉴스 예측 생성 테스트")
    print("=" * 80)

    db = SessionLocal()
    predictor = StockPredictor()

    try:
        # SK하이닉스 최근 뉴스 5개 조회
        news_ids = [1359, 1108, 943, 939, 947]

        # 활성 모델 조회 (DeepSeek만 사용 - 속도 때문)
        model = db.query(Model).filter(
            Model.id == 2,  # DeepSeek V3.2
            Model.is_active == True
        ).first()

        if not model:
            logger.error("❌ DeepSeek 모델을 찾을 수 없습니다")
            return

        logger.info(f"✅ 사용 모델: {model.name} ({model.provider}/{model.model_identifier})")
        logger.info(f"📰 처리할 뉴스: {len(news_ids)}개")
        print()

        predictions = []

        for i, news_id in enumerate(news_ids, 1):
            news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()
            if not news:
                logger.warning(f"⚠️ 뉴스 ID {news_id} 없음")
                continue

            print("=" * 80)
            print(f"📰 뉴스 {i}/{len(news_ids)}: {news.title[:60]}...")
            print(f"   발표일: {news.published_at}")
            print("=" * 80)

            # 기존 예측 확인
            existing = db.query(Prediction).filter(
                Prediction.news_id == news_id,
                Prediction.model_id == model.id
            ).first()

            if existing:
                logger.info(f"✅ 기존 예측 발견 (ID: {existing.id})")
                predictions.append(existing)

                # 예측 결과 출력
                print(f"\n📊 예측 결과:")
                print(f"   방향: {existing.direction}")
                print(f"   신뢰도: {existing.confidence}%")
                print(f"   근거: {existing.reasoning[:200]}...")
                print()
                continue

            # 새로운 예측 생성
            logger.info(f"🔄 새 예측 생성 중...")
            start_time = time.time()

            try:
                prediction = predictor.predict_single(news_id, model.id)
                elapsed = time.time() - start_time

                if prediction:
                    logger.info(f"✅ 예측 생성 완료 (소요시간: {elapsed:.1f}초)")
                    predictions.append(prediction)

                    # 예측 결과 출력
                    print(f"\n📊 예측 결과:")
                    print(f"   방향: {prediction.direction}")
                    print(f"   신뢰도: {prediction.confidence}%")
                    print(f"   근거: {prediction.reasoning[:200]}...")
                    print()
                else:
                    logger.error(f"❌ 예측 생성 실패")

            except Exception as e:
                logger.error(f"❌ 예측 생성 오류: {e}", exc_info=True)

        print("\n" + "=" * 80)
        print(f"✅ 예측 생성 완료: 총 {len(predictions)}개")
        print("=" * 80)

        # 예측 결과 요약
        if predictions:
            print("\n📊 예측 요약:")
            print("-" * 80)
            directions = {}
            for pred in predictions:
                directions[pred.direction] = directions.get(pred.direction, 0) + 1

            for direction, count in directions.items():
                print(f"   {direction}: {count}개")

            avg_confidence = sum(p.confidence for p in predictions) / len(predictions)
            print(f"   평균 신뢰도: {avg_confidence:.1f}%")
            print("-" * 80)

        return predictions

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
    finally:
        db.close()


def test_comprehensive_report():
    """종합 리포트 생성 및 확인 (API 호출)"""
    print("\n\n" + "=" * 80)
    print("📄 종합 리포트 생성 테스트")
    print("=" * 80)

    try:
        import requests

        # SK하이닉스 종목 코드
        stock_code = "000660"

        logger.info(f"\n🔄 {stock_code} 종합 리포트 API 호출 중...")

        # API 호출
        response = requests.post(
            f"http://localhost:8000/api/stock-analysis/{stock_code}/generate-report",
            timeout=60
        )

        if response.status_code == 200:
            report = response.json()

            print("\n✅ 종합 리포트 생성 성공!")
            print("=" * 80)
            print(f"📊 리포트 정보:")
            print(f"   종목: {report.get('stock_code')}")
            print(f"   생성일: {report.get('created_at')}")
            print(f"   분석 뉴스 수: {report.get('total_news_count', 0)}개")
            print(f"   종합 방향: {report.get('overall_direction')}")
            print(f"   평균 신뢰도: {report.get('avg_confidence', 0):.1f}%")
            print()
            print(f"📝 종합 의견:")
            summary = report.get('summary', '')
            print(f"   {summary[:300]}...")
            print("=" * 80)

            # 방향별 통계
            direction_stats = report.get('direction_stats', {})
            if direction_stats:
                print(f"\n📈 방향별 통계:")
                for direction, count in direction_stats.items():
                    print(f"   {direction}: {count}개")

            print("\n✅ 종합 리포트 테스트 완료!")

        else:
            print(f"\n⚠️ 종합 리포트 생성 실패: HTTP {response.status_code}")
            print(f"   응답: {response.text[:200]}")

    except Exception as e:
        logger.error(f"❌ 종합 리포트 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    # 1. 뉴스별 예측 생성
    predictions = test_skhynix_predictions()

    # 2. 종합 리포트 생성
    test_comprehensive_report()

    print("\n\n" + "=" * 80)
    print("🎉 모든 테스트 완료!")
    print("=" * 80)
    print("\n다음 단계:")
    print("  1. 프론트엔드에서 종목 화면 확인")
    print("  2. 기술적 지표가 예측에 어떻게 반영되었는지 검토")
    print("  3. 다른 종목으로도 테스트")
    print("  4. 예측 품질 개선 (필요시)")
