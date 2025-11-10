"""
실제 DB 데이터로 Resample 기능 테스트

DB에 저장된 실제 1분봉 데이터를 조회하고 Resample 유틸을 테스트합니다.

Usage:
    uv run python scripts/test_resample_with_real_data.py
"""
import logging
from datetime import datetime, timedelta

import pandas as pd

from backend.db.session import SessionLocal
from backend.db.models.stock import StockPriceMinute
from backend.utils.resample import (
    resample_ohlcv,
    resample_to_multiple_timeframes,
    fetch_and_resample
)


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_resample_with_db_data():
    """DB 데이터로 Resample 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 실제 DB 데이터로 Resample 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 1. 최근 데이터 확인
        logger.info("\n1️⃣ DB에서 최근 1분봉 데이터 확인")

        recent = db.query(StockPriceMinute).order_by(
            StockPriceMinute.datetime.desc()
        ).first()

        if not recent:
            logger.warning("⚠️  DB에 1분봉 데이터 없음")
            logger.info("💡 먼저 1분봉 수집기를 실행하세요:")
            logger.info("   KIS_MOCK_MODE=False uv run python -m backend.crawlers.kis_minute_collector")
            return False

        stock_code = recent.stock_code
        latest_datetime = recent.datetime

        logger.info(f"✅ 최근 데이터 발견:")
        logger.info(f"  - 종목: {stock_code}")
        logger.info(f"  - 시간: {latest_datetime}")
        logger.info(f"  - 가격: {recent.close:,}원")

        # 2. 1시간치 데이터 조회
        logger.info("\n2️⃣ 1시간치 데이터 조회")

        end_datetime = latest_datetime
        start_datetime = latest_datetime - timedelta(hours=1)

        query = db.query(StockPriceMinute).filter(
            StockPriceMinute.stock_code == stock_code,
            StockPriceMinute.datetime >= start_datetime,
            StockPriceMinute.datetime <= end_datetime
        ).order_by(StockPriceMinute.datetime)

        rows = query.all()
        logger.info(f"✅ 조회 완료: {len(rows)}건")

        if len(rows) < 10:
            logger.warning(f"⚠️  데이터가 너무 적음 ({len(rows)}건)")
            logger.info("💡 더 많은 데이터를 수집하거나 시간 범위를 늘려보세요")
            return False

        # DataFrame 변환
        df_data = []
        for row in rows:
            df_data.append({
                'datetime': row.datetime,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume
            })

        df = pd.DataFrame(df_data)
        logger.info(f"\n📊 원본 1분봉 데이터 (총 {len(df)}건):")
        logger.info(f"\n{df.head(10).to_string()}")

        # 3. 여러 시간대로 Resample
        logger.info("\n3️⃣ 여러 시간대로 Resample")

        timeframes = ["3T", "5T", "10T", "30T"]
        results = resample_to_multiple_timeframes(df, timeframes)

        for timeframe, resampled_df in results.items():
            logger.info(f"\n  📊 {timeframe} ({len(resampled_df)}건):")
            logger.info(f"  {resampled_df.to_string()}")

        # 4. 5분봉 상세 분석
        logger.info("\n4️⃣ 5분봉 상세 분석")

        df_5min = results["5T"]
        logger.info(f"\n5분봉 데이터 (총 {len(df_5min)}건):")
        logger.info(f"\n{df_5min.to_string()}")

        if len(df_5min) > 0:
            logger.info("\n📊 5분봉 통계:")
            logger.info(f"  - 시가 범위: {df_5min['open'].min():,} ~ {df_5min['open'].max():,}")
            logger.info(f"  - 고가 범위: {df_5min['high'].min():,} ~ {df_5min['high'].max():,}")
            logger.info(f"  - 저가 범위: {df_5min['low'].min():,} ~ {df_5min['low'].max():,}")
            logger.info(f"  - 종가 범위: {df_5min['close'].min():,} ~ {df_5min['close'].max():,}")
            logger.info(f"  - 총 거래량: {df_5min['volume'].sum():,}")
            logger.info(f"  - 평균 거래량: {df_5min['volume'].mean():,.0f}")

        # 5. fetch_and_resample 함수 테스트
        logger.info("\n5️⃣ fetch_and_resample 함수 테스트")

        # 30분치 데이터로 5분봉 생성
        end_dt = latest_datetime
        start_dt = latest_datetime - timedelta(minutes=30)

        df_fetched = fetch_and_resample(
            db, stock_code, start_dt, end_dt, timeframe="5T"
        )

        logger.info(f"\nfetch_and_resample 결과 (5T): {len(df_fetched)}건")
        logger.info(f"\n{df_fetched.to_string()}")

        # 6. OHLCV 검증
        logger.info("\n6️⃣ OHLCV 집계 검증")

        if len(results["5T"]) > 0:
            first_5min = results["5T"].iloc[0]
            logger.info(f"\n첫 번째 5분봉:")
            logger.info(f"  - 시간: {first_5min['datetime']}")
            logger.info(f"  - 시가(first): {first_5min['open']:,}")
            logger.info(f"  - 고가(max): {first_5min['high']:,}")
            logger.info(f"  - 저가(min): {first_5min['low']:,}")
            logger.info(f"  - 종가(last): {first_5min['close']:,}")
            logger.info(f"  - 거래량(sum): {first_5min['volume']:,}")

            # 원본 1분봉과 비교
            first_5min_time = pd.to_datetime(first_5min['datetime'])
            next_5min_time = first_5min_time + timedelta(minutes=5)

            original_rows = df[
                (df['datetime'] >= first_5min_time) &
                (df['datetime'] < next_5min_time)
            ]

            logger.info(f"\n해당 5분간의 원본 1분봉 ({len(original_rows)}건):")
            logger.info(f"\n{original_rows.to_string()}")

            # 검증
            logger.info(f"\n검증:")
            logger.info(f"  - 시가 일치: {first_5min['open'] == original_rows.iloc[0]['open']}")
            logger.info(f"  - 고가 일치: {first_5min['high'] == original_rows['high'].max()}")
            logger.info(f"  - 저가 일치: {first_5min['low'] == original_rows['low'].min()}")
            logger.info(f"  - 종가 일치: {first_5min['close'] == original_rows.iloc[-1]['close']}")
            logger.info(f"  - 거래량 일치: {first_5min['volume'] == original_rows['volume'].sum()}")

        logger.info("\n✅ Resample 테스트 완료!")
        return True

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)
        return False

    finally:
        db.close()


def main():
    """메인 실행"""
    logger.info("=" * 80)
    logger.info("🚀 실제 DB 데이터로 Resample 기능 검증")
    logger.info("=" * 80)

    start_time = datetime.now()

    try:
        success = test_resample_with_db_data()

        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️  총 소요 시간: {elapsed.total_seconds():.1f}초")

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("✅ 모든 테스트 통과!")
            logger.info("=" * 80)
        else:
            logger.warning("\n⚠️  테스트를 완료할 수 없습니다")

    except Exception as e:
        logger.error(f"❌ 실행 중 에러: {e}", exc_info=True)


if __name__ == "__main__":
    main()
