"""
장 시간 판별 유틸리티

한국 주식 시장의 거래 시간을 판별합니다.
"""
from datetime import datetime, time, timedelta
from typing import Optional


# 한국 주식시장 거래 시간
MARKET_OPEN_TIME = time(9, 0)  # 09:00
MARKET_CLOSE_TIME = time(15, 30)  # 15:30

# 거래일 (월~금)
TRADING_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday=0, Friday=4


def is_trading_day(dt: Optional[datetime] = None) -> bool:
    """
    거래일인지 확인합니다.

    Args:
        dt: 확인할 날짜/시간 (기본값: 현재 시간)

    Returns:
        거래일 여부 (True: 평일, False: 주말)

    Note:
        공휴일 체크는 추후 확장 가능
    """
    if dt is None:
        dt = datetime.now()

    # 평일(월~금) 체크
    return dt.weekday() in TRADING_WEEKDAYS


def is_market_hours(dt: Optional[datetime] = None) -> bool:
    """
    장 시간(09:00~15:30)인지 확인합니다.

    Args:
        dt: 확인할 날짜/시간 (기본값: 현재 시간)

    Returns:
        장 시간 여부
    """
    if dt is None:
        dt = datetime.now()

    current_time = dt.time()

    # 09:00 <= 현재 시간 < 15:30
    return MARKET_OPEN_TIME <= current_time < MARKET_CLOSE_TIME


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """
    현재 장이 열려있는지 확인합니다.

    거래일이면서 장 시간인 경우에만 True를 반환합니다.

    Args:
        dt: 확인할 날짜/시간 (기본값: 현재 시간)

    Returns:
        장 개장 여부

    Examples:
        >>> # 평일 10:00
        >>> is_market_open(datetime(2025, 10, 31, 10, 0))
        True

        >>> # 평일 16:00
        >>> is_market_open(datetime(2025, 10, 31, 16, 0))
        False

        >>> # 주말
        >>> is_market_open(datetime(2025, 11, 2, 10, 0))
        False
    """
    if dt is None:
        dt = datetime.now()

    return is_trading_day(dt) and is_market_hours(dt)


def get_market_status(dt: Optional[datetime] = None) -> str:
    """
    시장 상태를 문자열로 반환합니다.

    Args:
        dt: 확인할 날짜/시간 (기본값: 현재 시간)

    Returns:
        "open" (장중), "closed" (장마감), "weekend" (주말)
    """
    if dt is None:
        dt = datetime.now()

    if not is_trading_day(dt):
        return "weekend"

    if is_market_hours(dt):
        return "open"

    return "closed"


def get_next_market_open() -> datetime:
    """
    다음 장 개장 시간을 반환합니다.

    Returns:
        다음 장 개장 datetime
    """
    now = datetime.now()

    # 오늘이 거래일이고, 아직 장 시작 전이면 오늘 09:00
    if is_trading_day(now) and now.time() < MARKET_OPEN_TIME:
        return datetime.combine(now.date(), MARKET_OPEN_TIME)

    # 그 외의 경우, 다음 거래일 09:00 찾기
    next_day = now
    for _ in range(7):  # 최대 7일 탐색
        next_day = datetime(
            next_day.year,
            next_day.month,
            next_day.day,
            MARKET_OPEN_TIME.hour,
            MARKET_OPEN_TIME.minute,
        ) + timedelta(days=1)

        if is_trading_day(next_day):
            return next_day

    # fallback (should not reach here)
    return next_day


def get_time_until_market_open() -> Optional[int]:
    """
    장 개장까지 남은 시간(초)을 반환합니다.

    Returns:
        남은 시간(초) 또는 None (이미 장중인 경우)
    """
    if is_market_open():
        return None

    next_open = get_next_market_open()
    now = datetime.now()

    time_diff = next_open - now
    return int(time_diff.total_seconds())
