"""
Dual-Run 모드 일봉 수집기

FDR과 KIS 데이터를 동시에 수집하여 자동 검증합니다.
환경 변수 DUAL_RUN_MODE=true로 활성화.
"""
import logging
import asyncio
import os
from typing import Dict, Optional, List
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from backend.crawlers.stock_crawler import StockCrawler
from backend.crawlers.kis_daily_crawler import KISDailyCrawler
from backend.validators.kis_validator import get_validator
from backend.db.models.stock import Stock
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class DualRunCollector:
    """
    FDR + KIS 동시 수집 및 자동 검증

    1. FDR 데이터 수집 (source=fdr)
    2. KIS 데이터 수집 (source=kis)
    3. 자동 검증 실행
    4. 검증 결과 로깅
    """

    def __init__(self):
        self.fdr_crawler = StockCrawler(use_db=True)
        self.kis_crawler = KISDailyCrawler()
        self.validator = get_validator()

    async def collect_stock_dual(
        self,
        stock_code: str,
        days: int = 1,
        db: Optional[Session] = None
    ) -> Dict:
        """
        단일 종목 Dual-Run 수집

        Args:
            stock_code: 종목 코드
            days: 수집 기간 (일)
            db: DB 세션

        Returns:
            수집 및 검증 결과
        """
        start_time = datetime.now()

        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Dual-Run: {stock_code}")
        logger.info(f"{'='*60}")

        db_session = db or SessionLocal()
        should_close = db is None

        try:
            # 1. FDR 수집
            logger.info(f"1️⃣  FDR 데이터 수집 중...")
            fdr_start = datetime.now() - timedelta(days=days)
            fdr_df = self.fdr_crawler.fetch_stock_data(stock_code, start_date=fdr_start)

            if fdr_df is not None and not fdr_df.empty:
                fdr_count = self.fdr_crawler.save_stock_data(stock_code, fdr_df, db_session)
                logger.info(f"   ✅ FDR 저장: {fdr_count}건")
            else:
                logger.warning(f"   ⚠️  FDR 데이터 없음")
                fdr_count = 0

            # 2. KIS 수집
            logger.info(f"2️⃣  KIS 데이터 수집 중...")
            kis_result = await self.kis_crawler.collect_stock(
                stock_code,
                days=days,
                db=db_session
            )
            kis_count = kis_result.get("count", 0)
            logger.info(f"   ✅ KIS 저장: {kis_count}건")

            # 3. 자동 검증
            logger.info(f"3️⃣  자동 검증 실행 중...")
            validation_results = self._validate_collected_data(
                stock_code,
                days=days,
                db=db_session
            )

            # 4. 검증 결과 요약
            if validation_results:
                metrics = self.validator.calculate_metrics(validation_results)
                logger.info(f"   📊 검증 결과:")
                logger.info(f"      - 비교 건수: {metrics['total_count']}건")
                logger.info(f"      - 일치율: {metrics['match_rate']:.2f}%")
                logger.info(f"      - 평균 차이: {metrics['avg_diff_close_pct']:.3f}%")
                logger.info(f"      - 이상치: {metrics['anomaly_count']}건")

                # 이상치 상세
                anomalies = [r for r in validation_results if r.is_anomaly]
                if anomalies:
                    logger.warning(f"   ⚠️  이상치 발견:")
                    for a in anomalies[:3]:  # 최대 3건만 출력
                        logger.warning(
                            f"      {a.date}: FDR={a.fdr_close:,.0f}, "
                            f"KIS={a.kis_close:,.0f} (차이 {a.diff_close_pct:.2f}%)"
                        )
            else:
                logger.warning(f"   ⚠️  검증할 데이터 없음")
                metrics = {}

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"{'='*60}")
            logger.info(f"✅ Dual-Run 완료 ({elapsed:.1f}s)\n")

            return {
                "stock_code": stock_code,
                "status": "success",
                "fdr_count": fdr_count,
                "kis_count": kis_count,
                "validation": metrics,
                "elapsed_time": elapsed
            }

        except Exception as e:
            logger.error(f"❌ Dual-Run 실패: {stock_code}, {e}")
            return {
                "stock_code": stock_code,
                "status": "failed",
                "error": str(e)
            }

        finally:
            if should_close:
                db_session.close()

    def _validate_collected_data(
        self,
        stock_code: str,
        days: int,
        db: Session
    ) -> List:
        """
        수집된 데이터 검증

        Args:
            stock_code: 종목 코드
            days: 검증 기간
            db: DB 세션

        Returns:
            검증 결과 리스트
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days + 1)  # 여유분 추가

        results = self.validator.validate_stock(
            stock_code,
            start_date=start_date,
            end_date=end_date
        )

        return results

    async def collect_all_dual(
        self,
        days: int = 1,
        batch_size: int = 10
    ) -> Dict:
        """
        전체 종목 Dual-Run 수집

        Args:
            days: 수집 기간
            batch_size: 배치 크기

        Returns:
            전체 수집 결과
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 Dual-Run 모드 시작 (전체 종목, {days}일)")
        logger.info(f"{'='*80}\n")

        db = SessionLocal()

        try:
            # 활성 종목 조회
            stocks = db.query(Stock).filter(Stock.is_active == True).all()
            stock_codes = [stock.code for stock in stocks]

            logger.info(f"수집 대상: {len(stock_codes)}개 종목\n")

            results = []
            success_count = 0
            total_fdr = 0
            total_kis = 0

            # 배치 처리
            for i in range(0, len(stock_codes), batch_size):
                batch = stock_codes[i:i + batch_size]

                logger.info(f"\n📦 배치 {i//batch_size + 1}: {len(batch)}개 종목")

                # 배치 내 병렬 수집
                tasks = [
                    self.collect_stock_dual(code, days=days, db=db)
                    for code in batch
                ]

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"예외 발생: {result}")
                        continue

                    results.append(result)

                    if result["status"] == "success":
                        success_count += 1
                        total_fdr += result.get("fdr_count", 0)
                        total_kis += result.get("kis_count", 0)

                # Rate limiting
                if i + batch_size < len(stock_codes):
                    await asyncio.sleep(0.5)

            # 전체 결과 요약
            success_rate = (success_count / len(stock_codes)) * 100 if stock_codes else 0

            # 전체 검증 통계
            all_validations = []
            for r in results:
                if r["status"] == "success" and r.get("validation"):
                    all_validations.append(r["validation"])

            if all_validations:
                avg_match_rate = sum(v["match_rate"] for v in all_validations) / len(all_validations)
                avg_diff_pct = sum(v["avg_diff_close_pct"] for v in all_validations) / len(all_validations)
                total_anomalies = sum(v["anomaly_count"] for v in all_validations)
            else:
                avg_match_rate = 0
                avg_diff_pct = 0
                total_anomalies = 0

            summary = {
                "total_stocks": len(stock_codes),
                "success_count": success_count,
                "failed_count": len(stock_codes) - success_count,
                "success_rate": success_rate,
                "total_fdr_saved": total_fdr,
                "total_kis_saved": total_kis,
                "avg_match_rate": avg_match_rate,
                "avg_diff_pct": avg_diff_pct,
                "total_anomalies": total_anomalies,
                "results": results
            }

            logger.info(f"\n{'='*80}")
            logger.info(f"🎉 Dual-Run 전체 완료!")
            logger.info(f"{'='*80}")
            logger.info(f"📊 수집 결과:")
            logger.info(f"   - 전체: {len(stock_codes)}개")
            logger.info(f"   - 성공: {success_count}개 ({success_rate:.1f}%)")
            logger.info(f"   - 실패: {len(stock_codes) - success_count}개")
            logger.info(f"   - FDR 저장: {total_fdr}건")
            logger.info(f"   - KIS 저장: {total_kis}건")
            logger.info(f"\n📊 검증 결과:")
            logger.info(f"   - 평균 일치율: {avg_match_rate:.2f}%")
            logger.info(f"   - 평균 차이: {avg_diff_pct:.3f}%")
            logger.info(f"   - 총 이상치: {total_anomalies}건")
            logger.info(f"{'='*80}\n")

            return summary

        finally:
            db.close()


# 싱글톤
_collector: Optional[DualRunCollector] = None


def get_dual_run_collector() -> DualRunCollector:
    """Dual-Run Collector 싱글톤"""
    global _collector
    if _collector is None:
        _collector = DualRunCollector()
    return _collector


def is_dual_run_enabled() -> bool:
    """
    환경 변수로 Dual-Run 모드 활성화 여부 확인

    Returns:
        True: Dual-Run 모드 활성화
        False: 일반 모드
    """
    return os.getenv("DUAL_RUN_MODE", "false").lower() == "true"
