"""
Resample 유틸리티 테스트

Usage:
    uv run python scripts/test_resample.py
"""
import logging
from datetime import datetime, timedelta

import pandas as pd

from backend.utils.resample import (
    resample_ohlcv,
    get_common_timeframes,
    validate_timeframe,
    resample_to_multiple_timeframes,
    fetch_and_resample
)
from backend.db.session import SessionLocal
from backend.db.models.stock import StockPriceMinute


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_resample_basic():
    """기본 Resample 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 기본 Resample 테스트")
    logger.info("=" * 80)

    # 샘플 데이터 생성 (10분간의 1분봉 데이터)
    df = pd.DataFrame({
        'datetime': pd.date_range('2025-01-01 09:00', periods=10, freq='1min'),
        'open': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
        'high': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
        'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5, 108.5, 109.5],
        'volume': [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900]
    })

    logger.info(f"원본 데이터: {len(df)}건")
    logger.info(f"\n{df.to_string()}")

    # 5분봉으로 Resample
    resampled = resample_ohlcv(df, timeframe="5T")

    logger.info(f"\n5분봉 Resample 결과: {len(resampled)}건")
    logger.info(f"\n{resampled.to_string()}")

    # 검증
    assert len(resampled) == 2, "10분 데이터를 5분봉으로 변환하면 2개가 되어야 함"

    # 첫 번째 5분봉 검증 (09:00-09:04)
    first_bar = resampled.iloc[0]
    assert first_bar['open'] == 100, "첫 번째 봉의 시가는 100이어야 함"
    assert first_bar['high'] == 105, "첫 번째 봉의 고가는 105이어야 함"
    assert first_bar['low'] == 99, "첫 번째 봉의 저가는 99이어야 함"
    assert first_bar['close'] == 104.5, "첫 번째 봉의 종가는 104.5이어야 함"
    assert first_bar['volume'] == 6000, "첫 번째 봉의 거래량은 6000이어야 함"

    logger.info("\n✅ 기본 Resample 테스트 통과!")
    return True


def test_multiple_timeframes():
    """여러 시간대 Resample 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 여러 시간대 Resample 테스트")
    logger.info("=" * 80)

    # 60분간의 1분봉 데이터 생성
    df = pd.DataFrame({
        'datetime': pd.date_range('2025-01-01 09:00', periods=60, freq='1min'),
        'open': list(range(100, 160)),
        'high': list(range(101, 161)),
        'low': list(range(99, 159)),
        'close': [i + 0.5 for i in range(100, 160)],
        'volume': [1000 + i * 10 for i in range(60)]
    })

    logger.info(f"원본 데이터: {len(df)}건 (60분)")

    # 여러 시간대로 Resample
    results = resample_to_multiple_timeframes(df)

    logger.info("\nResample 결과:")
    for timeframe, resampled_df in results.items():
        logger.info(f"  - {timeframe}: {len(resampled_df)}건")

    # 검증
    assert len(results["3T"]) == 20, "60분을 3분봉으로 나누면 20개"
    assert len(results["5T"]) == 12, "60분을 5분봉으로 나누면 12개"
    assert len(results["10T"]) == 6, "60분을 10분봉으로 나누면 6개"
    assert len(results["30T"]) == 2, "60분을 30분봉으로 나누면 2개"
    assert len(results["60T"]) == 1, "60분을 60분봉으로 나누면 1개"

    logger.info("\n✅ 여러 시간대 Resample 테스트 통과!")
    return True


def test_common_timeframes():
    """일반 Timeframe 매핑 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 일반 Timeframe 매핑 테스트")
    logger.info("=" * 80)

    timeframes = get_common_timeframes()

    logger.info("지원되는 Timeframe:")
    for name, value in timeframes.items():
        logger.info(f"  - {name}: {value}")

    # 검증
    assert "1min" in timeframes
    assert "5min" in timeframes
    assert "60min" in timeframes
    assert timeframes["5min"] == "5T"

    logger.info("\n✅ Timeframe 매핑 테스트 통과!")
    return True


def test_validate_timeframe():
    """Timeframe 유효성 검사 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Timeframe 유효성 검사 테스트")
    logger.info("=" * 80)

    # 유효한 timeframe
    valid = ["1T", "3T", "5T", "10T", "30T", "60T", "1H"]
    for tf in valid:
        assert validate_timeframe(tf), f"{tf}는 유효해야 함"
        logger.info(f"  ✅ {tf}: 유효")

    # 유효하지 않은 timeframe
    invalid = ["5M", "1D", "1W", "invalid"]
    for tf in invalid:
        assert not validate_timeframe(tf), f"{tf}는 유효하지 않아야 함"
        logger.info(f"  ❌ {tf}: 유효하지 않음")

    logger.info("\n✅ Timeframe 유효성 검사 테스트 통과!")
    return True


def test_fetch_and_resample():
    """DB 조회 및 Resample 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 DB 조회 및 Resample 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 최근 1분봉 데이터 확인
        recent = db.query(StockPriceMinute).order_by(
            StockPriceMinute.datetime.desc()
        ).first()

        if not recent:
            logger.warning("⚠️  DB에 1분봉 데이터 없음 - 테스트 스킵")
            return True

        stock_code = recent.stock_code
        end_datetime = recent.datetime
        start_datetime = end_datetime - timedelta(hours=1)

        logger.info(f"종목: {stock_code}")
        logger.info(f"시작: {start_datetime}")
        logger.info(f"종료: {end_datetime}")

        # 5분봉으로 Resample
        resampled = fetch_and_resample(
            db, stock_code, start_datetime, end_datetime, timeframe="5T"
        )

        if not resampled.empty:
            logger.info(f"\n5분봉 데이터 샘플 (최근 5개):")
            logger.info(f"\n{resampled.tail().to_string()}")
            logger.info(f"\n✅ DB 조회 및 Resample 테스트 통과!")
        else:
            logger.warning("⚠️  Resample 결과가 비어있음")

        return True

    except Exception as e:
        logger.error(f"❌ DB 조회 및 Resample 테스트 실패: {e}")
        return False

    finally:
        db.close()


def main():
    """메인 실행"""
    logger.info("=" * 80)
    logger.info("🧪 Resample 유틸리티 테스트 시작")
    logger.info("=" * 80)

    tests = [
        ("기본 Resample", test_resample_basic),
        ("여러 시간대 Resample", test_multiple_timeframes),
        ("Timeframe 매핑", test_common_timeframes),
        ("Timeframe 유효성 검사", test_validate_timeframe),
        ("DB 조회 및 Resample", test_fetch_and_resample),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                logger.error(f"❌ {name} 실패")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {name} 에러: {e}", exc_info=True)

    logger.info("\n" + "=" * 80)
    logger.info("📊 테스트 결과")
    logger.info("=" * 80)
    logger.info(f"총 테스트: {len(tests)}개")
    logger.info(f"통과: {passed}개")
    logger.info(f"실패: {failed}개")

    if failed == 0:
        logger.info("\n✅ 모든 테스트 통과!")
    else:
        logger.error(f"\n❌ {failed}개 테스트 실패")

    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
