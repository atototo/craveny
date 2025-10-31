"""
크롤러 스케줄러

APScheduler를 사용하여 주기적으로 뉴스 및 주가 데이터를 크롤링합니다.
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from backend.crawlers.naver_crawler import NaverNewsCrawler
from backend.crawlers.hankyung_crawler import HankyungNewsCrawler
from backend.crawlers.maeil_crawler import MaeilNewsCrawler
from backend.crawlers.news_saver import NewsSaver
from backend.crawlers.stock_crawler import get_stock_crawler
from backend.crawlers.news_stock_matcher import run_daily_matching
from backend.utils.market_time import is_market_open
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class CrawlerScheduler:
    """크롤러 스케줄러 클래스"""

    def __init__(
        self, news_interval_minutes: int = 10, stock_interval_minutes: int = 1
    ):
        """
        Args:
            news_interval_minutes: 뉴스 크롤링 실행 간격 (분 단위)
            stock_interval_minutes: 주가 수집 실행 간격 (분 단위)
        """
        self.news_interval_minutes = news_interval_minutes
        self.stock_interval_minutes = stock_interval_minutes
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False

        # 뉴스 크롤링 통계
        self.news_total_crawls = 0
        self.news_total_saved = 0
        self.news_total_skipped = 0
        self.news_total_errors = 0

        # 주가 수집 통계
        self.stock_total_crawls = 0
        self.stock_total_stocks = 0
        self.stock_total_saved = 0
        self.stock_total_errors = 0

        # 뉴스-주가 매칭 통계
        self.matching_total_runs = 0
        self.matching_total_success = 0
        self.matching_total_fail = 0

    def _crawl_all_sources(self) -> None:
        """
        모든 언론사에서 뉴스를 크롤링하고 저장합니다.
        """
        logger.info("=" * 60)
        logger.info(f"🔄 뉴스 크롤링 시작 (#{self.news_total_crawls + 1})")
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
                self.news_total_errors += 1
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
                self.news_total_errors += 1
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
                self.news_total_errors += 1
                logger.error(f"   ❌ 매일경제 크롤링 실패: {e}")

            # 통계 업데이트
            self.news_total_crawls += 1
            self.news_total_saved += saved_total
            self.news_total_skipped += skipped_total

            # 성공률 계산
            success_rate = (
                (self.news_total_crawls - self.news_total_errors) / self.news_total_crawls * 100
                if self.news_total_crawls > 0
                else 0
            )

            logger.info("=" * 60)
            logger.info(f"✅ 뉴스 크롤링 완료: {saved_total}건 저장, {skipped_total}건 스킵")
            logger.info(
                f"📊 뉴스 전체 통계: 실행 {self.news_total_crawls}회, "
                f"저장 {self.news_total_saved}건, "
                f"스킵 {self.news_total_skipped}건, "
                f"에러 {self.news_total_errors}회, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            self.news_total_errors += 1
            logger.error(f"❌ 뉴스 크롤링 중 예상치 못한 에러: {e}")

        finally:
            db.close()

    def _collect_stock_prices(self) -> None:
        """
        주가 데이터를 수집합니다.
        장 시간(09:00~15:30)에만 실행됩니다.
        """
        # 장 시간 체크
        if not is_market_open():
            logger.debug("⏸️  주가 수집 스킵: 장 마감")
            return

        logger.info("=" * 60)
        logger.info(f"📈 주가 수집 시작 (#{self.stock_total_crawls + 1})")
        logger.info("=" * 60)

        try:
            # 주가 수집기 가져오기
            stock_crawler = get_stock_crawler()

            # Priority 1 종목만 수집 (핵심 대형주 10개)
            results = stock_crawler.collect_all_stocks(priority=1)

            # 통계 계산
            total_saved = sum(results.values())
            success_count = sum(1 for count in results.values() if count > 0)
            total_stocks = len(results)

            # 통계 업데이트
            self.stock_total_crawls += 1
            self.stock_total_stocks += total_stocks
            self.stock_total_saved += total_saved

            # 실패한 종목 수
            failed_count = total_stocks - success_count
            if failed_count > 0:
                self.stock_total_errors += failed_count

            # 성공률 계산
            success_rate = (success_count / total_stocks * 100) if total_stocks > 0 else 0

            logger.info("=" * 60)
            logger.info(
                f"✅ 주가 수집 완료: {success_count}/{total_stocks}개 종목, "
                f"총 {total_saved}건 저장"
            )
            logger.info(
                f"📊 주가 전체 통계: 실행 {self.stock_total_crawls}회, "
                f"처리 {self.stock_total_stocks}개 종목, "
                f"저장 {self.stock_total_saved}건, "
                f"에러 {self.stock_total_errors}회, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            self.stock_total_errors += 1
            logger.error(f"❌ 주가 수집 중 예상치 못한 에러: {e}")

    def _match_news_with_stocks(self) -> None:
        """
        뉴스-주가 매칭 작업을 실행합니다.
        매일 장 마감 후(15:40)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info(f"🔗 뉴스-주가 매칭 시작 (#{self.matching_total_runs + 1})")
        logger.info("=" * 60)

        db = SessionLocal()

        try:
            # 일일 매칭 실행 (최근 7일 뉴스 대상)
            success_count, fail_count = run_daily_matching(db, lookback_days=7)

            # 통계 업데이트
            self.matching_total_runs += 1
            self.matching_total_success += success_count
            self.matching_total_fail += fail_count

            # 성공률 계산
            total_attempts = self.matching_total_success + self.matching_total_fail
            success_rate = (
                (self.matching_total_success / total_attempts * 100) if total_attempts > 0 else 0
            )

            logger.info("=" * 60)
            logger.info(f"✅ 뉴스-주가 매칭 완료: 성공 {success_count}건, 실패 {fail_count}건")
            logger.info(
                f"📊 매칭 전체 통계: 실행 {self.matching_total_runs}회, "
                f"성공 {self.matching_total_success}건, "
                f"실패 {self.matching_total_fail}건, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 뉴스-주가 매칭 중 예상치 못한 에러: {e}")

        finally:
            db.close()

    def start(self) -> None:
        """스케줄러를 시작합니다."""
        if self.is_running:
            logger.warning("스케줄러가 이미 실행 중입니다")
            return

        logger.info(
            f"🚀 크롤러 스케줄러 시작 "
            f"(뉴스: {self.news_interval_minutes}분, 주가: {self.stock_interval_minutes}분)"
        )

        self.scheduler = BackgroundScheduler()

        # 뉴스 크롤링 작업 등록 (10분 간격)
        news_trigger = IntervalTrigger(minutes=self.news_interval_minutes)
        self.scheduler.add_job(
            func=self._crawl_all_sources,
            trigger=news_trigger,
            id="news_crawler_job",
            name="뉴스 크롤러",
            replace_existing=True,
        )

        # 주가 수집 작업 등록 (1분 간격)
        stock_trigger = IntervalTrigger(minutes=self.stock_interval_minutes)
        self.scheduler.add_job(
            func=self._collect_stock_prices,
            trigger=stock_trigger,
            id="stock_collector_job",
            name="주가 수집기",
            replace_existing=True,
        )

        # 뉴스-주가 매칭 작업 등록 (매일 15:40)
        matching_trigger = CronTrigger(hour=15, minute=40)
        self.scheduler.add_job(
            func=self._match_news_with_stocks,
            trigger=matching_trigger,
            id="news_stock_matching_job",
            name="뉴스-주가 매칭",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ 스케줄러 시작 완료")

        # 즉시 한 번 실행
        logger.info("🔄 초기 뉴스 크롤링 실행...")
        self._crawl_all_sources()

        # 장 시간이면 주가 수집도 즉시 실행
        if is_market_open():
            logger.info("🔄 초기 주가 수집 실행...")
            self._collect_stock_prices()
        else:
            logger.info("⏸️  장 마감 시간 - 주가 수집 대기 중")

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
            통계 딕셔너리 (뉴스, 주가, 매칭 통계)
        """
        # 뉴스 성공률
        news_success_rate = (
            (self.news_total_crawls - self.news_total_errors) / self.news_total_crawls * 100
            if self.news_total_crawls > 0
            else 0
        )

        # 주가 성공률
        stock_success_rate = (
            (self.stock_total_crawls - self.stock_total_errors) / self.stock_total_crawls * 100
            if self.stock_total_crawls > 0
            else 0
        )

        # 매칭 성공률
        total_matching_attempts = self.matching_total_success + self.matching_total_fail
        matching_success_rate = (
            (self.matching_total_success / total_matching_attempts * 100)
            if total_matching_attempts > 0
            else 0
        )

        return {
            "news": {
                "total_crawls": self.news_total_crawls,
                "total_saved": self.news_total_saved,
                "total_skipped": self.news_total_skipped,
                "total_errors": self.news_total_errors,
                "success_rate": round(news_success_rate, 2),
            },
            "stock": {
                "total_crawls": self.stock_total_crawls,
                "total_stocks": self.stock_total_stocks,
                "total_saved": self.stock_total_saved,
                "total_errors": self.stock_total_errors,
                "success_rate": round(stock_success_rate, 2),
            },
            "matching": {
                "total_runs": self.matching_total_runs,
                "total_success": self.matching_total_success,
                "total_fail": self.matching_total_fail,
                "success_rate": round(matching_success_rate, 2),
            },
            "is_running": self.is_running,
        }


# 싱글톤 인스턴스
_crawler_scheduler: Optional[CrawlerScheduler] = None


def get_crawler_scheduler(
    news_interval_minutes: int = 10, stock_interval_minutes: int = 1
) -> CrawlerScheduler:
    """
    CrawlerScheduler 싱글톤 인스턴스를 반환합니다.

    Args:
        news_interval_minutes: 뉴스 크롤링 실행 간격 (분)
        stock_interval_minutes: 주가 수집 실행 간격 (분)

    Returns:
        CrawlerScheduler 인스턴스
    """
    global _crawler_scheduler
    if _crawler_scheduler is None:
        _crawler_scheduler = CrawlerScheduler(news_interval_minutes, stock_interval_minutes)
    return _crawler_scheduler
