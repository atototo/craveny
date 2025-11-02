"""
크롤러 스케줄러 시작 스크립트

전체 자동화 프로세스를 시작합니다:
- 뉴스 크롤링 (10분마다)
- 종목 코드 매칭 (10분마다)
- 임베딩 생성 및 저장 (10분마다)
- 자동 알림 전송 (10분마다)
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from backend.scheduler.crawler_scheduler import CrawlerScheduler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """크롤러 스케줄러 시작"""
    logger.info("=" * 70)
    logger.info("🚀 크롤러 스케줄러 시작")
    logger.info("=" * 70)
    logger.info("")
    logger.info("📌 자동화 작업:")
    logger.info("   1. 뉴스 크롤링 (네이버, 한국경제, 매일경제)")
    logger.info("   2. 종목 코드 매칭")
    logger.info("   3. 임베딩 생성 및 Milvus 저장")
    logger.info("   4. 자동 예측 + 텔레그램 알림")
    logger.info("")
    logger.info("⏰ 실행 주기: 10분마다")
    logger.info("")
    logger.info("💡 중지하려면 Ctrl+C를 누르세요")
    logger.info("=" * 70)
    logger.info("")

    try:
        # 스케줄러 생성 및 시작
        scheduler = CrawlerScheduler(
            news_interval_minutes=10,  # 10분마다
            stock_interval_minutes=1,  # 1분마다 (주가 수집)
        )

        scheduler.start()

        # 블로킹 (스케줄러가 계속 실행되도록)
        logger.info("✅ 스케줄러 실행 중...")
        logger.info("")

        # 무한 대기
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("⏹️  사용자가 중지를 요청했습니다")
        logger.info("=" * 70)
        scheduler.stop()
        logger.info("✅ 크롤러 스케줄러 중지됨")
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ 크롤러 실행 중 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
