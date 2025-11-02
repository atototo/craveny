"""
중복 알림 방지 테스트

같은 뉴스에 대해 여러 번 알림을 시도했을 때 중복 방지가 제대로 작동하는지 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.notifications.auto_notify import process_new_news_notifications

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_duplicate_prevention():
    """중복 알림 방지 테스트"""
    logger.info("=" * 70)
    logger.info("🔄 중복 알림 방지 테스트")
    logger.info("=" * 70)

    db = SessionLocal()

    try:
        # 1. 테스트용 뉴스 추가
        logger.info("📝 테스트 뉴스 추가 중...")
        test_news = NewsArticle(
            title="현대차, 전기차 신모델 출시로 시장 점유율 확대 기대",
            content=(
                "현대자동차가 새로운 전기차 라인업을 공개하며 글로벌 전기차 시장에서의 "
                "입지를 강화하고 있다. 신모델은 1회 충전으로 500km 이상 주행이 가능하며, "
                "급속충전 시 30분 이내에 80% 충전이 완료된다. 업계는 이번 신모델 출시로 "
                "현대차의 시장 점유율이 크게 늘어날 것으로 전망하고 있다."
            ),
            source="테스트",
            published_at=datetime.now(),
            stock_code="005380",  # 현대차
        )

        db.add(test_news)
        db.commit()
        db.refresh(test_news)

        logger.info(f"✅ 테스트 뉴스 추가 완료 (ID: {test_news.id})")
        logger.info(f"   제목: {test_news.title[:50]}...")
        logger.info(f"   종목: {test_news.stock_code}")
        logger.info(f"   notified_at: {test_news.notified_at}")
        logger.info("")

        # 2. 첫 번째 알림 실행
        logger.info("1️⃣  첫 번째 알림 실행 중...")
        stats1 = process_new_news_notifications(db=db, lookback_minutes=60)

        logger.info(f"   처리: {stats1['processed']}건")
        logger.info(f"   성공: {stats1['success']}건")
        logger.info(f"   실패: {stats1['failed']}건")
        logger.info("")

        # 3. 뉴스 상태 확인
        db.refresh(test_news)
        logger.info(f"   notified_at 업데이트됨: {test_news.notified_at}")
        logger.info("")

        # 4. 두 번째 알림 실행 (중복 방지 확인)
        logger.info("2️⃣  두 번째 알림 실행 중 (중복 방지 테스트)...")
        stats2 = process_new_news_notifications(db=db, lookback_minutes=60)

        logger.info(f"   처리: {stats2['processed']}건")
        logger.info(f"   성공: {stats2['success']}건")
        logger.info(f"   실패: {stats2['failed']}건")
        logger.info("")

        # 5. 결과 검증
        logger.info("=" * 70)
        logger.info("📊 테스트 결과")
        logger.info("=" * 70)

        success = True

        if stats1["success"] >= 1:
            logger.info("✅ 첫 번째 알림: 정상 전송됨")
        else:
            logger.error("❌ 첫 번째 알림: 전송 실패")
            success = False

        if stats2["processed"] == 0:
            logger.info("✅ 두 번째 알림: 중복 방지 성공 (처리 건수 0)")
        else:
            logger.error(
                f"❌ 두 번째 알림: 중복 방지 실패 (처리 건수 {stats2['processed']})"
            )
            success = False

        if test_news.notified_at is not None:
            logger.info(f"✅ notified_at: {test_news.notified_at}")
        else:
            logger.error("❌ notified_at: 업데이트되지 않음")
            success = False

        logger.info("")

        if success:
            logger.info("🎉 모든 테스트 통과!")
            logger.info("")
            logger.info("💡 확인 사항:")
            logger.info("   - 텔레그램에 알림이 1개만 왔는지 확인하세요")
            logger.info("   - 두 번째 실행에서는 알림이 오지 않아야 합니다")
            return True
        else:
            logger.error("❌ 일부 테스트 실패")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 중 오류 발생: {e}", exc_info=True)
        return False

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 중복 알림 방지 테스트 시작")
    logger.info("")

    success = test_duplicate_prevention()

    logger.info("")
    logger.info("=" * 70)
    if success:
        logger.info("✅ 테스트 성공")
        sys.exit(0)
    else:
        logger.error("❌ 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
