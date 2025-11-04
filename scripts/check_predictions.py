"""
예측 데이터 확인 스크립트
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.model import Model
from backend.db.models.news import NewsArticle
from sqlalchemy import func
from datetime import datetime, timedelta

def check_predictions():
    """각 모델별 예측 데이터 확인"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 60)
        print("모델별 예측 데이터 현황")
        print("=" * 60)

        # 모델별 예측 개수 조회
        results = (
            db.query(
                Model.id,
                Model.name,
                func.count(Prediction.id).label('prediction_count'),
                func.max(Prediction.created_at).label('latest_prediction')
            )
            .outerjoin(Prediction, Model.id == Prediction.model_id)
            .group_by(Model.id, Model.name)
            .order_by(Model.id)
            .all()
        )

        for model_id, model_name, count, latest in results:
            latest_str = latest.strftime('%Y-%m-%d %H:%M:%S') if latest else 'N/A'
            print(f"\n[{model_id}] {model_name}")
            print(f"  예측 개수: {count}개")
            print(f"  최근 예측: {latest_str}")

        # 최근 7일 뉴스 개수
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        recent_news_count = (
            db.query(func.count(NewsArticle.id))
            .filter(
                NewsArticle.created_at >= cutoff_time,
                NewsArticle.stock_code.isnot(None),
            )
            .scalar()
        )

        print("\n" + "=" * 60)
        print(f"최근 7일 뉴스 (종목코드 있는 것): {recent_news_count}개")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    check_predictions()
