"""
뉴스-주가 매칭 테스트 스크립트

영업일 계산, 주가 변동률 계산, 매칭 로직을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime

from backend.utils.business_days import (
    is_business_day,
    get_next_business_day,
    add_business_days,
    get_business_days_between,
)
from backend.crawlers.news_stock_matcher import (
    calculate_price_change,
    get_stock_price_at_date,
    get_price_changes_for_news,
    match_news_with_stock,
    run_daily_matching,
)
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.db.models.stock import StockPrice
from backend.db.models.match import NewsStockMatch

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_business_days():
    """영업일 계산 테스트"""
    logger.info("=" * 60)
    logger.info("📅 영업일 계산 테스트")
    logger.info("=" * 60)

    # 테스트 날짜: 2025-10-31 (금요일)
    test_date = datetime(2025, 10, 31)

    # 1. 영업일 여부
    is_bday = is_business_day(test_date)
    logger.info(f"2025-10-31 (금요일) 영업일 여부: {is_bday}")
    assert is_bday is True, "금요일은 영업일이어야 함"

    # 2. 주말 체크
    weekend = datetime(2025, 11, 1)  # 토요일
    is_weekend = is_business_day(weekend)
    logger.info(f"2025-11-01 (토요일) 영업일 여부: {is_weekend}")
    assert is_weekend is False, "토요일은 영업일이 아님"

    # 3. 다음 영업일
    next_bday = get_next_business_day(test_date, skip_days=1)
    logger.info(
        f"2025-10-31 (금요일) 다음 영업일: {next_bday.strftime('%Y-%m-%d (%A)')}"
    )
    assert next_bday.date() == datetime(2025, 11, 3).date(), "다음 영업일은 월요일이어야 함"

    # 4. T+3일 (영업일 기준)
    t_plus_3 = add_business_days(test_date, days=3)
    logger.info(f"T+3일 (영업일): {t_plus_3.strftime('%Y-%m-%d (%A)')}")
    assert t_plus_3.date() == datetime(2025, 11, 5).date(), "T+3일은 2025-11-05 (수요일)이어야 함"

    # 5. 영업일 간격 계산
    start = datetime(2025, 10, 31)  # 금요일
    end = datetime(2025, 11, 5)  # 수요일
    bdays = get_business_days_between(start, end)
    logger.info(f"2025-10-31 ~ 2025-11-05 사이 영업일 수: {bdays}일")
    assert bdays == 3, "금요일 ~ 다음주 수요일은 3 영업일"

    logger.info("✅ 영업일 계산 테스트 통과")
    logger.info("")


def test_price_change_calculation():
    """가격 변동률 계산 테스트"""
    logger.info("=" * 60)
    logger.info("📈 가격 변동률 계산 테스트")
    logger.info("=" * 60)

    # 1. 상승
    change1 = calculate_price_change(100.0, 110.0)
    logger.info(f"100 → 110: {change1:+.2f}%")
    assert change1 == 10.0, "10% 상승이어야 함"

    # 2. 하락
    change2 = calculate_price_change(100.0, 95.0)
    logger.info(f"100 → 95: {change2:+.2f}%")
    assert change2 == -5.0, "-5% 하락이어야 함"

    # 3. 변동 없음
    change3 = calculate_price_change(100.0, 100.0)
    logger.info(f"100 → 100: {change3:+.2f}%")
    assert change3 == 0.0, "0% 변동이어야 함"

    # 4. 0으로 나누기
    change4 = calculate_price_change(0.0, 100.0)
    logger.info(f"0 → 100: {change4:+.2f}% (0으로 나누기 방지)")
    assert change4 == 0.0, "0으로 나누기는 0% 반환"

    logger.info("✅ 가격 변동률 계산 테스트 통과")
    logger.info("")


def test_stock_price_query():
    """주가 조회 테스트"""
    logger.info("=" * 60)
    logger.info("📊 주가 조회 테스트")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 삼성전자 주가 조회 (2025-10-31)
        test_date = datetime(2025, 10, 31)
        stock_code = "005930"

        price = get_stock_price_at_date(stock_code, test_date, db)

        if price:
            logger.info(f"✅ {stock_code} ({test_date.strftime('%Y-%m-%d')}) 주가: {price:,.0f}원")
        else:
            logger.warning(f"⚠️  {stock_code} ({test_date.strftime('%Y-%m-%d')}) 주가 데이터 없음")

        # 다음 영업일 주가 조회
        next_date = get_next_business_day(test_date, skip_days=1)
        next_price = get_stock_price_at_date(stock_code, next_date, db)

        if next_price:
            logger.info(
                f"✅ {stock_code} ({next_date.strftime('%Y-%m-%d')}) 주가: {next_price:,.0f}원"
            )
            if price:
                change = calculate_price_change(price, next_price)
                logger.info(f"   변동률: {change:+.2f}%")
        else:
            logger.warning(
                f"⚠️  {stock_code} ({next_date.strftime('%Y-%m-%d')}) 주가 데이터 없음"
            )

    finally:
        db.close()

    logger.info("")


def test_news_stock_matching():
    """뉴스-주가 매칭 테스트"""
    logger.info("=" * 60)
    logger.info("🔗 뉴스-주가 매칭 테스트")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 최근 뉴스 조회 (종목 코드가 있는 뉴스)
        news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .order_by(NewsArticle.published_at.desc())
            .first()
        )

        if not news:
            logger.warning("⚠️  종목 코드가 있는 뉴스가 없습니다")
            return

        logger.info(f"테스트 뉴스: ID={news.id}, 종목={news.stock_code}")
        logger.info(f"   제목: {news.title[:50]}...")
        logger.info(f"   발표일: {news.published_at.strftime('%Y-%m-%d %H:%M')}")

        # 변동률 계산
        price_changes = get_price_changes_for_news(news, db)

        logger.info("계산된 변동률:")
        logger.info(f"   T+1일: {price_changes['1d']}")
        logger.info(f"   T+3일: {price_changes['3d']}")
        logger.info(f"   T+5일: {price_changes['5d']}")

        # 매칭 레코드 저장
        success = match_news_with_stock(news.id, db)

        if success:
            logger.info("✅ 뉴스-주가 매칭 성공")

            # 저장된 매칭 레코드 확인
            match = (
                db.query(NewsStockMatch)
                .filter(
                    NewsStockMatch.news_id == news.id,
                    NewsStockMatch.stock_code == news.stock_code,
                )
                .first()
            )

            if match:
                logger.info(f"저장된 매칭 레코드:")
                logger.info(f"   ID: {match.id}")
                logger.info(f"   T+1일 변동률: {match.price_change_1d}")
                logger.info(f"   T+3일 변동률: {match.price_change_3d}")
                logger.info(f"   T+5일 변동률: {match.price_change_5d}")
                logger.info(
                    f"   계산 시간: {match.calculated_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        else:
            logger.warning("❌ 뉴스-주가 매칭 실패")

    finally:
        db.close()

    logger.info("")


def test_daily_matching():
    """일일 매칭 작업 테스트"""
    logger.info("=" * 60)
    logger.info("🔄 일일 매칭 작업 테스트")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # 최근 7일 뉴스 대상으로 매칭 실행
        success_count, fail_count = run_daily_matching(db, lookback_days=7)

        logger.info("=" * 60)
        logger.info(f"✅ 일일 매칭 작업 완료:")
        logger.info(f"   성공: {success_count}건")
        logger.info(f"   실패: {fail_count}건")
        logger.info(
            f"   성공률: {(success_count / (success_count + fail_count) * 100) if (success_count + fail_count) > 0 else 0:.1f}%"
        )
        logger.info("=" * 60)

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    try:
        # 1. 영업일 계산 테스트
        test_business_days()

        # 2. 가격 변동률 계산 테스트
        test_price_change_calculation()

        # 3. 주가 조회 테스트
        test_stock_price_query()

        # 4. 뉴스-주가 매칭 테스트
        test_news_stock_matching()

        # 5. 일일 매칭 작업 테스트
        test_daily_matching()

        logger.info("✅ 모든 테스트 완료")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
