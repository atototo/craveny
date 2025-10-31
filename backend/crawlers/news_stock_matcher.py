"""
뉴스-주가 매칭기

뉴스 발표 후 1일/3일/5일 주가 변동률을 계산하여 저장합니다.
"""
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models.news import NewsArticle
from backend.db.models.stock import StockPrice
from backend.db.models.match import NewsStockMatch
from backend.utils.business_days import add_business_days


logger = logging.getLogger(__name__)


def calculate_price_change(t0_price: float, tn_price: float) -> float:
    """
    주가 변동률을 계산합니다.

    Args:
        t0_price: 기준 시점 주가
        tn_price: 비교 시점 주가

    Returns:
        변동률 (%) - 소수점 둘째 자리까지 반올림

    Examples:
        >>> calculate_price_change(100.0, 110.0)
        10.0

        >>> calculate_price_change(100.0, 95.0)
        -5.0

        >>> calculate_price_change(0.0, 100.0)
        0.0
    """
    if t0_price == 0:
        return 0.0

    change = ((tn_price - t0_price) / t0_price) * 100
    return round(change, 2)


def get_stock_price_at_date(
    stock_code: str, target_date: datetime, db: Session
) -> Optional[float]:
    """
    특정 날짜의 주가(종가)를 조회합니다.

    Args:
        stock_code: 종목 코드 (6자리)
        target_date: 조회할 날짜
        db: 데이터베이스 세션

    Returns:
        종가 (없으면 None)
    """
    # 날짜 부분만 비교 (시간 제거)
    target_date_normalized = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    stock_price = (
        db.query(StockPrice)
        .filter(
            StockPrice.stock_code == stock_code,
            StockPrice.date == target_date_normalized,
        )
        .first()
    )

    if stock_price:
        return stock_price.close
    else:
        return None


def get_price_changes_for_news(
    news: NewsArticle, db: Session
) -> Dict[str, Optional[float]]:
    """
    뉴스 발표 후 1일/3일/5일 주가 변동률을 계산합니다.

    Args:
        news: 뉴스 기사 객체
        db: 데이터베이스 세션

    Returns:
        변동률 딕셔너리 {'1d': ..., '3d': ..., '5d': ...}
        데이터가 없으면 None
    """
    if not news.stock_code:
        logger.warning(f"뉴스 ID {news.id}에 종목 코드가 없습니다")
        return {"1d": None, "3d": None, "5d": None}

    # T0 시점 주가 (뉴스 발표일)
    t0_date = news.published_at.replace(hour=0, minute=0, second=0, microsecond=0)
    t0_price = get_stock_price_at_date(news.stock_code, t0_date, db)

    if t0_price is None:
        logger.warning(
            f"뉴스 ID {news.id}, 종목 {news.stock_code}의 "
            f"T0 주가({t0_date.strftime('%Y-%m-%d')})를 찾을 수 없습니다"
        )
        return {"1d": None, "3d": None, "5d": None}

    logger.debug(
        f"뉴스 ID {news.id}, 종목 {news.stock_code}, "
        f"T0 주가({t0_date.strftime('%Y-%m-%d')}): {t0_price:,.0f}원"
    )

    # T+1, T+3, T+5일 주가 조회
    results = {}

    for days, key in [(1, "1d"), (3, "3d"), (5, "5d")]:
        tn_date = add_business_days(t0_date, days=days)
        tn_price = get_stock_price_at_date(news.stock_code, tn_date, db)

        if tn_price is None:
            logger.warning(
                f"뉴스 ID {news.id}, 종목 {news.stock_code}의 "
                f"T+{days}일 주가({tn_date.strftime('%Y-%m-%d')})를 찾을 수 없습니다"
            )
            results[key] = None
        else:
            change = calculate_price_change(t0_price, tn_price)
            results[key] = change
            logger.debug(
                f"   T+{days}일 ({tn_date.strftime('%Y-%m-%d')}): "
                f"{tn_price:,.0f}원, 변동률: {change:+.2f}%"
            )

    return results


