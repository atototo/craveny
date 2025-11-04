"""
백그라운드 예측 생성 테스트 스크립트
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.utils.background_prediction import generate_predictions_for_recent_news

def test():
    """백그라운드 예측 생성 테스트"""
    print("\n" + "=" * 60)
    print("백그라운드 예측 생성 테스트")
    print("=" * 60)

    try:
        # GPT-4o (model_id=1)과 Claude (model_id=4)에 대해 테스트
        print("\n테스트 대상: GPT-4o (1) vs Claude (4)")
        print("최근 20개 뉴스, 최근 7일")
        print("백그라운드 실행: False (동기 실행으로 테스트)\n")

        stats = generate_predictions_for_recent_news(
            model_ids=[1, 4],
            limit=20,
            days=7,
            in_background=False  # 동기 실행으로 테스트
        )

        print("\n" + "=" * 60)
        print("결과:")
        print(f"  총 뉴스 개수: {stats['total']}")
        print(f"  예측 스케줄: {stats['scheduled']}")
        print(f"  스킵된 개수: {stats['skipped']}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test()
