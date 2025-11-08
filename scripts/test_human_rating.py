"""
Test script for human rating update functionality.

Usage:
    python scripts/test_human_rating.py <evaluation_id> <quality> <usefulness> <overall>

Example:
    python scripts/test_human_rating.py 1 4 5 4
"""
import sys
import logging
from backend.db.session import SessionLocal
from backend.services.evaluation_service import EvaluationService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """사람 평가 업데이트 테스트."""
    if len(sys.argv) < 5:
        print("Usage: python scripts/test_human_rating.py <evaluation_id> <quality> <usefulness> <overall>")
        print("Example: python scripts/test_human_rating.py 1 4 5 4")
        return 1

    try:
        evaluation_id = int(sys.argv[1])
        quality = int(sys.argv[2])
        usefulness = int(sys.argv[3])
        overall = int(sys.argv[4])
    except ValueError:
        print("❌ 모든 파라미터는 숫자여야 합니다")
        return 1

    print("=" * 80)
    print("📊 사람 평가 업데이트 테스트")
    print("=" * 80)
    print(f"Evaluation ID: {evaluation_id}")
    print(f"Quality: {quality}/5")
    print(f"Usefulness: {usefulness}/5")
    print(f"Overall: {overall}/5")
    print()

    db = SessionLocal()
    try:
        service = EvaluationService(db)

        # 사람 평가 업데이트
        result = service.update_human_rating(
            evaluation_id=evaluation_id,
            quality=quality,
            usefulness=usefulness,
            overall=overall,
            evaluated_by="test_user",
            reason="테스트 평가"
        )

        if result:
            print()
            print("✅ 사람 평가 업데이트 성공!")
            print(f"Final Score: {result.final_score:.1f}")
            print(f"Auto Score: {(result.target_accuracy_score * 0.4 + result.timing_score * 0.3 + result.risk_management_score * 0.3):.1f}")
            print(f"Human Score: {((quality + usefulness + overall) / 3 * 20):.1f}")
            return 0
        else:
            print()
            print("❌ 사람 평가 업데이트 실패")
            return 1

    except Exception as e:
        logger.error(f"❌ 에러 발생: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