def create_news_stock_match(
    news_id: int, stock_code: str, price_changes: Dict[str, Optional[float]], db: Session
) -> Optional[NewsStockMatch]:
    """
    뉴스-주가 매칭 레코드를 생성합니다.

    Args:
        news_id: 뉴스 ID
        stock_code: 종목 코드
        price_changes: 변동률 딕셔너리 {'1d': ..., '3d': ..., '5d': ...}
        db: 데이터베이스 세션

    Returns:
        생성된 NewsStockMatch 객체 또는 None (실패 시)
    """
    try:
        # 중복 체크 (같은 뉴스 ID + 종목 코드)
        existing = (
            db.query(NewsStockMatch)
            .filter(
                NewsStockMatch.news_id == news_id,
                NewsStockMatch.stock_code == stock_code,
            )
            .first()
        )

        if existing:
            # 기존 레코드 업데이트
            existing.price_change_1d = price_changes.get("1d")
            existing.price_change_3d = price_changes.get("3d")
            existing.price_change_5d = price_changes.get("5d")
            existing.calculated_at = datetime.utcnow()
            logger.debug(f"기존 매칭 레코드 업데이트: 뉴스 ID {news_id}, 종목 {stock_code}")
            match = existing
        else:
            # 새 레코드 생성
            match = NewsStockMatch(
                news_id=news_id,
                stock_code=stock_code,
                price_change_1d=price_changes.get("1d"),
                price_change_3d=price_changes.get("3d"),
                price_change_5d=price_changes.get("5d"),
                calculated_at=datetime.utcnow(),
            )
            db.add(match)
            logger.debug(f"새 매칭 레코드 생성: 뉴스 ID {news_id}, 종목 {stock_code}")

        db.commit()
        return match

    except Exception as e:
        db.rollback()
        logger.error(f"매칭 레코드 저장 실패: 뉴스 ID {news_id}, 에러: {e}")
        return None


def match_news_with_stock(news_id: int, db: Session) -> bool:
    """
    특정 뉴스의 주가 변동률을 계산하고 저장합니다.

    Args:
        news_id: 뉴스 ID
        db: 데이터베이스 세션

    Returns:
        성공 여부
    """
    try:
        # 뉴스 조회
        news = db.query(NewsArticle).filter(NewsArticle.id == news_id).first()

        if not news:
            logger.warning(f"뉴스 ID {news_id}를 찾을 수 없습니다")
            return False

        if not news.stock_code:
            logger.debug(f"뉴스 ID {news_id}에 종목 코드가 없습니다 (스킵)")
            return False

        # 변동률 계산
        price_changes = get_price_changes_for_news(news, db)

        # 모든 변동률이 None이면 저장 안 함
        if all(v is None for v in price_changes.values()):
            logger.warning(f"뉴스 ID {news_id}의 모든 변동률이 계산되지 않았습니다")
            return False

        # 매칭 레코드 저장
        match = create_news_stock_match(news.id, news.stock_code, price_changes, db)

        if match:
            logger.info(
                f"✅ 뉴스-주가 매칭 완료: 뉴스 ID {news.id}, 종목 {news.stock_code}, "
                f"1d={price_changes['1d']}, 3d={price_changes['3d']}, 5d={price_changes['5d']}"
            )
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"뉴스-주가 매칭 실패: 뉴스 ID {news_id}, 에러: {e}")
        return False


def run_daily_matching(db: Session, lookback_days: int = 7) -> Tuple[int, int]:
    """
    일일 뉴스-주가 매칭 작업을 실행합니다.

    최근 N일 이내의 뉴스 중 아직 매칭되지 않았거나
    변동률이 불완전한 뉴스를 대상으로 매칭을 수행합니다.

    Args:
        db: 데이터베이스 세션
        lookback_days: 조회 기간 (일 단위, 기본값: 7일)

    Returns:
        (성공 건수, 실패 건수) 튜플
    """
    logger.info("=" * 60)
    logger.info(f"📊 일일 뉴스-주가 매칭 작업 시작 (최근 {lookback_days}일)")
    logger.info("=" * 60)

    try:
        # 최근 N일 이내의 뉴스 조회 (종목 코드가 있는 뉴스만)
        cutoff_date = add_business_days(datetime.now(), days=-lookback_days)

        news_list = (
            db.query(NewsArticle)
            .filter(
                NewsArticle.stock_code.isnot(None),
                NewsArticle.published_at >= cutoff_date,
            )
            .order_by(NewsArticle.published_at.desc())
            .all()
        )

        logger.info(f"매칭 대상 뉴스: {len(news_list)}건")

        success_count = 0
        fail_count = 0

        for news in news_list:
            success = match_news_with_stock(news.id, db)
            if success:
                success_count += 1
            else:
                fail_count += 1

        logger.info("=" * 60)
        logger.info(f"✅ 일일 뉴스-주가 매칭 완료: 성공 {success_count}건, 실패 {fail_count}건")
        logger.info("=" * 60)

        return success_count, fail_count

    except Exception as e:
        logger.error(f"일일 뉴스-주가 매칭 중 에러 발생: {e}", exc_info=True)
        return 0, 0
