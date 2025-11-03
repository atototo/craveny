"""
모든 종목의 종합 리포트를 A/B 형식으로 재생성

AB_TEST_ENABLED=true 상태에서 실행하여
기존 단일 모델 리포트를 A/B 비교 리포트로 업데이트합니다.
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func
from backend.db.session import SessionLocal
from backend.db.models.prediction import Prediction
from backend.services.stock_analysis_service import update_stock_analysis_summary
from backend.config import settings
import asyncio


async def regenerate_all_reports():
    """모든 종목의 A/B 리포트 재생성"""

    print("=" * 80)
    print("모든 종목 A/B 종합 리포트 재생성")
    print("=" * 80)

    # 1. A/B 테스트 활성화 확인
    print(f"\n[1] A/B 테스트 설정 확인")
    print(f"  - AB_TEST_ENABLED: {settings.AB_TEST_ENABLED}")
    print(f"  - Model A: {settings.MODEL_A_NAME} ({settings.MODEL_A_PROVIDER})")
    print(f"  - Model B: {settings.MODEL_B_NAME} ({settings.MODEL_B_PROVIDER})")

    if not settings.AB_TEST_ENABLED:
        print("\n❌ A/B 테스트가 비활성화되어 있습니다!")
        print("   .env 파일에서 AB_TEST_ENABLED=true로 설정하세요")
        return False

    print("  ✅ A/B 테스트 활성화됨")

    # 2. 종목 목록 조회
    db = SessionLocal()
    try:
        # 예측이 있는 종목 코드 조회
        stock_codes = (
            db.query(Prediction.stock_code)
            .distinct()
            .filter(Prediction.stock_code.isnot(None))
            .all()
        )
        stock_codes = [code[0] for code in stock_codes]

        print(f"\n[2] 종목 목록 조회")
        print(f"  - 총 {len(stock_codes)}개 종목 발견")

        if not stock_codes:
            print("  ⚠️ 예측 데이터가 있는 종목이 없습니다")
            return True

        # 3. 각 종목별 A/B 리포트 생성
        print(f"\n[3] A/B 종합 리포트 생성")
        success_count = 0
        failed_count = 0

        for i, stock_code in enumerate(stock_codes, 1):
            print(f"\n  [{i}/{len(stock_codes)}] {stock_code} 처리 중...")

            try:
                # 강제 업데이트 (force_update=True)
                summary = await update_stock_analysis_summary(
                    stock_code=stock_code,
                    db=db,
                    force_update=True
                )

                if summary:
                    print(f"    ✅ A/B 리포트 생성 완료")
                    success_count += 1
                else:
                    print(f"    ❌ 리포트 생성 실패")
                    failed_count += 1

            except Exception as e:
                print(f"    ❌ 오류 발생: {e}")
                failed_count += 1

        # 4. 결과 요약
        print("\n" + "=" * 80)
        print("재생성 완료")
        print("=" * 80)
        print(f"  - 총 종목: {len(stock_codes)}개")
        print(f"  - 성공: {success_count}개")
        print(f"  - 실패: {failed_count}개")

        if success_count > 0:
            print("\n✅ A/B 종합 리포트 재생성 성공!")
            print("\n다음 단계:")
            print("  1. 백엔드 재시작 (변경사항 적용)")
            print("  2. 종목 분석 페이지 확인")
            print("  3. GPT-4o vs DeepSeek 비교 확인")
        else:
            print("\n⚠️ 성공한 리포트가 없습니다")

        return success_count > 0

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(regenerate_all_reports())
    sys.exit(0 if success else 1)
