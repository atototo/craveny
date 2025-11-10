"""
주가 데이터 Resample 유틸리티

1분봉 데이터를 다양한 시간대로 변환하는 함수들을 제공합니다.
- 1분봉 → 3분/5분/10분/30분/60분봉
- OHLCV 집계 (Open: first, High: max, Low: min, Close: last, Volume: sum)
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models.stock import StockPriceMinute


logger = logging.getLogger(__name__)


def resample_ohlcv(df: pd.DataFrame, timeframe: str = "5T") -> pd.DataFrame:
    """
    1분봉 데이터를 다양한 시간대로 리샘플링

    Args:
        df: 1분봉 DataFrame (columns: datetime, open, high, low, close, volume)
        timeframe: 시간 단위
            - "1T" or "1min": 1분 (원본)
            - "3T" or "3min": 3분
            - "5T" or "5min": 5분
            - "10T" or "10min": 10분
            - "30T" or "30min": 30분
            - "60T" or "60min" or "1H": 60분 (1시간)

    Returns:
        리샘플링된 DataFrame

    Example:
        >>> df = pd.DataFrame({
        ...     'datetime': pd.date_range('2025-01-01 09:00', periods=10, freq='1min'),
        ...     'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        ...     'high': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        ...     'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        ...     'close': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
        ...     'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
        ... })
        >>> resampled = resample_ohlcv(df, timeframe="5T")
        >>> print(resampled)
    """
    if df.empty:
        logger.warning("빈 DataFrame이 전달됨, 빈 DataFrame 반환")
        return df

    # datetime 컬럼이 없으면 에러
    if 'datetime' not in df.columns:
        raise ValueError("DataFrame에 'datetime' 컬럼이 필요합니다")

    # 복사본 생성
    df = df.copy()

    # datetime을 인덱스로 설정
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)

    # Resample
    try:
        resampled = df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
    except Exception as e:
        logger.error(f"Resample 실패: {e}")
        raise

    # NaN 제거 (데이터가 없는 시간대 제거)
    resampled = resampled.dropna()

    # 인덱스를 컬럼으로 복원
    resampled.reset_index(inplace=True)

    logger.debug(f"Resample 완료: {len(df)}개 → {len(resampled)}개 (timeframe={timeframe})")

    return resampled


def fetch_and_resample(
    db: Session,
    stock_code: str,
    start_datetime: datetime,
    end_datetime: datetime,
    timeframe: str = "5T"
) -> pd.DataFrame:
    """
    DB에서 1분봉 데이터를 조회하고 리샘플링

    Args:
        db: SQLAlchemy Session
        stock_code: 종목 코드 (예: "005930")
        start_datetime: 시작 시간
        end_datetime: 종료 시간
        timeframe: 시간 단위 (예: "5T", "10T", "30T", "60T")

    Returns:
        리샘플링된 DataFrame

    Example:
        >>> from backend.db.session import SessionLocal
        >>> from datetime import datetime, timedelta
        >>> db = SessionLocal()
        >>> end = datetime.now()
        >>> start = end - timedelta(hours=1)
        >>> df = fetch_and_resample(db, "005930", start, end, timeframe="5T")
        >>> print(df)
    """
    try:
        # DB 조회
        query = db.query(StockPriceMinute).filter(
            StockPriceMinute.stock_code == stock_code,
            StockPriceMinute.datetime >= start_datetime,
            StockPriceMinute.datetime <= end_datetime
        ).order_by(StockPriceMinute.datetime)

        rows = query.all()

        if not rows:
            logger.warning(
                f"데이터 없음: {stock_code} ({start_datetime} ~ {end_datetime})"
            )
            return pd.DataFrame(columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])

        # DataFrame 변환
        data = []
        for row in rows:
            data.append({
                'datetime': row.datetime,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume
            })

        df = pd.DataFrame(data)

        logger.info(
            f"DB 조회 완료: {stock_code} - {len(df)}건 "
            f"({start_datetime.strftime('%Y-%m-%d %H:%M')} ~ {end_datetime.strftime('%Y-%m-%d %H:%M')})"
        )

        # Resample
        resampled = resample_ohlcv(df, timeframe=timeframe)

        logger.info(
            f"Resample 완료: {stock_code} - {len(df)}건 → {len(resampled)}건 ({timeframe})"
        )

        return resampled

    except Exception as e:
        logger.error(f"fetch_and_resample 실패: {stock_code} - {e}")
        raise


def get_common_timeframes() -> Dict[str, str]:
    """
    일반적으로 사용되는 timeframe 매핑

    Returns:
        timeframe 이름과 pandas resample 문자열 매핑

    Example:
        >>> timeframes = get_common_timeframes()
        >>> print(timeframes)
        {
            '1min': '1T',
            '3min': '3T',
            '5min': '5T',
            '10min': '10T',
            '30min': '30T',
            '60min': '60T',
            '1hour': '1H'
        }
    """
    return {
        "1min": "1T",
        "3min": "3T",
        "5min": "5T",
        "10min": "10T",
        "30min": "30T",
        "60min": "60T",
        "1hour": "1H"
    }


def validate_timeframe(timeframe: str) -> bool:
    """
    Timeframe 문자열 유효성 검사

    Args:
        timeframe: 검증할 timeframe 문자열

    Returns:
        유효하면 True, 아니면 False

    Example:
        >>> validate_timeframe("5T")
        True
        >>> validate_timeframe("5M")  # M은 Month를 의미하므로 잘못된 사용
        False
    """
    valid_timeframes = list(get_common_timeframes().values())
    return timeframe in valid_timeframes


def resample_to_multiple_timeframes(
    df: pd.DataFrame,
    timeframes: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    1분봉 데이터를 여러 시간대로 한 번에 리샘플링

    Args:
        df: 1분봉 DataFrame
        timeframes: 리샘플링할 시간대 리스트 (기본값: ["3T", "5T", "10T", "30T", "60T"])

    Returns:
        timeframe별 리샘플링된 DataFrame 딕셔너리

    Example:
        >>> df = pd.DataFrame(...)  # 1분봉 데이터
        >>> results = resample_to_multiple_timeframes(df)
        >>> print(results.keys())
        dict_keys(['3T', '5T', '10T', '30T', '60T'])
        >>> print(results['5T'])  # 5분봉 데이터
    """
    if timeframes is None:
        timeframes = ["3T", "5T", "10T", "30T", "60T"]

    results = {}

    for timeframe in timeframes:
        try:
            results[timeframe] = resample_ohlcv(df, timeframe=timeframe)
            logger.debug(f"Resample 완료: {timeframe} - {len(results[timeframe])}건")
        except Exception as e:
            logger.error(f"Resample 실패: {timeframe} - {e}")
            results[timeframe] = pd.DataFrame(
                columns=['datetime', 'open', 'high', 'low', 'close', 'volume']
            )

    return results
