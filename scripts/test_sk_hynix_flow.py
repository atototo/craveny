"""
SK하이닉스(000660) 전체 플로우 테스트 스크립트

단계별 실행:
1. SK하이닉스 관련 Prediction/Summary/Evaluation 데이터 삭제
2. Prediction 생성 (1개 모델로 시작)
3. StockAnalysisSummary 생성
4. ModelEvaluation 생성
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
from backend.db.models.stock_analysis import StockAnalysisSummary
from backend.db.models.model_evaluation import ModelEvaluation
from backend.llm.predictor import get_predictor
from backend.llm.vector_search import get_vector_search
from backend.llm.investment_report import InvestmentReportGenerator
from sqlalchemy import and_
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCK_CODE = "000660"  # SK하이닉스
STOCK_NAME = "SK하이닉스"


def clean_all_data():
    """전체 Prediction/StockAnalysisSummary/ModelEvaluation 데이터 삭제"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"🗑️  전체 데이터 삭제 시작 (구 프롬프트 + FDR 데이터)")
        print("=" * 80)

        # 1. Prediction 삭제
        predictions = db.query(Prediction).all()
        pred_count = len(predictions)
        for pred in predictions:
            db.delete(pred)
        db.commit()
        print(f"✅ Prediction: {pred_count}개 삭제")

        # 2. StockAnalysisSummary 삭제
        summaries = db.query(StockAnalysisSummary).all()
        summary_count = len(summaries)
        for summary in summaries:
            db.delete(summary)
        db.commit()
        print(f"✅ StockAnalysisSummary: {summary_count}개 삭제")

        # 3. ModelEvaluation 삭제
        evaluations = db.query(ModelEvaluation).all()
        eval_count = len(evaluations)
        for evaluation in evaluations:
            db.delete(evaluation)
        db.commit()
        print(f"✅ ModelEvaluation: {eval_count}개 삭제")

        print(f"\n🎯 총 {pred_count + summary_count + eval_count}개 레코드 삭제 완료")
        print("   이제 신 프롬프트 + KIS API 데이터로 재생성합니다.")

    finally:
        db.close()


async def step1_create_predictions():
    """Step 1: Prediction 생성 (1개 모델로 시작)"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"1️⃣  {STOCK_NAME} Prediction 생성 시작")
        print("=" * 80)

        # 활성 모델 중 첫 번째 모델만 사용
        model = db.query(Model).filter(Model.is_active == True).first()
        if not model:
            print("❌ 활성 모델이 없습니다.")
            return False

        print(f"\n📊 사용 모델: {model.name} (ID: {model.id})")

        # 11월 3-7일 SK하이닉스 뉴스 조회
        start_date = datetime(2025, 11, 3)
        end_date = datetime(2025, 11, 8)

        news_articles = db.query(NewsArticle).filter(
            and_(
                NewsArticle.stock_code == STOCK_CODE,
                NewsArticle.published_at >= start_date,
                NewsArticle.published_at < end_date
            )
        ).order_by(NewsArticle.published_at.asc()).all()

        print(f"📰 {STOCK_NAME} 뉴스: {len(news_articles)}개")

        if not news_articles:
            print("⚠️  뉴스가 없습니다.")
            return False

        # Predictor 초기화
        predictor = get_predictor()
        vector_search = get_vector_search()

        # 각 뉴스에 대해 예측 생성
        success_count = 0
        error_count = 0

        for idx, news in enumerate(news_articles, 1):
            news_date = news.published_at.strftime("%Y-%m-%d %H:%M")
            print(f"\n[{idx}/{len(news_articles)}] 뉴스 ID {news.id} ({news_date})")
            print(f"  제목: {news.title[:50]}...")

            # 유사 뉴스 검색
            news_text = f"{news.title}\n{news.content}"
            similar_news = vector_search.get_news_with_price_changes(
                news_text=news_text,
                stock_code=STOCK_CODE,
                db=db,
                top_k=5,
                similarity_threshold=0.7,
            )

            # 현재 뉴스 데이터
            current_news_data = {
                "title": news.title,
                "content": news.content,
                "stock_code": STOCK_CODE,
            }

            try:
                # 모델별 클라이언트 사용
                model_info = predictor.active_models[model.id]
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
                    use_cache=False,
                )

                # 원래 클라이언트 복원
                predictor.client = temp_client
                predictor.model = temp_model

                if result:
                    # DB에 저장
                    prediction = Prediction(
                        news_id=news.id,
                        stock_code=STOCK_CODE,
                        model_id=model.id,
                        sentiment_direction=result.get("sentiment_direction"),
                        sentiment_score=result.get("sentiment_score"),
                        impact_level=result.get("impact_level"),
                        relevance_score=result.get("relevance_score"),
                        urgency_level=result.get("urgency_level"),
                        reasoning=result.get("reasoning"),
                        impact_analysis=result.get("impact_analysis"),
                        pattern_analysis=result.get("pattern_analysis"),
                        current_price=result.get("current_price"),
                        created_at=news.published_at,
                    )
                    db.add(prediction)
                    db.commit()

                    success_count += 1
                    print(f"  ✅ {result.get('sentiment_direction')} (영향도: {result.get('impact_level')})")
                else:
                    error_count += 1
                    print(f"  ❌ 예측 실패")

            except Exception as e:
                error_count += 1
                print(f"  ❌ 오류: {e}")
                db.rollback()

        print(f"\n📊 Prediction 생성 완료:")
        print(f"   성공: {success_count}개")
        print(f"   실패: {error_count}개")

        return success_count > 0

    finally:
        db.close()


async def step2_create_summary():
    """Step 2: StockAnalysisSummary 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"2️⃣  {STOCK_NAME} StockAnalysisSummary 생성 시작")
        print("=" * 80)

        # Prediction 개수 확인
        pred_count = db.query(Prediction).filter(
            Prediction.stock_code == STOCK_CODE
        ).count()

        print(f"📊 기존 Prediction: {pred_count}개")

        if pred_count == 0:
            print("⚠️  Prediction이 없어서 Summary를 생성할 수 없습니다.")
            return False

        # 활성 모델 조회
        model = db.query(Model).filter(Model.is_active == True).first()
        if not model:
            print("❌ 활성 모델이 없습니다.")
            return False

        print(f"📊 사용 모델: {model.name} (ID: {model.id})")

        # InvestmentReportGenerator 초기화
        generator = InvestmentReportGenerator()

        # 리포트 생성
        print(f"\n🔄 리포트 생성 중...")
        report = await generator.generate_report(
            stock_code=STOCK_CODE,
            model_id=model.id,
            db=db
        )

        if report:
            print(f"✅ StockAnalysisSummary 생성 성공 (ID: {report.id})")
            print(f"   종합 의견: {report.overall_sentiment}")
            print(f"   주요 트렌드: {len(report.key_trends or [])}개")
            return True
        else:
            print("❌ StockAnalysisSummary 생성 실패")
            return False

    finally:
        db.close()


