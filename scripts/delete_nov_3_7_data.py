"""
11월 3-7일 데이터 삭제 스크립트

KIS API 프롬프트 업데이트 이전에 생성된 데이터를 삭제합니다.
- Prediction (1,486개)
- StockAnalysisSummary (종합 투자 리포트)
- ModelEvaluation (138개)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from collections import defaultdict
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.model_evaluation import ModelEvaluation


def delete_old_data():
    """11월 3-7일 기존 데이터 삭제"""
    db = SessionLocal()

    try:
        start_date = datetime(2025, 11, 3)
        end_date = datetime(2025, 11, 8)  # 11월 7일 23:59:59까지

        print("=" * 80)
        print("🗑️  11월 3-7일 데이터 삭제 시작")
        print("=" * 80)

        # 1. Prediction 삭제
        print("\n📊 Prediction 데이터 조회 중...")
        predictions = db.query(Prediction).filter(
            Prediction.created_at >= start_date,
            Prediction.created_at < end_date
        ).all()

        pred_count = len(predictions)
        print(f"   총 {pred_count}개 Prediction 발견")

        if pred_count > 0:
            # 모델별 카운트
            by_model = defaultdict(int)
            for p in predictions:
                if p.model_id:
                    by_model[p.model_id] += 1
                else:
                    by_model["None"] += 1

            print("   모델별 분포:")
            for model_id in sorted(by_model.keys(), key=lambda x: (x == "None", x)):
                print(f"     - Model {model_id}: {by_model[model_id]}개")

            # 삭제
            for p in predictions:
                db.delete(p)

            db.commit()
            print(f"✅ {pred_count}개 Prediction 삭제 완료")
        else:
            print("⚠️  삭제할 Prediction 없음")

        # 2. StockAnalysisSummary 삭제
        print("\n📑 StockAnalysisSummary (종합 투자 리포트) 조회 중...")
        summaries = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.last_updated >= start_date,
            StockAnalysisSummary.last_updated < end_date
        ).all()

        summary_count = len(summaries)
        print(f"   총 {summary_count}개 StockAnalysisSummary 발견")

        if summary_count > 0:
            # 종목별 카운트
            by_stock = defaultdict(int)
            for s in summaries:
                by_stock[s.stock_code] += 1

            print("   종목별 분포:")
            for stock_code in sorted(by_stock.keys()):
                print(f"     - {stock_code}: {by_stock[stock_code]}개")

            # 삭제
            for s in summaries:
                db.delete(s)

            db.commit()
            print(f"✅ {summary_count}개 StockAnalysisSummary 삭제 완료")
        else:
            print("⚠️  삭제할 StockAnalysisSummary 없음")

        # 3. ModelEvaluation 삭제
        print("\n📈 ModelEvaluation 데이터 조회 중...")
        evaluations = db.query(ModelEvaluation).filter(
            ModelEvaluation.predicted_at >= start_date,
            ModelEvaluation.predicted_at < end_date
        ).all()

        eval_count = len(evaluations)
        print(f"   총 {eval_count}개 ModelEvaluation 발견")

        if eval_count > 0:
            # 모델별 카운트
            by_model_eval = defaultdict(int)
            for e in evaluations:
                by_model_eval[e.model_id] += 1

            print("   모델별 분포:")
            for model_id in sorted(by_model_eval.keys()):
                print(f"     - Model {model_id}: {by_model_eval[model_id]}개")

            # 삭제
            for e in evaluations:
                db.delete(e)

            db.commit()
            print(f"✅ {eval_count}개 ModelEvaluation 삭제 완료")
        else:
            print("⚠️  삭제할 ModelEvaluation 없음")

        # 4. 최종 확인
        print("\n" + "=" * 80)
        print("🎯 삭제 완료 요약")
        print("=" * 80)
        print(f"   Prediction: {pred_count}개 삭제")
        print(f"   StockAnalysisSummary: {summary_count}개 삭제")
        print(f"   ModelEvaluation: {eval_count}개 삭제")
        print(f"   총: {pred_count + summary_count + eval_count}개 레코드 삭제")
        print()
        print("✅ 11월 3-7일 데이터 삭제 완료!")
        print("   이제 새 프롬프트로 재생성할 수 있습니다.")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n⚠️  경고: 11월 3-7일 모든 데이터를 삭제합니다.")
    print("   - Prediction (뉴스별 영향도 분석)")
    print("   - StockAnalysisSummary (종합 투자 리포트)")
    print("   - ModelEvaluation (모델 평가)")
    response = input("계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        delete_old_data()
    else:
        print("❌ 취소되었습니다.")
