"""
한국 주식 시장 시간 체크 유틸리티

장 시작: 09:00
장 마감: 15:30
"""
import logging
from datetime import datetime, time
from typing import Optional

logger = logging.getLogger(__name__)


# 한국 공휴일 (2025년)
# TODO: 동적으로 공휴일 API 연동 (한국거래소 API 또는 한국천문연구원 API)
KOREAN_HOLIDAYS_2025 = {
    "2025-01-01",  # 신정
    "2025-01-28",  # 설날 연휴
    "2025-01-29",  # 설날
    "2025-01-30",  # 설날 연휴
    "2025-03-01",  # 삼일절
    "2025-03-03",  # 대체공휴일
    "2025-05-05",  # 어린이날
    "2025-05-06",  # 대체공휴일
    "2025-06-06",  # 현충일
    "2025-08-15",  # 광복절
    "2025-09-06",  # 추석 연휴
    "2025-09-07",  # 추석 연휴
    "2025-09-08",  # 추석
    "2025-09-09",  # 추석 연휴
    "2025-10-03",  # 개천절
    "2025-10-09",  # 한글날
    "2025-12-25",  # 성탄절
}


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """
    주식 시장이 열려있는지 확인

    Args:
        dt: 확인할 시각 (기본: 현재 시각)

    Returns:
        시장이 열려있으면 True, 아니면 False
    """
    if dt is None:
        dt = datetime.now()

    # 1. 주말 체크
    if dt.weekday() >= 5:  # 토요일(5), 일요일(6)
        logger.debug(f"⏸️  주말: {dt.strftime('%Y-%m-%d %A')}")
        return False

    # 2. 공휴일 체크
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in KOREAN_HOLIDAYS_2025:
        logger.debug(f"⏸️  공휴일: {date_str}")
        return False

    # 3. 장 시간 체크 (09:00 ~ 15:30)
    market_open_time = time(9, 0)
    market_close_time = time(15, 30)

    current_time = dt.time()

    if current_time < market_open_time:
        logger.debug(f"⏸️  장 시작 전: {current_time.strftime('%H:%M:%S')}")
        return False

    if current_time >= market_close_time:
        logger.debug(f"⏸️  장 마감 후: {current_time.strftime('%H:%M:%S')}")
        return False

    # 장 시간
    logger.debug(f"✅ 장 시간: {current_time.strftime('%H:%M:%S')}")
    return True


def get_next_market_open() -> Optional[datetime]:
    """
    다음 장 시작 시간 조회

    Returns:
        다음 장 시작 datetime (주말/공휴일 고려)
    """
    dt = datetime.now()

    # 오늘 장 시작 시간
    market_open = dt.replace(hour=9, minute=0, second=0, microsecond=0)

    # 오늘 장이 아직 안 열렸으면 오늘 반환
    if dt < market_open and is_market_open(market_open):
        return market_open

    # 내일부터 체크
    from datetime import timedelta

    for i in range(1, 10):  # 최대 10일 후까지 체크
        next_day = dt + timedelta(days=i)
        next_open = next_day.replace(hour=9, minute=0, second=0, microsecond=0)

        if is_market_open(next_open):
            return next_open

    return None


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """
    거래일인지 확인 (시간 무관)

    Args:
        dt: 확인할 날짜 (기본: 오늘)

    Returns:
        거래일이면 True, 아니면 False
    """
    if dt is None:
        dt = datetime.now()

    # 주말 체크
    if dt.weekday() >= 5:
        return False

    # 공휴일 체크
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in KOREAN_HOLIDAYS_2025:
        return False

    return True
