"""
Manual evaluation runner for testing.

Usage:
    python scripts/run_evaluation.py                    # 어제 날짜 평가
    python scripts/run_evaluation.py 2025-11-05        # 특정 날짜 평가
"""
import sys
import logging
from datetime import datetime, timedelta

from backend.scheduler.evaluation_scheduler import EvaluationScheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """수동 평가 실행."""
    print("=" * 80)
    print("📊 모델 평가 수동 실행 도구")
    print("=" * 80)

    # 날짜 입력
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            print(f"❌ 잘못된 날짜 형식: {date_str} (예: 2025-11-05)")
            return 1
    else:
        target_date = datetime.now() - timedelta(days=1)

    print(f"📅 평가 대상 날짜: {target_date.date()}")
    print()

    # 평가 실행
    scheduler = EvaluationScheduler()
    scheduler.run_manual(target_date)

    return 0


if __name__ == "__main__":
    sys.exit(main())
