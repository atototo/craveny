"""
크롤러 스케줄러

APScheduler를 사용하여 주기적으로 뉴스 및 주가 데이터를 크롤링합니다.
"""
import logging
import asyncio
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
from backend.crawlers.kis_daily_crawler import get_kis_daily_crawler
from backend.crawlers.kis_minute_collector import run_minute_collector
from backend.crawlers.kis_market_data_collector import (
    OrderbookCollector,
    CurrentPriceCollector,
    InvestorTradingCollector,
    StockInfoCollector,
    SectorIndexCollector,
)
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

        # 모델 평가 통계
        self.evaluation_total_runs = 0
        self.evaluation_total_reports = 0
        self.evaluation_total_success = 0
        self.evaluation_total_failed = 0

        # KIS 일봉 수집 통계
        self.kis_daily_total_runs = 0
        self.kis_daily_total_stocks = 0
        self.kis_daily_total_saved = 0
        self.kis_daily_total_errors = 0

        # KIS 1분봉 수집 통계
        self.kis_minute_total_runs = 0
        self.kis_minute_total_stocks = 0
        self.kis_minute_total_saved = 0
        self.kis_minute_total_errors = 0

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

    # FDR 주가 수집 제거 - KIS API로 전환 완료
    # _collect_stock_prices() 메서드는 더 이상 사용하지 않음

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

    async def _collect_kis_daily_prices(self) -> None:
        """
        KIS API로 일봉 데이터를 수집합니다.
        매일 장 마감 후(15:40)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info(f"📈 KIS 일봉 데이터 수집 시작 (#{self.kis_daily_total_runs + 1})")
        logger.info("=" * 60)

        try:
            # KIS 일봉 수집기 가져오기
            crawler = get_kis_daily_crawler()

            # 과거 30일 데이터 수집
            summary = await crawler.collect_all_stocks(days=30, batch_size=10)

            # 통계 업데이트
            self.kis_daily_total_runs += 1
            self.kis_daily_total_stocks += summary["total_stocks"]
            self.kis_daily_total_saved += summary["total_saved"]
            self.kis_daily_total_errors += summary["failed_count"]

            # 성공률 계산
            success_rate = summary["success_rate"]

            logger.info("=" * 60)
            logger.info(
                f"✅ KIS 일봉 수집 완료: {summary['success_count']}/{summary['total_stocks']}개 종목, "
                f"총 {summary['total_saved']}건 저장"
            )
            logger.info(
                f"📊 KIS 일봉 전체 통계: 실행 {self.kis_daily_total_runs}회, "
                f"처리 {self.kis_daily_total_stocks}개 종목, "
                f"저장 {self.kis_daily_total_saved}건, "
                f"에러 {self.kis_daily_total_errors}회, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            self.kis_daily_total_errors += 1
            logger.error(f"❌ KIS 일봉 수집 중 예상치 못한 에러: {e}")

    async def _collect_index_daily(self) -> None:
        """
        KIS API로 업종/지수 일자별 데이터를 수집합니다.
        매일 장 마감 후(18:00)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info("📊 KIS 업종/지수 일자별 데이터 수집 시작")
        logger.info("=" * 60)

        try:
            from backend.crawlers.index_daily_collector import IndexDailyCollector

            collector = IndexDailyCollector(batch_size=5)
            result = await collector.collect_today()

            logger.info("=" * 60)
            logger.info(
                f"✅ 업종/지수 수집 완료: 성공 {result['collected']}건, 실패 {result['failed']}건"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 업종/지수 수집 중 예상치 못한 에러: {e}", exc_info=True)

    async def _collect_kis_minute_prices(self) -> None:
        """
        KIS API로 1분봉 데이터를 수집합니다.
        장 시간(09:00~15:30)에만 실행됩니다.
        """
        # 장 시간 체크
        if not is_market_open():
            logger.debug("⏸️  1분봉 수집 스킵: 장 마감")
            return

        logger.info("=" * 60)
        logger.info(f"📊 KIS 1분봉 데이터 수집 시작 (#{self.kis_minute_total_runs + 1})")
        logger.info("=" * 60)

        try:
            # 1분봉 수집기 실행
            await run_minute_collector()

            # 통계 업데이트
            self.kis_minute_total_runs += 1

            logger.info("=" * 60)
            logger.info("✅ KIS 1분봉 수집 완료")
            logger.info(
                f"📊 KIS 1분봉 전체 통계: 실행 {self.kis_minute_total_runs}회"
            )
            logger.info("=" * 60)

        except Exception as e:
            self.kis_minute_total_errors += 1
            logger.error(f"❌ KIS 1분봉 수집 중 예상치 못한 에러: {e}")

    async def _collect_market_data(self) -> None:
        """
        KIS API로 시장 데이터 수집 (호가, 현재가, 종목정보, 업종지수).
        장 시간(09:00~15:30)에만 실행됩니다.
        """
        # 장 시간 체크
        if not is_market_open():
            logger.debug("⏸️  시장 데이터 수집 스킵: 장 마감")
            return

        logger.info("=" * 60)
        logger.info("📊 KIS 시장 데이터 수집 시작")
        logger.info("=" * 60)

        try:
            # 호가 데이터 수집
            logger.info("📈 호가 데이터 수집 시작...")
            orderbook_collector = OrderbookCollector(batch_size=10)
            await orderbook_collector.collect_all()

            # 현재가 데이터 수집
            logger.info("💰 현재가 데이터 수집 시작...")
            current_price_collector = CurrentPriceCollector(batch_size=10)
            await current_price_collector.collect_all()

            # 업종 지수 수집
            logger.info("📊 업종 지수 수집 시작...")
            sector_index_collector = SectorIndexCollector()
            await sector_index_collector.collect_all()

            logger.info("=" * 60)
            logger.info("✅ 시장 데이터 수집 완료")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 시장 데이터 수집 중 에러: {e}")

    async def _collect_investor_trading(self) -> None:
        """
        투자자별 매매동향 데이터 수집.
        매일 장 마감 후(16:00)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info("💼 투자자별 매매동향 수집 시작")
        logger.info("=" * 60)

        try:
            # 최근 30일 데이터 수집
            collector = InvestorTradingCollector(batch_size=5)
            await collector.collect_all(days=30)

            logger.info("=" * 60)
            logger.info("✅ 투자자별 매매동향 수집 완료")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 투자자별 매매동향 수집 중 에러: {e}")

    async def _collect_stock_info(self) -> None:
        """
        종목 기본정보 수집.
        매일 장 마감 후(16:10)에 실행됩니다.
        """
        logger.info("=" * 60)
        logger.info("ℹ️  종목 기본정보 수집 시작")
        logger.info("=" * 60)

        try:
            collector = StockInfoCollector(batch_size=10)
            await collector.collect_all()

            logger.info("=" * 60)
            logger.info("✅ 종목 기본정보 수집 완료")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 종목 기본정보 수집 중 에러: {e}")

    async def _collect_overtime_prices(self) -> None:
        """
        시간외 거래 가격 수집.
        매일 저녁 18:00에 실행됩니다 (시간외 거래 종료 후).
        """
        logger.info("=" * 60)
        logger.info("🌙 시간외 거래 가격 수집 시작")
        logger.info("=" * 60)

        try:
            from backend.crawlers.kis_market_data_collector import OvertimePriceCollector

            collector = OvertimePriceCollector(batch_size=10)
            await collector.collect_all()

            logger.info("=" * 60)
            logger.info("✅ 시간외 거래 가격 수집 완료")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 시간외 거래 가격 수집 중 에러: {e}")

    async def _generate_stock_reports(self) -> None:
        """
        종목별 투자 리포트 생성.
        하루 3번 실행됩니다 (09:15, 13:00, 15:40).
        Priority 1-2 종목만 대상.
        """
        logger.info("=" * 60)
        logger.info("📝 종목별 투자 리포트 생성 시작")
        logger.info("=" * 60)

        db = SessionLocal()

        try:
            from backend.services.stock_analysis_service import update_stock_analysis_summary

            # Priority 1-2 종목만 조회
            priority_stocks = db.query(Stock).filter(
                Stock.is_active == True,
                Stock.priority <= 2
            ).all()

            logger.info(f"📊 리포트 생성 대상: {len(priority_stocks)}개 종목 (Priority 1-2)")

            success_count = 0
            failed_count = 0

            for stock in priority_stocks:
                try:
                    # 리포트 생성 (force_update=True로 항상 새로 생성)
                    report = await update_stock_analysis_summary(
                        stock_code=stock.code,
                        db=db,
                        force_update=True
                    )

                    if report:
                        success_count += 1
                        logger.info(
                            f"  ✅ {stock.name} ({stock.code}): "
                            f"기준가 {report.base_price:,.0f}원, "
                            f"목표가 {report.short_term_target_price:,.0f}원"
                        )
                    else:
                        failed_count += 1
                        logger.warning(f"  ⚠️  {stock.name} ({stock.code}) 리포트 생성 실패")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"  ❌ {stock.name} ({stock.code}) 리포트 생성 에러: {e}")

            logger.info("=" * 60)
            logger.info(f"✅ 리포트 생성 완료: 성공 {success_count}개, 실패 {failed_count}개")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 리포트 생성 중 예상치 못한 에러: {e}")

        finally:
            db.close()

    def _generate_model_evaluations(self) -> None:
        """
        최근 투자 리포트에 대한 모델 평가 생성.
        매일 16:30에 실행됩니다 (리포트 생성 후).
        Priority 1-2 종목만 대상.
        """
        logger.info("=" * 60)
        logger.info(f"🎯 모델 평가 생성 시작 (#{self.evaluation_total_runs + 1})")
        logger.info("=" * 60)

        db = SessionLocal()

        try:
            from backend.services.evaluation_service import EvaluationService
            from backend.db.models.ab_test_config import ABTestConfig
            from backend.db.models.model import Model
            from datetime import datetime

            # 오늘 생성된 리포트 조회
            today = datetime.now()
            start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)

            reports = db.query(StockAnalysisSummary).filter(
                StockAnalysisSummary.last_updated >= start_of_day,
                StockAnalysisSummary.last_updated <= end_of_day,
                StockAnalysisSummary.base_price.isnot(None),
                StockAnalysisSummary.short_term_target_price.isnot(None),
                StockAnalysisSummary.short_term_support_price.isnot(None)
            ).all()

            # Priority 1-2 종목만 필터링
            priority_stocks = db.query(Stock).filter(
                Stock.is_active == True,
                Stock.priority <= 2
            ).all()
            priority_codes = {s.code for s in priority_stocks}

            reports = [r for r in reports if r.stock_code in priority_codes]

            logger.info(f"📊 평가 대상 리포트: {len(reports)}건 (Priority 1-2 종목만)")

            if not reports:
                logger.info("⏭️  평가할 리포트가 없습니다")
                return

            # EvaluationService 초기화
            service = EvaluationService(db)

            success_count = 0
            failed_count = 0

            # A/B 테스트 설정 조회
            ab_config = db.query(ABTestConfig).filter(ABTestConfig.is_active == True).first()

            for report in reports:
                try:
                    # A/B 테스트 리포트인 경우 두 모델 모두 평가
                    if report.custom_data and report.custom_data.get('ab_test_enabled') and ab_config:
                        model_a = db.query(Model).filter(Model.id == ab_config.model_a_id).first()
                        model_b = db.query(Model).filter(Model.id == ab_config.model_b_id).first()

                        # Model A 평가
                        try:
                            eval_a = service.evaluate_report(report, model_id=ab_config.model_a_id)
                            if eval_a:
                                success_count += 1
                                logger.info(
                                    f"  ✅ {report.stock_code} - Model A ({model_a.name}): "
                                    f"score={eval_a.final_score:.1f}"
                                )
                            else:
                                failed_count += 1
                                logger.warning(f"  ⚠️  {report.stock_code} - Model A 평가 실패")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"  ❌ {report.stock_code} - Model A 평가 에러: {e}")

                        # Model B 평가
                        try:
                            eval_b = service.evaluate_report(report, model_id=ab_config.model_b_id)
                            if eval_b:
                                success_count += 1
                                logger.info(
                                    f"  ✅ {report.stock_code} - Model B ({model_b.name}): "
                                    f"score={eval_b.final_score:.1f}"
                                )
                            else:
                                failed_count += 1
                                logger.warning(f"  ⚠️  {report.stock_code} - Model B 평가 실패")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"  ❌ {report.stock_code} - Model B 평가 에러: {e}")
                    else:
                        # 일반 리포트 (단일 모델)
                        try:
                            evaluation = service.evaluate_report(report, model_id=1)
                            if evaluation:
                                success_count += 1
                                logger.info(
                                    f"  ✅ {report.stock_code}: score={evaluation.final_score:.1f}"
                                )
                            else:
                                failed_count += 1
                                logger.warning(f"  ⚠️  {report.stock_code} 평가 실패")
                        except Exception as e:
                            failed_count += 1
                            logger.error(f"  ❌ {report.stock_code} 평가 에러: {e}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"  ❌ {report.stock_code} 평가 중 에러: {e}")

            # 통계 업데이트
            self.evaluation_total_runs += 1
            self.evaluation_total_reports += len(reports)
            self.evaluation_total_success += success_count
            self.evaluation_total_failed += failed_count

            # 성공률 계산
            total_attempts = self.evaluation_total_success + self.evaluation_total_failed
            success_rate = (
                (self.evaluation_total_success / total_attempts * 100)
                if total_attempts > 0
                else 0
            )

            logger.info("=" * 60)
            logger.info(f"✅ 모델 평가 생성 완료: 성공 {success_count}건, 실패 {failed_count}건")
            logger.info(
                f"📊 평가 전체 통계: 실행 {self.evaluation_total_runs}회, "
                f"리포트 {self.evaluation_total_reports}건, "
                f"성공 {self.evaluation_total_success}건, "
                f"실패 {self.evaluation_total_failed}건, "
                f"성공률 {success_rate:.1f}%"
            )
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 모델 평가 생성 중 예상치 못한 에러: {e}")

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

        # FDR 주가 수집 제거 - KIS API로 전환 완료

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

        # KIS 업종/지수 일자별 수집 작업 등록 (매일 18:00 - 시간외 거래 마감 후)
        index_daily_trigger = CronTrigger(hour=18, minute=0)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_index_daily()),
            trigger=index_daily_trigger,
            id="kis_index_daily_job",
            name="KIS 업종/지수 일자별 수집기",
            replace_existing=True,
        )

        # KIS 일봉 수집 작업 등록 (매일 15:40 - 장 마감 후)
        kis_daily_trigger = CronTrigger(hour=15, minute=40)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_kis_daily_prices()),
            trigger=kis_daily_trigger,
            id="kis_daily_collector_job",
            name="KIS 일봉 수집기",
            replace_existing=True,
        )

        # KIS 1분봉 수집 작업 등록 (매 1분 - 장 시간만)
        kis_minute_trigger = IntervalTrigger(minutes=1)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_kis_minute_prices()),
            trigger=kis_minute_trigger,
            id="kis_minute_collector_job",
            name="KIS 1분봉 수집기",
            replace_existing=True,
        )

        # KIS 시장 데이터 수집 작업 등록 (매 5분 - 장 시간만)
        market_data_trigger = IntervalTrigger(minutes=5)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_market_data()),
            trigger=market_data_trigger,
            id="kis_market_data_job",
            name="KIS 시장 데이터 수집",
            replace_existing=True,
        )

        # 투자자별 매매동향 수집 (매일 16:00 - 장 마감 후)
        investor_trading_trigger = CronTrigger(hour=16, minute=0)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_investor_trading()),
            trigger=investor_trading_trigger,
            id="investor_trading_job",
            name="투자자별 매매동향 수집",
            replace_existing=True,
        )

        # 종목 기본정보 수집 (매일 16:10 - 장 마감 후)
        stock_info_trigger = CronTrigger(hour=16, minute=10)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_stock_info()),
            trigger=stock_info_trigger,
            id="stock_info_job",
            name="종목 기본정보 수집",
            replace_existing=True,
        )

        # 시간외 거래 가격 수집 (매일 18:00 - 시간외 거래 종료 후)
        overtime_trigger = CronTrigger(hour=18, minute=0)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._collect_overtime_prices()),
            trigger=overtime_trigger,
            id="overtime_price_job",
            name="시간외 거래 가격 수집",
            replace_existing=True,
        )

        # 리포트 생성 (하루 3번 - 장 시작 후, 점심 후, 장 마감 후)
        # 장 시작 후 (09:15)
        report_morning_trigger = CronTrigger(hour=9, minute=15)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._generate_stock_reports()),
            trigger=report_morning_trigger,
            id="stock_report_morning_job",
            name="투자 리포트 생성 (장초)",
            replace_existing=True,
        )

        # 점심 시간 후 (13:00)
        report_lunch_trigger = CronTrigger(hour=13, minute=0)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._generate_stock_reports()),
            trigger=report_lunch_trigger,
            id="stock_report_lunch_job",
            name="투자 리포트 생성 (장중)",
            replace_existing=True,
        )

        # 장 마감 후 (15:40)
        report_close_trigger = CronTrigger(hour=15, minute=40)
        self.scheduler.add_job(
            func=lambda: asyncio.run(self._generate_stock_reports()),
            trigger=report_close_trigger,
            id="stock_report_close_job",
            name="투자 리포트 생성 (장마감)",
            replace_existing=True,
        )

        # 모델 평가 생성 (매일 16:30 - 리포트 생성 후)
        evaluation_trigger = CronTrigger(hour=16, minute=30)
        self.scheduler.add_job(
            func=self._generate_model_evaluations,
            trigger=evaluation_trigger,
            id="model_evaluation_job",
            name="모델 평가 생성",
            replace_existing=True,
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ 스케줄러 시작 완료")
        logger.info("⏰ 크롤러들이 스케줄에 따라 자동 실행됩니다")
        logger.info("   - 최신 뉴스: 10분마다")
        logger.info("   - 종목별 검색: 10분마다")
        logger.info("   - DART 공시: 5분마다")
        logger.info("   - 투자 리포트: 매일 09:15 (장초), 13:00 (장중), 15:40 (장마감)")
        logger.info("   - KIS 일봉 수집: 매일 15:40 (장 마감 후)")
        logger.info("   - KIS 1분봉 수집: 매 1분 (장 시간만)")
        logger.info("   - KIS 시장 데이터: 매 5분 (호가, 현재가, 업종지수 - 장 시간만)")
        logger.info("   - 투자자별 매매동향: 매일 16:00 (장 마감 후)")
        logger.info("   - 종목 기본정보: 매일 16:10 (장 마감 후)")
        logger.info("   - 모델 평가 생성: 매일 16:30 (리포트 생성 후)")
        logger.info("   - 시간외 거래 가격: 매일 18:00 (시간외 거래 종료 후)")
        logger.info("   - KIS 업종/지수 일자별: 매일 18:00 (시간외 거래 종료 후)")

        # 초기 실행은 선택사항 (환경 변수로 제어)
        # 첫 스케줄까지 기다리는 것이 서버 시작을 빠르게 합니다
        import os
        if os.getenv("RUN_INITIAL_CRAWL", "false").lower() == "true":
            logger.info("🔄 초기 크롤링 실행...")
            self._crawl_all_sources()
            self._crawl_stock_specific_news()
            self._crawl_dart_disclosures()
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

        # KIS 일봉 성공률
        kis_daily_success_rate = (
            (self.kis_daily_total_runs - self.kis_daily_total_errors) / self.kis_daily_total_runs * 100
            if self.kis_daily_total_runs > 0
            else 0
        )

        # KIS 1분봉 성공률
        kis_minute_success_rate = (
            (self.kis_minute_total_runs - self.kis_minute_total_errors) / self.kis_minute_total_runs * 100
            if self.kis_minute_total_runs > 0
            else 0
        )

        # 모델 평가 성공률
        evaluation_success_rate = (
            (self.evaluation_total_success / (self.evaluation_total_success + self.evaluation_total_failed) * 100)
            if (self.evaluation_total_success + self.evaluation_total_failed) > 0
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
            "evaluation": {
                "total_runs": self.evaluation_total_runs,
                "total_reports": self.evaluation_total_reports,
                "total_success": self.evaluation_total_success,
                "total_failed": self.evaluation_total_failed,
                "success_rate": round(evaluation_success_rate, 2),
            },
            "kis_daily": {
                "total_runs": self.kis_daily_total_runs,
                "total_stocks": self.kis_daily_total_stocks,
                "total_saved": self.kis_daily_total_saved,
                "total_errors": self.kis_daily_total_errors,
                "success_rate": round(kis_daily_success_rate, 2),
            },
            "kis_minute": {
                "total_runs": self.kis_minute_total_runs,
                "total_stocks": self.kis_minute_total_stocks,
                "total_saved": self.kis_minute_total_saved,
                "total_errors": self.kis_minute_total_errors,
                "success_rate": round(kis_minute_success_rate, 2),
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
