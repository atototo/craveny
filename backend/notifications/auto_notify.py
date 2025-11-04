"""
자동 알림 모듈

새로운 뉴스에 대해 자동으로 예측을 수행하고 텔레그램으로 알림을 전송합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from backend.db.models.news import NewsArticle
from backend.llm.vector_search import get_vector_search
from backend.llm.predictor import get_predictor
from backend.notifications.telegram import get_telegram_notifier
from backend.utils.embedding_deduplicator import get_embedding_deduplicator
from backend.config import settings


logger = logging.getLogger(__name__)


def process_new_news_notifications(
    db: Session,
    lookback_minutes: int = 15,
) -> dict:
    """
    최근에 저장된 뉴스에 대해 자동으로 예측을 수행하고 알림을 전송합니다.

    Args:
        db: 데이터베이스 세션
        lookback_minutes: 조회할 과거 시간 (분 단위)

    Returns:
        처리 통계 {processed, success, failed}
    """
    try:
        # 최근 N분 이내 저장된 뉴스 조회 (종목 코드가 있는 것만)
        cutoff_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)

        recent_news = (
            db.query(NewsArticle)
            .filter(
                NewsArticle.created_at >= cutoff_time,
                NewsArticle.stock_code.isnot(None),
                NewsArticle.notified_at.is_(None),  # 아직 알림을 보내지 않은 뉴스만
            )
            .order_by(NewsArticle.created_at.desc())
            .limit(10)  # 최대 10건만 처리
            .all()
        )

        if not recent_news:
            logger.debug(f"최근 {lookback_minutes}분 이내 새 뉴스 없음")
            return {"processed": 0, "success": 0, "failed": 0}

        logger.info(
            f"🔔 자동 알림 처리: 최근 {lookback_minutes}분 이내 {len(recent_news)}건 발견"
        )

        vector_search = get_vector_search()
        predictor = get_predictor()
        notifier = get_telegram_notifier()
        embedding_deduplicator = get_embedding_deduplicator()

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for news in recent_news:
            try:
                logger.info(f"처리 중: {news.title[:50]}... (종목: {news.stock_code})")

                # 0. 임베딩 기반 알림 중복 검사
                news_text = f"{news.title}\n{news.content}"
                should_skip, similar_id, similarity = embedding_deduplicator.should_skip_notification(
                    news_text=news_text,
                    stock_code=news.stock_code,
                    db=db,
                    notification_lookback_hours=4,
                )

                if should_skip:
                    logger.info(
                        f"🔕 유사 뉴스 알림 이력 존재 (유사도={similarity:.3f}) "
                        f"→ 알림 skip (뉴스 ID={news.id}, 유사 뉴스 ID={similar_id})"
                    )
                    # notified_at 업데이트 (알림 skip했지만 처리는 완료)
                    news.notified_at = datetime.utcnow()
                    db.commit()
                    skipped_count += 1
                    continue

                # 1. 유사 뉴스 검색
                similar_news = vector_search.get_news_with_price_changes(
                    news_text=news_text,
                    stock_code=news.stock_code,
                    db=db,
                    top_k=5,
                    similarity_threshold=0.5,
                )

                # 2. 예측 수행
                current_news_data = {
                    "title": news.title,
                    "content": news.content,
                    "stock_code": news.stock_code,
                }

                # 멀티모델 예측: 모든 활성 모델로 예측 생성
                all_predictions = predictor.predict_all_models(
                    current_news=current_news_data,
                    similar_news=similar_news,
                    news_id=news.id,
                )

                # A/B 설정에 따라 표시할 두 모델 예측 조회
                prediction = predictor.get_ab_predictions(news_id=news.id)

                # 3. 텔레그램 알림 전송
                if notifier.send_prediction(
                    news_title=news.title,
                    stock_code=news.stock_code,
                    prediction=prediction,
                ):
                    # 알림 전송 성공 시 notified_at 업데이트
                    news.notified_at = datetime.utcnow()
                    db.commit()

                    success_count += 1
                    comp = prediction.get("comparison", {})
                    logger.info(
                        f"✅ A/B 알림 전송 성공: {news.title[:30]}... "
                        f"(모델 {len(all_predictions)}개 예측 완료, A/B 일치: {comp.get('agreement')}, 차이: {comp.get('confidence_diff')}%)"
                    )
                else:
                    failed_count += 1
                    logger.warning(f"⚠️  알림 전송 실패: {news.title[:30]}...")

            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 뉴스 처리 실패 (ID={news.id}): {e}", exc_info=True)

        logger.info(
            f"📊 자동 알림 완료: 성공 {success_count}건, 실패 {failed_count}건, skip {skipped_count}건"
        )

        return {
            "processed": len(recent_news),
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
        }

    except Exception as e:
        logger.error(f"❌ 자동 알림 처리 중 오류: {e}", exc_info=True)
        return {"processed": 0, "success": 0, "failed": 0}
