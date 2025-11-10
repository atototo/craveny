"""
11월 3-7일 전체 데이터 재생성 통합 스크립트

KIS API 프롬프트 업데이트 후 모든 데이터를 재생성합니다.

실행 순서:
1. 기존 데이터 삭제
2. Prediction 재생성 (뉴스별 영향도 분석)
3. StockAnalysisSummary 재생성 (종합 투자 리포트)
4. ModelEvaluation 재생성 (모델 평가)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_script(script_name: str, description: str):
    """
    스크립트 실행

    Args:
        script_name: 실행할 스크립트 파일명
        description: 스크립트 설명
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"▶️  {description}")
    logger.info(f"{'='*80}")

    script_path = Path(__file__).parent / script_name

    # Python 스크립트 직접 import 후 실행
    try:
        if script_name == "delete_nov_3_7_data.py":
            from delete_nov_3_7_data import delete_old_data
            delete_old_data()

        elif script_name == "regenerate_nov_3_7_predictions.py":
            from regenerate_nov_3_7_predictions import regenerate_predictions
            await regenerate_predictions()

        elif script_name == "regenerate_nov_3_7_reports.py":
            from regenerate_nov_3_7_reports import regenerate_all_reports
            await regenerate_all_reports()

        elif script_name == "regenerate_nov_3_7_evaluations.py":
            from regenerate_nov_3_7_evaluations import regenerate_all_evaluations
            regenerate_all_evaluations()

        logger.info(f"✅ {description} 완료")

    except Exception as e:
        logger.error(f"❌ {description} 실패: {e}")
        import traceback
        traceback.print_exc()
        raise


async def regenerate_all():
    """11월 3-7일 전체 데이터 재생성"""
    logger.info("\n" + "=" * 80)
    logger.info("🚀 11월 3-7일 전체 데이터 재생성 시작")
    logger.info("=" * 80)
    logger.info("KIS API 프롬프트 업데이트 반영")
    logger.info("\n실행 순서:")
    logger.info("  1️⃣  기존 데이터 삭제")
    logger.info("  2️⃣  Prediction 재생성")
    logger.info("  3️⃣  StockAnalysisSummary 재생성")
    logger.info("  4️⃣  ModelEvaluation 재생성")
    logger.info("=" * 80)

    try:
        # 1. 기존 데이터 삭제
        await run_script(
            "delete_nov_3_7_data.py",
            "1️⃣  기존 데이터 삭제"
        )

        # 2. Prediction 재생성
        await run_script(
            "regenerate_nov_3_7_predictions.py",
            "2️⃣  Prediction 재생성 (뉴스별 영향도 분석)"
        )

        # 3. StockAnalysisSummary 재생성
        await run_script(
            "regenerate_nov_3_7_reports.py",
            "3️⃣  StockAnalysisSummary 재생성 (종합 투자 리포트)"
        )

        # 4. ModelEvaluation 재생성
        await run_script(
            "regenerate_nov_3_7_evaluations.py",
            "4️⃣  ModelEvaluation 재생성 (모델 평가)"
        )

        # 최종 요약
        logger.info("\n" + "=" * 80)
        logger.info("🎉 전체 재생성 완료!")
        logger.info("=" * 80)
        logger.info("✅ 11월 3-7일 모든 데이터가 새 프롬프트로 재생성되었습니다.")
        logger.info("   - Prediction (뉴스별 영향도 분석)")
        logger.info("   - StockAnalysisSummary (종합 투자 리포트)")
        logger.info("   - ModelEvaluation (모델 평가)")
        logger.info("\n📊 프론트엔드에서 확인하세요:")
        logger.info("   - http://localhost:3000 (메인 페이지)")
        logger.info("   - http://localhost:3000/ab-test (A/B 테스트)")
        logger.info("   - http://localhost:3000/models (모델 평가)")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 재생성 실패: {e}")
        logger.error("   일부 단계만 완료되었을 수 있습니다.")
        raise


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("⚠️  경고: 11월 3-7일 모든 데이터를 삭제하고 재생성합니다.")
    print("=" * 80)
    print("삭제 대상:")
    print("  - Prediction (뉴스별 영향도 분석)")
    print("  - StockAnalysisSummary (종합 투자 리포트)")
    print("  - ModelEvaluation (모델 평가)")
    print("\n재생성:")
    print("  - 새 프롬프트 (KIS API 데이터 포함)")
    print("  - 모든 활성 모델 (멀티모델 시스템)")
    print("=" * 80)

    response = input("\n계속하시겠습니까? (yes/no): ")

    if response.lower() == "yes":
        asyncio.run(regenerate_all())
    else:
        print("❌ 취소되었습니다.")
