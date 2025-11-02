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
from backend.crawlers.naver_search_crawler import NaverNewsSearchCrawler
from backend.crawlers.dart_crawler import DartCrawler
from backend.crawlers.news_saver import NewsSaver
from backend.crawlers.stock_crawler import get_stock_crawler
from backend.crawlers.news_stock_matcher import run_daily_matching
from backend.llm.embedder import run_daily_embedding
from backend.utils.market_time import is_market_open
from backend.db.session import SessionLocal
from backend.db.models.stock import Stock
from backend.notifications.auto_notify import process_new_news_notifications


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

        # 뉴스 임베딩 통계
        self.embedding_total_runs = 0
        self.embedding_total_success = 0
        self.embedding_total_fail = 0

        # 자동 알림 통계
        self.notify_total_runs = 0
        self.notify_total_processed = 0
        self.notify_total_success = 0
        self.notify_total_failed = 0

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

    def _crawl_stock_specific_news(self) -> None:
        """
        종목별로 뉴스를 검색하여 수집합니다.
        우선순위에 따라 수집량 차등 적용.
        """
        logger.info("=" * 60)
        logger.info("🎯 종목별 뉴스 검색 시작")
        logger.info("=" * 60)

        db = SessionLocal()
        saver = NewsSaver(db)
        search_crawler = NaverNewsSearchCrawler()

        saved_total = 0
        skipped_total = 0

        try:
            # DB에서 활성화된 종목 가져오기
            stocks = db.query(Stock).filter(Stock.is_active == True).order_by(Stock.priority).all()

            logger.info(f"📊 검색 대상 종목: {len(stocks)}개")

            for stock in stocks:
                try:
                    # 우선순위별 수집량 결정
                    if stock.priority <= 2:
                        limit = 10  # 높은 우선순위
                    elif stock.priority == 3:
                        limit = 5   # 중간 우선순위
                    else:
                        limit = 3   # 낮은 우선순위

                    logger.info(f"🔍 {stock.name} ({stock.code}) 검색 중... (최대 {limit}건)")

                    # 종목명으로 뉴스 검색
                    # NAVER는 한글로 검색 (영문 "NAVER"로 검색하면 출처 "네이버"가 모두 검색됨)
                    search_query = "네이버" if stock.name == "NAVER" else stock.name

                    news_list = search_crawler.search_news(
                        query=search_query,
                        max_pages=1,
                        max_results=limit
                    )

                    if news_list:
                        # 뉴스에 종목코드 명시적 설정
                        for news in news_list:
                            news.company_name = stock.name
                            # stock_code는 news_saver에서 자동 매칭되지만 명시적으로 설정 가능

                        saved, skipped = saver.save_news_batch(news_list)
                        saved_total += saved
                        skipped_total += skipped

                        if saved > 0:
                            logger.info(f"   ✅ {saved}건 저장, {skipped}건 스킵")
                        else:
                            logger.debug(f"   ⏭️  전부 중복 ({skipped}건)")
                    else:
                        logger.debug(f"   ℹ️  검색 결과 없음")

                except Exception as e:
                    logger.error(f"   ❌ {stock.name} 검색 실패: {e}")

            logger.info("=" * 60)
            logger.info(f"✅ 종목별 검색 완료: {saved_total}건 저장, {skipped_total}건 스킵")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 종목별 검색 중 오류: {e}", exc_info=True)

        finally:
            db.close()

    def _crawl_dart_disclosures(self) -> None:
        """
        DART 공시 정보를 수집합니다.
        Priority 1-2 종목만 대상 (중요 종목만)
        """
        logger.info("=" * 60)
        logger.info("📋 DART 공시 수집 시작")
        logger.info("=" * 60)

        db = SessionLocal()
        saver = NewsSaver(db)
        dart_crawler = DartCrawler()

        # DART API 키가 없으면 스킵
        if not dart_crawler.api_key:
            logger.warning("⚠️  DART API 키가 없어 공시 수집을 건너뜁니다")
            logger.info("   API 키 발급: https://opendart.fss.or.kr/")
            db.close()
            return

        saved_total = 0
        skipped_total = 0

        try:
            # Priority 1-2 종목만 공시 수집 (중요 종목)
            stocks = db.query(Stock).filter(
                Stock.is_active == True,
                Stock.priority <= 2
            ).all()

            logger.info(f"📊 공시 수집 대상: {len(stocks)}개 (Priority 1-2만)")

            for stock in stocks:
                try:
                    logger.info(f"📋 {stock.name} ({stock.code}) 공시 검색 중...")

                    # 최근 3일간 공시 검색
                    from datetime import datetime, timedelta
                    disclosures = dart_crawler.fetch_disclosures_by_stock_code(
                        stock_code=stock.code,
                        start_date=datetime.now() - timedelta(days=3),
                        end_date=datetime.now(),
                    )

                    if disclosures:
                        # 공시에 종목 정보 설정
                        for disclosure in disclosures:
                            disclosure.company_name = stock.name

                        saved, skipped = saver.save_news_batch(disclosures)
                        saved_total += saved
                        skipped_total += skipped

                        if saved > 0:
                            logger.info(f"   ✅ {saved}건 저장, {skipped}건 스킵")
                        else:
                            logger.debug(f"   ⏭️  전부 중복 ({skipped}건)")
                    else:
                        logger.debug(f"   ℹ️  공시 없음")

                except Exception as e:
                    logger.error(f"   ❌ {stock.name} 공시 수집 실패: {e}")

            logger.info("=" * 60)
            logger.info(f"✅ DART 공시 수집 완료: {saved_total}건 저장, {skipped_total}건 스킵")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ DART 공시 수집 중 오류: {e}", exc_info=True)

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

    def _embed_news(self) -> None:
        """
        뉴스 임베딩 작업을 실행합니다.
        매일 장 마감 후(16:00)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info(f"🔤 뉴스 임베딩 시작 (#{self.embedding_total_runs + 1})")
        logger.info("=" * 60)

        try:
            # 일일 임베딩 실행 (배치 100건)
            success_count, fail_count = run_daily_embedding(batch_size=100)

            # 통계 업데이트
            self.embedding_total_runs += 1
            self.embedding_total_success += success_count
            self.embedding_total_fail += fail_count

            # 성공률 계산
            total_attempts = self.embedding_total_success + self.embedding_total_fail
            success_rate = (
                (self.embedding_total_success / total_attempts * 100)
                if total_attempts > 0
                else 0
            )

            logger.info("=" * 60)
            logger.info(f"✅ 뉴스 임베딩 완료: 성공 {success_count}건, 실패 {fail_count}건")
            logger.info(
                f"📊 임베딩 전체 통계: 실행 {self.embedding_total_runs}회, "
                f"성공 {self.embedding_total_success}건, "
                f"실패 {self.embedding_total_fail}건, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 뉴스 임베딩 중 예상치 못한 에러: {e}")

    def _auto_notify(self) -> None:
        """
        최근 뉴스에 대해 자동으로 예측을 수행하고 텔레그램 알림을 전송합니다.
        뉴스 크롤링 직후에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info(f"🔔 자동 알림 시작 (#{self.notify_total_runs + 1})")
        logger.info("=" * 60)

        db = SessionLocal()

        try:
            # 최근 15분 이내 뉴스 처리
            stats = process_new_news_notifications(db, lookback_minutes=15)

            # 통계 업데이트
            self.notify_total_runs += 1
            self.notify_total_processed += stats["processed"]
            self.notify_total_success += stats["success"]
            self.notify_total_failed += stats["failed"]

            # 성공률 계산
            total_attempts = self.notify_total_success + self.notify_total_failed
            success_rate = (
                (self.notify_total_success / total_attempts * 100)
                if total_attempts > 0
                else 0
            )

            logger.info("=" * 60)
            logger.info(
                f"✅ 자동 알림 완료: 처리 {stats['processed']}건, "
                f"성공 {stats['success']}건, 실패 {stats['failed']}건"
            )
            logger.info(
                f"📊 알림 전체 통계: 실행 {self.notify_total_runs}회, "
                f"처리 {self.notify_total_processed}건, "
                f"성공 {self.notify_total_success}건, "
                f"실패 {self.notify_total_failed}건, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 자동 알림 중 예상치 못한 에러: {e}")

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

        # 종목별 검색 작업 등록 (10분 간격)
        stock_news_trigger = IntervalTrigger(minutes=self.news_interval_minutes)
        self.scheduler.add_job(
            func=self._crawl_stock_specific_news,
            trigger=stock_news_trigger,
            id="stock_news_search_job",
            name="종목별 뉴스 검색",
            replace_existing=True,
        )

        # DART 공시 크롤링 작업 등록 (5분 간격)
        dart_trigger = IntervalTrigger(minutes=5)
        self.scheduler.add_job(
            func=self._crawl_dart_disclosures,
            trigger=dart_trigger,
            id="dart_disclosure_job",
            name="DART 공시 크롤링",
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

        # 뉴스 임베딩 작업 등록 (매일 16:00)
        embedding_trigger = CronTrigger(hour=16, minute=0)
        self.scheduler.add_job(
            func=self._embed_news,
            trigger=embedding_trigger,
            id="news_embedding_job",
            name="뉴스 임베딩",
            replace_existing=True,
        )

        # 자동 알림 작업 등록 (뉴스 크롤링과 동일한 주기)
        notify_trigger = IntervalTrigger(minutes=self.news_interval_minutes)
        self.scheduler.add_job(
            func=self._auto_notify,
            trigger=notify_trigger,
            id="auto_notify_job",
            name="자동 알림",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ 스케줄러 시작 완료")
        logger.info("⏰ 크롤러들이 스케줄에 따라 자동 실행됩니다")
        logger.info("   - 최신 뉴스: 10분마다")
        logger.info("   - 종목별 검색: 10분마다")
        logger.info("   - DART 공시: 5분마다")
        logger.info("   - 주가 수집: 1분마다 (장 시간)")

        # 초기 실행은 선택사항 (환경 변수로 제어)
        # 첫 스케줄까지 기다리는 것이 서버 시작을 빠르게 합니다
        import os
        if os.getenv("RUN_INITIAL_CRAWL", "false").lower() == "true":
            logger.info("🔄 초기 크롤링 실행...")
            self._crawl_all_sources()
            self._crawl_stock_specific_news()
            self._crawl_dart_disclosures()

            if is_market_open():
                self._collect_stock_prices()
        else:
            logger.info("⏭️  초기 크롤링 스킵 - 첫 스케줄까지 대기 중...")

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
            통계 딕셔너리 (뉴스, 주가, 매칭, 임베딩 통계)
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

        # 임베딩 성공률
        total_embedding_attempts = self.embedding_total_success + self.embedding_total_fail
        embedding_success_rate = (
            (self.embedding_total_success / total_embedding_attempts * 100)
            if total_embedding_attempts > 0
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
            "embedding": {
                "total_runs": self.embedding_total_runs,
                "total_success": self.embedding_total_success,
                "total_fail": self.embedding_total_fail,
                "success_rate": round(embedding_success_rate, 2),
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
