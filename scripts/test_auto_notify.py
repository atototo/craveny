"""
자동 알림 시스템 통합 테스트

새 뉴스 추가 → 자동 알림 → 예측 → 텔레그램 전송 전체 플로우를 테스트합니다.
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


def test_auto_notification():
    """자동 알림 시스템 통합 테스트"""
    logger.info("=" * 70)
    logger.info("🔔 자동 알림 시스템 통합 테스트")
    logger.info("=" * 70)

    db = SessionLocal()

    try:
        # 1. 테스트용 뉴스 추가
        logger.info("📝 테스트 뉴스 추가 중...")
        test_news = NewsArticle(
            title="삼성전자, 신형 반도체 공정 개발 성공으로 실적 개선 기대",
            content=(
                "삼성전자가 차세대 3나노 공정 개발에 성공하며 반도체 시장에서의 경쟁력을 "
                "한층 강화했다. 업계 전문가들은 이번 기술 혁신이 향후 실적 개선으로 이어질 "
                "것으로 전망하고 있다. 새로운 공정은 기존 대비 전력 효율이 30% 향상되었으며, "
                "처리 속도도 20% 빨라졌다. 이는 AI 칩과 고성능 컴퓨팅 시장에서 강점을 가질 "
                "것으로 예상된다."
            ),
            source="테스트",
            published_at=datetime.now(),
            stock_code="005930",  # 삼성전자
        )

        db.add(test_news)
        db.commit()
        db.refresh(test_news)

        logger.info(f"✅ 테스트 뉴스 추가 완료 (ID: {test_news.id})")
        logger.info(f"   제목: {test_news.title[:50]}...")
        logger.info(f"   종목: {test_news.stock_code}")
        logger.info(f"   created_at: {test_news.created_at}")
        logger.info(f"   current time: {datetime.now()}")
        logger.info("")

        # 2. 자동 알림 프로세스 실행
        logger.info("🔔 자동 알림 프로세스 실행 중...")
        stats = process_new_news_notifications(
            db=db,
            lookback_minutes=60,  # 최근 60분 이내 뉴스 (넉넉하게)
        )

        # 3. 결과 확인
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 테스트 결과")
        logger.info("=" * 70)
        logger.info(f"처리된 뉴스: {stats['processed']}건")
        logger.info(f"성공: {stats['success']}건")
        logger.info(f"실패: {stats['failed']}건")
        logger.info("")

        if stats["success"] > 0:
            logger.info("✅ 자동 알림 시스템 테스트 성공!")
            logger.info("")
            logger.info("💡 다음을 확인하세요:")
            logger.info("   1. 텔레그램 앱에서 알림 메시지 도착 확인")
            logger.info("   2. 메시지에 예측 결과가 포함되어 있는지 확인")
            logger.info("   3. 유사 뉴스 개수와 예측 근거 확인")
            return True
        else:
            logger.error("❌ 알림 전송 실패")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 중 오류 발생: {e}", exc_info=True)
        return False

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 자동 알림 시스템 통합 테스트 시작")
    logger.info("")

    success = test_auto_notification()

    logger.info("")
    logger.info("=" * 70)
    if success:
        logger.info("🎉 모든 테스트 통과!")
        sys.exit(0)
    else:
        logger.error("❌ 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
