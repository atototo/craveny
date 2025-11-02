#!/usr/bin/env python
"""
주가 과거 데이터 수집 스크립트

target_stocks.json의 모든 종목에 대해 과거 3개월 주가 데이터를 수집합니다.
신규 종목이 추가되었을 때 또는 초기 설정 시 실행하세요.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime, timedelta
from typing import Optional

from backend.crawlers.stock_crawler import get_stock_crawler
from backend.db.session import SessionLocal
from backend.db.models.stock import StockPrice
from sqlalchemy import func

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_earliest_date_for_stock(db, stock_code: str) -> Optional[datetime]:
    """
    특정 종목의 가장 오래된 주가 데이터 날짜를 반환합니다.

    Args:
        db: 데이터베이스 세션
        stock_code: 종목 코드

    Returns:
        가장 오래된 날짜 또는 None (데이터 없음)
    """
    min_date = db.query(func.min(StockPrice.date)).filter(
        StockPrice.stock_code == stock_code
    ).scalar()
    return min_date


def collect_history_for_stock(stock_code: str, stock_name: str, days: int = 90) -> int:
    """
    특정 종목의 과거 주가 데이터를 수집합니다.

    Args:
        stock_code: 종목 코드
        stock_name: 종목명
        days: 수집할 과거 일수 (기본값: 90일)

    Returns:
        저장된 레코드 수
    """
    logger.info("=" * 70)
    logger.info(f"📈 {stock_name} ({stock_code}) 과거 주가 수집 시작")
    logger.info("=" * 70)

    db = SessionLocal()
    stock_crawler = get_stock_crawler()

    try:
        # 기존 데이터 확인
        earliest_date = get_earliest_date_for_stock(db, stock_code)
        existing_count = db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code
        ).count()

        if earliest_date:
            logger.info(f"기존 데이터: {existing_count}건 (가장 오래된: {earliest_date.date()})")
        else:
            logger.info(f"기존 데이터: 없음")

        # 수집 기간 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 기존 데이터가 있으면 그 이전부터만 수집
        if earliest_date:
            # 기존 데이터가 충분히 오래되었으면 스킵
            target_start_date = end_date - timedelta(days=days)
            if earliest_date.date() <= target_start_date.date():
                logger.info(f"✅ 충분한 과거 데이터 존재 ({days}일 이상). 수집 스킵")
                return 0

            # 기존 데이터 이전부터 수집
            end_date = earliest_date - timedelta(days=1)
            logger.info(f"수집 기간: {start_date.date()} ~ {end_date.date()}")
        else:
            logger.info(f"수집 기간: 최근 {days}일 ({start_date.date()} ~ {end_date.date()})")

        # 주가 데이터 수집
        df = stock_crawler.fetch_stock_data(stock_code, start_date=start_date)

        if df is None or df.empty:
            logger.warning(f"⚠️  {stock_name}: 수집된 주가 데이터가 없습니다")
            return 0

        logger.info(f"✅ {len(df)}건의 주가 데이터를 수집했습니다")

        # 데이터베이스 저장
        saved_count = stock_crawler.save_stock_data(stock_code, df, db)

        logger.info(f"💾 저장 완료: {saved_count}건")

        # 최종 통계
        total_count = db.query(StockPrice).filter(
            StockPrice.stock_code == stock_code
        ).count()
        new_earliest = get_earliest_date_for_stock(db, stock_code)
        new_latest = db.query(func.max(StockPrice.date)).filter(
            StockPrice.stock_code == stock_code
        ).scalar()

        logger.info(f"📊 최종 데이터: {total_count}건 ({new_earliest.date()} ~ {new_latest.date()})")
        logger.info("")

        return saved_count

    except Exception as e:
        logger.error(f"❌ {stock_name} 주가 수집 실패: {e}", exc_info=True)
        db.rollback()
        return 0

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 주가 과거 데이터 수집 시작")
    logger.info("")

    # 주가 수집기에서 종목 리스트 가져오기
    stock_crawler = get_stock_crawler()

    # 모든 우선순위의 종목 수집
    total_collected = 0
    total_stocks = len(stock_crawler.target_stocks)

    logger.info(f"대상 종목: {total_stocks}개")
    logger.info(f"수집 기간: 최근 90일")
    logger.info("")

    # 각 종목별 과거 주가 수집
    for stock in stock_crawler.target_stocks:
        count = collect_history_for_stock(
            stock_code=stock["code"],
            stock_name=stock["name"],
            days=90  # 3개월
        )
        total_collected += count

    # 최종 결과
    logger.info("=" * 70)
    logger.info("✅ 주가 과거 데이터 수집 완료")
    logger.info("=" * 70)
    logger.info(f"총 수집 레코드: {total_collected}건")
    logger.info("")


if __name__ == "__main__":
    main()
