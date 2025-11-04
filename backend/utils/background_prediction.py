"""
백그라운드 예측 생성 유틸리티

새 모델 추가 또는 A/B 설정 변경 시 자동으로 예측을 생성합니다.
"""
import logging
import threading
from typing import List, Optional
from datetime import datetime, timedelta

from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.prediction import Prediction
from backend.llm.predictor import get_predictor
from backend.llm.vector_search import get_vector_search
from backend.utils.prediction_status import get_tracker


logger = logging.getLogger(__name__)


def generate_predictions_for_news(
    news_id: int,
    model_ids: List[int],
    in_background: bool = True,
    task_id: Optional[str] = None
) -> None:
    """
    특정 뉴스에 대해 지정된 모델들로 예측을 생성합니다.

    Args:
        news_id: 뉴스 ID
        model_ids: 예측을 생성할 모델 ID 리스트
        in_background: 백그라운드 스레드로 실행 여부
        task_id: 진행 상태 추적용 task ID
    """
    if in_background:
        thread = threading.Thread(
            target=_generate_predictions_worker,
            args=(news_id, model_ids, task_id),
            daemon=True
        )
        thread.start()
        logger.info(f"백그라운드 예측 생성 시작: news_id={news_id}, models={model_ids}")
    else:
        _generate_predictions_worker(news_id, model_ids, task_id)


def _generate_predictions_worker(news_id: int, model_ids: List[int], task_id: Optional[str] = None) -> None:
    """백그라운드 워커: 예측 생성 실행"""
    db = SessionLocal()
    tracker = get_tracker() if task_id else None

    try:
        # 뉴스 조회
        news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()
        if not news:
            logger.warning(f"뉴스를 찾을 수 없음: news_id={news_id}")
            return

        predictor = get_predictor()
        vector_search = get_vector_search()

        # 유사 뉴스 검색
        news_text = f"{news.title}\n{news.content}"
        similar_news = vector_search.get_news_with_price_changes(
            news_text=news_text,
            stock_code=news.stock_code,
            db=db,
            top_k=5,
            similarity_threshold=0.5,
        )

        current_news_data = {
            "title": news.title,
            "content": news.content,
            "stock_code": news.stock_code,
        }

        # 각 모델별로 예측 생성
        for model_id in model_ids:
            # 이미 예측이 있는지 확인
            existing = db.query(Prediction).filter(
                Prediction.news_id == news_id,
                Prediction.model_id == model_id
            ).first()

            if existing:
                logger.debug(f"예측 이미 존재: news_id={news_id}, model_id={model_id}")
                continue

            # 예측 생성
            try:
                model_info = predictor.active_models.get(model_id)
                if not model_info:
                    logger.warning(f"모델을 찾을 수 없음: model_id={model_id}")
                    continue

                # _predict_with_model() 호출 시 올바른 파라미터 전달
                prediction_data = predictor._predict_with_model(
                    client=model_info["client"],
                    model_name=model_info["model_identifier"],
                    provider=model_info["provider"],
                    prompt=predictor._build_prompt(current_news_data, similar_news),
                    similar_count=len(similar_news),
                )

                if prediction_data:
                    predictor._save_model_prediction(
                        news_id=news_id,
                        model_id=model_id,
                        stock_code=news.stock_code,
                        prediction_data=prediction_data,
                    )
                    logger.info(f"✅ 예측 생성 완료: news_id={news_id}, model_id={model_id}")

                    # 진행 상태 업데이트
                    if tracker and task_id:
                        tracker.increment_progress(task_id, success=True)
                else:
                    logger.warning(f"예측 생성 실패: news_id={news_id}, model_id={model_id}")

                    # 진행 상태 업데이트
                    if tracker and task_id:
                        tracker.increment_progress(task_id, success=False)

            except Exception as e:
                logger.error(f"예측 생성 오류: news_id={news_id}, model_id={model_id}, error={e}", exc_info=True)

                # 진행 상태 업데이트
                if tracker and task_id:
                    tracker.increment_progress(task_id, success=False)

    except Exception as e:
        logger.error(f"백그라운드 예측 워커 오류: {e}", exc_info=True)
    finally:
        db.close()


def generate_predictions_for_recent_news(
    model_ids: List[int],
    limit: int = 20,
    days: int = 7,
    in_background: bool = True,
    task_id: Optional[str] = None
) -> dict:
    """
    최근 뉴스에 대해 지정된 모델들로 예측을 생성합니다.

    Args:
        model_ids: 예측을 생성할 모델 ID 리스트
        limit: 처리할 최대 뉴스 개수
        days: 조회할 과거 일수
        in_background: 백그라운드 스레드로 실행 여부
        task_id: 진행 상태 추적용 task ID

    Returns:
        처리 통계 {"total": N, "skipped": M, "scheduled": K, "task_id": str}
    """
    db = SessionLocal()
    tracker = get_tracker()

    try:
        # 최근 N일 이내 뉴스 조회 (종목 코드가 있는 것만)
        cutoff_time = datetime.utcnow() - timedelta(days=days)

        recent_news = (
            db.query(NewsArticle)
            .filter(
                NewsArticle.created_at >= cutoff_time,
                NewsArticle.stock_code.isnot(None),
            )
            .order_by(NewsArticle.created_at.desc())
            .limit(limit)
            .all()
        )

        if not recent_news:
            logger.info("최근 뉴스 없음")
            return {"total": 0, "skipped": 0, "scheduled": 0, "task_id": None}

        logger.info(f"최근 {len(recent_news)}개 뉴스 발견 (최근 {days}일)")

        scheduled_count = 0
        skipped_count = 0

        # 예측 생성할 총 개수 계산
        total_predictions_needed = 0
        news_to_process = []

        for news in recent_news:
            # 각 모델에 대해 예측이 없는지 확인
            missing_models = []
            for model_id in model_ids:
                existing = db.query(Prediction).filter(
                    Prediction.news_id == news.id,
                    Prediction.model_id == model_id
                ).first()

                if not existing:
                    missing_models.append(model_id)

            if missing_models:
                total_predictions_needed += len(missing_models)
                news_to_process.append((news.id, missing_models))
                scheduled_count += 1
            else:
                skipped_count += 1

        # task_id 생성 (없으면 자동 생성)
        if not task_id and total_predictions_needed > 0:
            from backend.db.models.model import Model
            model_names = db.query(Model.name).filter(Model.id.in_(model_ids)).all()
            model_names_str = " vs ".join([name[0] for name in model_names])
            task_id = f"ab_predict_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # 진행 상태 추적 시작
            tracker.start_task(
                task_id=task_id,
                total_count=total_predictions_needed,
                description=f"{model_names_str} 예측 생성 중"
            )
            logger.info(f"진행 상태 추적 시작: {task_id}, 총 {total_predictions_needed}개 예측 생성")

        # 실제 예측 생성
        for news_id, missing_models in news_to_process:
            generate_predictions_for_news(
                news_id=news_id,
                model_ids=missing_models,
                in_background=in_background,
                task_id=task_id
            )

        logger.info(
            f"예측 생성 스케줄 완료: "
            f"total={len(recent_news)}, scheduled={scheduled_count}, skipped={skipped_count}"
        )

        return {
            "total": len(recent_news),
            "skipped": skipped_count,
            "scheduled": scheduled_count,
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"최근 뉴스 예측 생성 오류: {e}", exc_info=True)
        if task_id:
            tracker.fail_task(task_id, str(e))
        return {"total": 0, "skipped": 0, "scheduled": 0, "task_id": None}
    finally:
        db.close()
