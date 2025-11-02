#!/usr/bin/env python
"""
기존 뉴스에 대한 예측 일괄 생성

이미 저장된 뉴스 중 예측이 없는 뉴스에 대해 예측을 실행합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.prediction import Prediction
from backend.llm.predictor import StockPredictor
from backend.llm.vector_search import get_vector_search

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def backfill_predictions(limit: int = None):
    """
    예측이 없는 뉴스에 대해 예측을 생성합니다.

    Args:
        limit: 처리할 최대 뉴스 개수 (None이면 전체)
    """
    logger.info("=" * 70)
    logger.info("🚀 기존 뉴스 예측 일괄 생성 시작")
    logger.info("=" * 70)

    db = SessionLocal()
    predictor = None

    try:
        # Predictor 초기화
        logger.info("예측 시스템 초기화 중...")
        predictor = StockPredictor()
        logger.info("✅ 예측 시스템 초기화 완료")

        # 예측이 없는 뉴스 조회 (종목코드가 있는 것만)
        query = (
            db.query(NewsArticle)
            .outerjoin(Prediction, NewsArticle.id == Prediction.news_id)
            .filter(
                NewsArticle.stock_code.isnot(None),  # 종목코드가 있는 뉴스만
                Prediction.id.is_(None)  # 예측이 없는 뉴스
            )
            .order_by(NewsArticle.created_at.desc())
        )

        if limit:
            query = query.limit(limit)

        news_list = query.all()

        logger.info(f"📊 예측 대상 뉴스: {len(news_list)}건")
        logger.info("")

        if len(news_list) == 0:
            logger.info("예측이 필요한 뉴스가 없습니다.")
            return

        # 각 뉴스에 대해 예측 실행
        success_count = 0
        fail_count = 0

        # 벡터 검색 초기화
        vector_search = get_vector_search()

        for idx, news in enumerate(news_list, 1):
            try:
                logger.info(f"[{idx}/{len(news_list)}] 뉴스 ID={news.id}, 종목={news.stock_code}")
                logger.info(f"  제목: {news.title[:60]}")

                # 1. 유사 뉴스 검색
                news_text = f"{news.title} {news.content}"
                similar_news = vector_search.get_news_with_price_changes(
                    news_text=news_text,
                    stock_code=news.stock_code,
                    db=db,
                    top_k=5,
                    similarity_threshold=0.7
                )

                logger.info(f"  유사 뉴스: {len(similar_news)}건")

                # 2. 예측 실행
                current_news = {
                    "title": news.title,
                    "content": news.content,
                    "stock_code": news.stock_code,
                }

                prediction_result = predictor.predict(
                    current_news=current_news,
                    similar_news=similar_news,
                    news_id=news.id,
                    use_cache=True
                )

                if prediction_result:
                    # 예측 방향 변환 (한글 → 영문)
                    prediction_text = prediction_result.get("prediction", "유지")
                    direction_map = {"상승": "up", "하락": "down", "유지": "hold"}
                    direction = direction_map.get(prediction_text, "hold")

                    # 신뢰도 변환 (0-100 → 0.0-1.0)
                    confidence_percent = prediction_result.get("confidence", 0)
                    confidence = confidence_percent / 100.0

                    # 예측 결과 저장
                    prediction = Prediction(
                        news_id=news.id,
                        stock_code=news.stock_code,
                        direction=direction,
                        confidence=confidence,
                        reasoning=prediction_result.get("reasoning", ""),
                        current_price=prediction_result.get("current_price"),
                        target_period="1일"
                    )

                    db.add(prediction)
                    db.commit()

                    logger.info(
                        f"  ✅ 예측 완료: 방향={prediction.direction}, "
                        f"신뢰도={prediction.confidence:.2f}"
                    )
                    success_count += 1
                else:
                    logger.warning(f"  ⚠️  예측 결과 없음")
                    fail_count += 1

            except Exception as e:
                logger.error(f"  ❌ 예측 실패: {e}", exc_info=True)
                db.rollback()
                fail_count += 1

            logger.info("")

        # 최종 결과
        logger.info("=" * 70)
        logger.info("✅ 예측 일괄 생성 완료")
        logger.info("=" * 70)
        logger.info(f"✨ 성공: {success_count}건")
        logger.info(f"❌ 실패: {fail_count}건")
        logger.info(f"📊 전체: {len(news_list)}건")
        logger.info("")

        # 최종 통계
        total_predictions = db.query(Prediction).count()
        logger.info(f"💾 DB 저장 상태: 전체 예측 {total_predictions}건")

    except Exception as e:
        logger.error(f"❌ 예측 일괄 생성 실패: {e}", exc_info=True)
        db.rollback()

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description="기존 뉴스에 대한 예측 일괄 생성")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="처리할 최대 뉴스 개수 (기본값: 전체)"
    )

    args = parser.parse_args()

    backfill_predictions(limit=args.limit)


if __name__ == "__main__":
    main()
