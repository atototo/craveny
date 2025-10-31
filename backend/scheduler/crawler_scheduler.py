"""
뉴스 크롤러 스케줄러

APScheduler를 사용하여 주기적으로 뉴스를 크롤링합니다.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.crawlers.naver_crawler import NaverNewsCrawler
from backend.crawlers.hankyung_crawler import HankyungNewsCrawler
from backend.crawlers.maeil_crawler import MaeilNewsCrawler
from backend.crawlers.news_saver import NewsSaver
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """크롤러 스케줄러 클래스"""

    def __init__(self, interval_minutes: int = 10):
        """
        Args:
            interval_minutes: 크롤링 실행 간격 (분 단위)
        """
        self.interval_minutes = interval_minutes
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

        # 크롤링 통계
        self.total_crawls = 0
        self.total_saved = 0
        self.total_skipped = 0
        self.total_errors = 0

    def _crawl_all_sources(self) -> None:
        """
        모든 언론사에서 뉴스를 크롤링하고 저장합니다.
        """
        logger.info("=" * 60)
        logger.info(f"🔄 뉴스 크롤링 시작 (#{self.total_crawls + 1})")
        logger.info("=" * 60)

        db = SessionLocal()
        saver = NewsSaver(db)

        saved_total = 0
        skipped_total = 0

        try:
            # 1. 네이버 뉴스 크롤링
            try:
                logger.info("📰 네이버 뉴스 크롤링...")
                with NaverNewsCrawler() as naver:
                    news_list = naver.fetch_news(limit=10)
                    if news_list:
                        saved, skipped = saver.save_news_batch(news_list)
                        saved_total += saved
                        skipped_total += skipped
                        logger.info(f"   ✅ 네이버: {saved}건 저장, {skipped}건 스킵")
                    else:
                        logger.warning("   ⚠️  네이버: 뉴스 없음")
            except Exception as e:
                self.total_errors += 1
                logger.error(f"   ❌ 네이버 크롤링 실패: {e}")

            # 2. 한국경제 뉴스 크롤링
            try:
                logger.info("📰 한국경제 뉴스 크롤링...")
                with HankyungNewsCrawler() as hankyung:
                    news_list = hankyung.fetch_news(limit=10)
                    if news_list:
                        saved, skipped = saver.save_news_batch(news_list)
                        saved_total += saved
                        skipped_total += skipped
                        logger.info(f"   ✅ 한국경제: {saved}건 저장, {skipped}건 스킵")
                    else:
                        logger.warning("   ⚠️  한국경제: 뉴스 없음")
            except Exception as e:
                self.total_errors += 1
                logger.error(f"   ❌ 한국경제 크롤링 실패: {e}")

            # 3. 매일경제 뉴스 크롤링
            try:
                logger.info("📰 매일경제 뉴스 크롤링...")
                with MaeilNewsCrawler() as maeil:
                    news_list = maeil.fetch_news(limit=10)
                    if news_list:
                        saved, skipped = saver.save_news_batch(news_list)
                        saved_total += saved
                        skipped_total += skipped
                        logger.info(f"   ✅ 매일경제: {saved}건 저장, {skipped}건 스킵")
                    else:
                        logger.warning("   ⚠️  매일경제: 뉴스 없음")
            except Exception as e:
                self.total_errors += 1
                logger.error(f"   ❌ 매일경제 크롤링 실패: {e}")

            # 통계 업데이트
            self.total_crawls += 1
            self.total_saved += saved_total
            self.total_skipped += skipped_total

            # 성공률 계산
            success_rate = (
                (self.total_crawls - self.total_errors) / self.total_crawls * 100
                if self.total_crawls > 0
                else 0
            )

            logger.info("=" * 60)
            logger.info(f"✅ 크롤링 완료: {saved_total}건 저장, {skipped_total}건 스킵")
            logger.info(
                f"📊 전체 통계: 실행 {self.total_crawls}회, "
                f"저장 {self.total_saved}건, "
                f"스킵 {self.total_skipped}건, "
                f"에러 {self.total_errors}회, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            self.total_errors += 1
            logger.error(f"❌ 크롤링 중 예상치 못한 에러: {e}")

        finally:
            db.close()

    def start(self) -> None:
        """스케줄러를 시작합니다."""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        logger.info(f"🚀 크롤러 스케줄러 시작 (간격: {self.interval_minutes}분)")

        self.scheduler = BackgroundScheduler()

        # IntervalTrigger 설정 (10분 간격)
        trigger = IntervalTrigger(minutes=self.interval_minutes)

        # 크롤링 작업 등록
        self.scheduler.add_job(
            func=self._crawl_all_sources,
            trigger=trigger,
            id="news_crawler_job",
            name="뉴스 크롤러",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ 스케줄러 시작 완료")

        # 즉시 한 번 실행
        logger.info("🔄 초기 크롤링 실행...")
        self._crawl_all_sources()

    def shutdown(self) -> None:
        """스케줄러를 종료합니다."""
        if not self.is_running:
            logger.warning("스케줄러가 실행되지 않았습니다")
            return

        logger.info("🛑 크롤러 스케줄러 종료 중...")

        if self.scheduler:
            self.scheduler.shutdown(wait=False)

        self.is_running = False
        logger.info("✅ 스케줄러 종료 완료")

    def get_stats(self) -> dict:
        """
        크롤링 통계를 반환합니다.

        Returns:
            통계 딕셔너리
        """
        success_rate = (
            (self.total_crawls - self.total_errors) / self.total_crawls * 100
            if self.total_crawls > 0
            else 0
        )

        return {
            "total_crawls": self.total_crawls,
            "total_saved": self.total_saved,
            "total_skipped": self.total_skipped,
            "total_errors": self.total_errors,
            "success_rate": round(success_rate, 2),
            "is_running": self.is_running,
        }


# 싱글톤 인스턴스
_crawler_scheduler: Optional[CrawlerScheduler] = None


def get_crawler_scheduler(interval_minutes: int = 10) -> CrawlerScheduler:
    """
    CrawlerScheduler 싱글톤 인스턴스를 반환합니다.

    Args:
        interval_minutes: 크롤링 실행 간격

    Returns:
        CrawlerScheduler 인스턴스
    """
    global _crawler_scheduler
    if _crawler_scheduler is None:
        _crawler_scheduler = CrawlerScheduler(interval_minutes)
    return _crawler_scheduler
