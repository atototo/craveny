"""
model_predictions 테이블 데이터를 predictions 테이블로 마이그레이션

기존 model_predictions (JSON 기반) → predictions (명시적 컬럼)
"""
import sys
import os
import json

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.model import Model  # Foreign key 관계 해결용
from sqlalchemy import text


def migrate_data():
    """model_predictions 데이터를 predictions 테이블로 마이그레이션"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 60)
        print("model_predictions → predictions 데이터 마이그레이션")
        print("=" * 60)

        # 1. model_predictions 데이터 조회
        result = db.execute(text("""
            SELECT news_id, model_id, stock_code, prediction_data, created_at
            FROM model_predictions
            ORDER BY news_id, model_id
        """))

        records = result.fetchall()
        print(f"\n📊 총 {len(records)}개 레코드 발견")

        if len(records) == 0:
            print("✅ 마이그레이션할 데이터 없음")
            return

        # 2. 각 레코드를 predictions 테이블로 이전
        migrated_count = 0
        skipped_count = 0

        for record in records:
            news_id, model_id, stock_code, prediction_data_json, created_at = record

            try:
                # JSON 파싱 (이미 dict인 경우도 처리)
                if isinstance(prediction_data_json, dict):
                    prediction_data = prediction_data_json
                elif isinstance(prediction_data_json, str):
                    prediction_data = json.loads(prediction_data_json)
                else:
                    print(f"⚠️  알 수 없는 타입: {type(prediction_data_json)}")
                    continue

                # predictions 테이블에 이미 존재하는지 확인
                existing = db.query(Prediction).filter(
                    Prediction.news_id == news_id,
                    Prediction.model_id == model_id
                ).first()

                if existing:
                    print(f"⏭️  건너뜀: news_id={news_id}, model_id={model_id} (이미 존재)")
                    skipped_count += 1
                    continue

                # predictions 테이블에 INSERT
                new_prediction = Prediction(
                    news_id=news_id,
                    model_id=model_id,
                    stock_code=stock_code,
                    direction=prediction_data.get("direction", "hold"),
                    confidence=prediction_data.get("confidence", 0.5),
                    reasoning=prediction_data.get("reasoning", ""),
                    current_price=prediction_data.get("current_price"),
                    short_term=prediction_data.get("short_term"),
                    medium_term=prediction_data.get("medium_term"),
                    long_term=prediction_data.get("long_term"),
                    confidence_breakdown=prediction_data.get("confidence_breakdown"),
                    pattern_analysis=prediction_data.get("pattern_analysis"),
                    created_at=created_at,
                )
                db.add(new_prediction)
                migrated_count += 1

                print(f"✅ 마이그레이션: news_id={news_id}, model_id={model_id}, direction={new_prediction.direction}, confidence={new_prediction.confidence:.2f}")

            except Exception as e:
                print(f"❌ 실패: news_id={news_id}, model_id={model_id} - {e}")

        # 3. 커밋
        db.commit()

        print("\n" + "=" * 60)
        print(f"✅ 마이그레이션 완료: {migrated_count}개 성공, {skipped_count}개 건너뜀")
        print("=" * 60)

        # 4. 결과 확인
        pred_count = db.query(Prediction).count()
        print(f"\n📊 predictions 테이블 총 레코드 수: {pred_count}")

    except Exception as e:
        print(f"\n❌ 마이그레이션 실패: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    migrate_data()
