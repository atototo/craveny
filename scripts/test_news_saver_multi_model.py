"""
news_saver.py 멀티 모델 예측 테스트

뉴스 저장 시 모든 활성 모델에 대해 예측이 생성되는지 확인합니다.
"""
import logging
from datetime import datetime

from backend.db.session import SessionLocal
from backend.crawlers.base_crawler import NewsArticleData
from backend.crawlers.news_saver import NewsSaver

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_multi_model_prediction():
    """멀티 모델 예측 생성 테스트"""
    db = SessionLocal()

    try:
        # 테스트 뉴스 데이터
        test_news = NewsArticleData(
            title="[테스트] 삼성전자, AI 반도체 신기술 개발 성공",
            content="삼성전자가 차세대 AI 반도체 기술 개발에 성공했다고 발표했다. "
                   "이번 기술은 기존 대비 성능이 2배 향상되었으며, 전력 소비는 30% 절감되었다.",
            published_at=datetime.utcnow(),
            source="test_source",
            company_name="삼성전자",
            url="https://test.com/news/123",
            author="테스트 기자",
            metadata={}
        )

        # NewsSaver로 저장 (auto_predict=True)
        logger.info("=" * 80)
        logger.info("테스트: 뉴스 저장 및 멀티 모델 예측 생성")
        logger.info("=" * 80)

        saver = NewsSaver(db, auto_predict=True)
        saved_news = saver.save_news(test_news)

        if not saved_news:
            logger.error("❌ 뉴스 저장 실패 (중복일 수 있음)")
            return

        logger.info(f"✅ 뉴스 저장 완료: ID={saved_news.id}")

        # 생성된 예측 조회
        from backend.db.models.prediction import Prediction
        predictions = db.query(Prediction).filter(
            Prediction.news_id == saved_news.id
        ).all()

        logger.info("")
        logger.info("=" * 80)
        logger.info("생성된 예측 확인:")
        logger.info("=" * 80)

        if not predictions:
            logger.warning("⚠️  예측이 생성되지 않았습니다 (임베딩 중복일 수 있음)")
        else:
            for pred in predictions:
                logger.info(
                    f"예측 ID={pred.id} | model_id={pred.model_id} | "
                    f"방향={pred.direction} | 신뢰도={pred.confidence:.2f}"
                )

            # model_id 확인
            model_ids = [p.model_id for p in predictions]
            has_legacy = any(mid is None for mid in model_ids)
            has_multi = any(mid is not None for mid in model_ids)

            logger.info("")
            logger.info("=" * 80)
            logger.info("결과 분석:")
            logger.info("=" * 80)
            logger.info(f"총 예측 수: {len(predictions)}개")
            logger.info(f"레거시 예측 (model_id=None): {'있음 ❌' if has_legacy else '없음 ✅'}")
            logger.info(f"멀티 모델 예측 (model_id 있음): {'있음 ✅' if has_multi else '없음 ❌'}")

            if has_multi and not has_legacy:
                logger.info("")
                logger.info("🎉 SUCCESS: 멀티 모델 예측 시스템 정상 작동!")
            elif has_legacy and not has_multi:
                logger.error("")
                logger.error("❌ FAIL: 레거시 단일 모델 예측만 생성됨")
            else:
                logger.warning("")
                logger.warning("⚠️  WARNING: 레거시 + 멀티 모델 혼재")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    test_multi_model_prediction()
