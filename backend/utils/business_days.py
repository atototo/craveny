"""
영업일 계산 유틸리티

한국 주식 시장의 영업일(평일)을 계산합니다.
"""
from datetime import datetime, timedelta
from typing import Optional, List


# 한국 주식시장 영업일 (월~금)
BUSINESS_WEEKDAYS = [0, 1, 2, 3, 4]  # Monday=0, Friday=4

# 한국 공휴일 (추후 확장)
# 2025년 공휴일 리스트 (예시)
HOLIDAYS_2025: List[str] = [
    "2025-01-01",  # 신정
    "2025-01-28",  # 설날 연휴
    "2025-01-29",  # 설날
    "2025-01-30",  # 설날 연휴
    "2025-03-01",  # 삼일절
    "2025-03-03",  # 대체공휴일 (삼일절)
    "2025-05-05",  # 어린이날
    "2025-05-06",  # 대체공휴일 (어린이날)
    "2025-06-06",  # 현충일
    "2025-08-15",  # 광복절
    "2025-09-06",  # 추석 연휴
    "2025-09-07",  # 추석 연휴
    "2025-09-08",  # 추석
    "2025-09-09",  # 추석 연휴
    "2025-10-03",  # 개천절
    "2025-10-09",  # 한글날
    "2025-12-25",  # 크리스마스
]


def get_holidays(year: Optional[int] = None) -> List[datetime]:
    """
    특정 연도의 공휴일 리스트를 반환합니다.

    Args:
        year: 연도 (기본값: 현재 연도)

    Returns:
        datetime 객체 리스트
    """
    if year is None:
        year = datetime.now().year

    # 현재는 2025년만 지원
    if year == 2025:
        return [datetime.strptime(date, "%Y-%m-%d") for date in HOLIDAYS_2025]
    else:
        # 다른 연도는 빈 리스트 반환 (추후 확장)
        return []


def is_business_day(dt: Optional[datetime] = None, include_holidays: bool = True) -> bool:
    """
    주어진 날짜가 영업일인지 확인합니다.

    Args:
        dt: 확인할 날짜 (기본값: 현재 날짜)
        include_holidays: 공휴일 체크 여부 (기본값: True)

    Returns:
        영업일 여부 (True: 영업일, False: 주말/공휴일)

    Examples:
        >>> # 평일 (월요일)
        >>> is_business_day(datetime(2025, 11, 3))
        True

        >>> # 주말 (일요일)
        >>> is_business_day(datetime(2025, 11, 2))
        False

        >>> # 공휴일 (크리스마스)
        >>> is_business_day(datetime(2025, 12, 25))
        False
    """
    if dt is None:
        dt = datetime.now()

    # 주말 체크
    if dt.weekday() not in BUSINESS_WEEKDAYS:
        return False

    # 공휴일 체크
    if include_holidays:
        holidays = get_holidays(dt.year)
        # 날짜 부분만 비교
        dt_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        for holiday in holidays:
            if dt_date.date() == holiday.date():
                return False

    return True


def get_next_business_day(
    dt: Optional[datetime] = None, skip_days: int = 1, include_holidays: bool = True
) -> datetime:
    """
    주어진 날짜로부터 N 영업일 후의 날짜를 반환합니다.

    Args:
        dt: 기준 날짜 (기본값: 현재 날짜)
        skip_days: 건너뛸 영업일 수 (기본값: 1)
        include_holidays: 공휴일 체크 여부 (기본값: True)

    Returns:
        N 영업일 후의 datetime

    Examples:
        >>> # 금요일 → 다음 영업일 (월요일)
        >>> get_next_business_day(datetime(2025, 10, 31), skip_days=1)
        datetime(2025, 11, 3, 0, 0)

        >>> # 목요일 → 3 영업일 후 (화요일, 주말 건너뜀)
        >>> get_next_business_day(datetime(2025, 10, 30), skip_days=3)
        datetime(2025, 11, 4, 0, 0)
    """
    if dt is None:
        dt = datetime.now()

    # 시간 정보 제거 (날짜만)
    current_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    business_days_counted = 0

    # 다음 날부터 시작
    next_date = current_date + timedelta(days=1)

    # N 영업일을 찾을 때까지 반복
    while business_days_counted < skip_days:
        if is_business_day(next_date, include_holidays=include_holidays):
            business_days_counted += 1

        # 아직 N 영업일에 도달하지 못했으면 다음 날로
        if business_days_counted < skip_days:
            next_date += timedelta(days=1)

    return next_date


def add_business_days(
    dt: Optional[datetime] = None, days: int = 1, include_holidays: bool = True
) -> datetime:
    """
    주어진 날짜에 영업일 기준으로 days를 더합니다.

    Args:
        dt: 기준 날짜 (기본값: 현재 날짜)
        days: 추가할 영업일 수 (음수 가능)
        include_holidays: 공휴일 체크 여부 (기본값: True)

    Returns:
        영업일 기준으로 days를 더한 datetime

    Examples:
        >>> # T+1일 (1 영업일 후)
        >>> add_business_days(datetime(2025, 10, 31), days=1)
        datetime(2025, 11, 3, 0, 0)

        >>> # T-1일 (1 영업일 전)
        >>> add_business_days(datetime(2025, 11, 3), days=-1)
        datetime(2025, 10, 31, 0, 0)
    """
    if dt is None:
        dt = datetime.now()

    if days == 0:
        return dt

    # 양수: 미래로
    if days > 0:
        return get_next_business_day(dt, skip_days=days, include_holidays=include_holidays)

    # 음수: 과거로
    current_date = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    business_days_counted = 0

    prev_date = current_date - timedelta(days=1)

    # N 영업일을 찾을 때까지 반복
    while business_days_counted < abs(days):
        if is_business_day(prev_date, include_holidays=include_holidays):
            business_days_counted += 1

        if business_days_counted < abs(days):
            prev_date -= timedelta(days=1)

    return prev_date


def get_business_days_between(
    start_date: datetime, end_date: datetime, include_holidays: bool = True
) -> int:
    """
    두 날짜 사이의 영업일 수를 계산합니다.

    Args:
        start_date: 시작 날짜
        end_date: 종료 날짜
        include_holidays: 공휴일 체크 여부 (기본값: True)

    Returns:
        영업일 수 (시작일 제외, 종료일 포함)

    Examples:
        >>> # 금요일 ~ 월요일 (1 영업일)
        >>> get_business_days_between(
        ...     datetime(2025, 10, 31),
        ...     datetime(2025, 11, 3)
        ... )
        1
    """
    start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if start >= end:
        return 0

    business_days = 0
    current = start + timedelta(days=1)

    while current <= end:
        if is_business_day(current, include_holidays=include_holidays):
            business_days += 1
        current += timedelta(days=1)

    return business_days