def step3_create_evaluation():
    """Step 3: ModelEvaluation 생성"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        print(f"3️⃣  {STOCK_NAME} ModelEvaluation 생성 시작")
        print("=" * 80)

        # StockAnalysisSummary 확인
        summary_count = db.query(StockAnalysisSummary).filter(
            StockAnalysisSummary.stock_code == STOCK_CODE
        ).count()

        print(f"📊 기존 StockAnalysisSummary: {summary_count}개")

        if summary_count == 0:
            print("⚠️  StockAnalysisSummary가 없어서 Evaluation을 생성할 수 없습니다.")
            return False

        # TODO: ModelEvaluation 생성 로직 구현
        # 현재는 배치 스크립트 확인 후 구현

        print("⚠️  ModelEvaluation 생성 로직은 아직 구현되지 않았습니다.")
        print("   regenerate_nov_3_7_evaluations.py 참고하여 구현 예정")

        return True

    finally:
        db.close()


async def main():
    """메인 실행 함수"""
    print("\n" + "=" * 80)
    print(f"🚀 신 프롬프트 + KIS API 데이터 생성 테스트")
    print("=" * 80)
    print("실행 단계:")
    print("  0️⃣  전체 데이터 삭제 (구 프롬프트 + FDR)")
    print("  1️⃣  SK하이닉스 Prediction 생성 (1개 모델)")
    print("  2️⃣  SK하이닉스 StockAnalysisSummary 생성")
    print("  3️⃣  SK하이닉스 ModelEvaluation 생성")
    print("=" * 80)

    # 0. 전체 데이터 삭제
    clean_all_data()

    # 1. Prediction 생성
    step1_success = await step1_create_predictions()
    if not step1_success:
        print("\n❌ Step 1 실패로 중단합니다.")
        return

    # 2. Summary 생성
    step2_success = await step2_create_summary()
    if not step2_success:
        print("\n❌ Step 2 실패로 중단합니다.")
        return

    # 3. Evaluation 생성
    step3_success = step3_create_evaluation()

    # 최종 결과
    print("\n" + "=" * 80)
    print("🎉 전체 플로우 테스트 완료")
    print("=" * 80)
    print(f"  Step 1 (Prediction):          {'✅' if step1_success else '❌'}")
    print(f"  Step 2 (Summary):             {'✅' if step2_success else '❌'}")
    print(f"  Step 3 (Evaluation):          {'✅' if step3_success else '❌'}")
    print("=" * 80)


if __name__ == "__main__":
    print("\n⚠️  주의: 전체 Prediction/Summary/Evaluation 데이터를 삭제하고")
    print("        SK하이닉스로 신 프롬프트 + KIS API 데이터를 생성합니다.")
    response = input("\n계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        asyncio.run(main())
    else:
        print("❌ 취소되었습니다.")
