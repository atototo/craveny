"""
일별 1분봉 API 테스트 및 Resample 실습

과거 일자의 1분봉 데이터를 조회하고 Resample 유틸을 테스트합니다.

Usage:
    KIS_MOCK_MODE=False uv run python scripts/test_daily_minute_api.py
"""
import asyncio
import logging
from datetime import datetime, timedelta

import pandas as pd

from backend.crawlers.kis_client import KISClient
from backend.db.session import SessionLocal
from backend.db.models.stock import StockPriceMinute
from backend.utils.resample import (
    resample_ohlcv,
    resample_to_multiple_timeframes
)


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_daily_minute_api():
    """일별 1분봉 API 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 일별 1분봉 API 테스트")
    logger.info("=" * 80)

    try:
        # KIS Client 초기화
        client = KISClient()

        # 테스트 파라미터
        stock_code = "005930"  # 삼성전자
        # 어제 날짜 사용 (주말이면 금요일)
        yesterday = datetime.now() - timedelta(days=1)
        while yesterday.weekday() >= 5:  # 주말이면 하루씩 더 이전으로
            yesterday -= timedelta(days=1)
        target_date = yesterday.strftime("%Y%m%d")
        start_time = "090000"  # 09:00:00

        logger.info(f"\n📊 조회 정보:")
        logger.info(f"  - 종목: {stock_code} (삼성전자)")
        logger.info(f"  - 일자: {target_date}")
        logger.info(f"  - 시작 시간: {start_time}")

        # API 호출
        logger.info(f"\n🔍 일별 1분봉 데이터 조회 중...")
        response = await client.get_daily_minute_prices(
            stock_code=stock_code,
            target_date=target_date,
            start_time=start_time
        )

        # 응답 확인
        if response.get("rt_cd") != "0":
            logger.error(f"❌ API 호출 실패: {response.get('msg1')}")
            return None

        output = response.get("output2", [])
        logger.info(f"\n✅ 조회 성공: {len(output)}건")

        if not output:
            logger.warning("⚠️  조회된 데이터가 없습니다")
            return None

        # 데이터 샘플 출력 (첫 5개, 마지막 5개)
        logger.info(f"\n📋 데이터 샘플 (첫 5개):")
        for i, item in enumerate(output[:5], 1):
            logger.info(
                f"  {i}. {item['stck_bsop_date']} {item['stck_cntg_hour']}: "
                f"시가={item['stck_oprc']:>8} 고가={item['stck_hgpr']:>8} "
                f"저가={item['stck_lwpr']:>8} 종가={item['stck_prpr']:>8} "
                f"거래량={item['cntg_vol']:>10}"
            )

        if len(output) > 10:
            logger.info(f"\n📋 데이터 샘플 (마지막 5개):")
            for i, item in enumerate(output[-5:], len(output) - 4):
                logger.info(
                    f"  {i}. {item['stck_bsop_date']} {item['stck_cntg_hour']}: "
                    f"시가={item['stck_oprc']:>8} 고가={item['stck_hgpr']:>8} "
                    f"저가={item['stck_lwpr']:>8} 종가={item['stck_prpr']:>8} "
                    f"거래량={item['cntg_vol']:>10}"
                )

        return output

    except ValueError as e:
        logger.error(f"❌ API 호출 실패: {e}")
        logger.info("💡 일별 1분봉 API는 실전투자 전용입니다 (KIS_MOCK_MODE=False)")
        return None

    except Exception as e:
        logger.error(f"❌ 예상치 못한 에러: {e}", exc_info=True)
        return None


async def save_to_db_and_resample(data: list):
    """DB 저장 및 Resample 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("💾 DB 저장 및 Resample 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 1. 데이터 변환 및 DB 저장
        logger.info("\n1️⃣ 데이터 변환 및 DB 저장")

        stock_code = "005930"
        saved_count = 0

        for item in data:
            # 날짜/시간 파싱
            date_str = item["stck_bsop_date"]  # YYYYMMDD
            time_str = item["stck_cntg_hour"]  # HHMMSS

            dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")

            # DB 중복 체크
            existing = db.query(StockPriceMinute).filter(
                StockPriceMinute.stock_code == stock_code,
                StockPriceMinute.datetime == dt
            ).first()

            if existing:
                continue

            # 저장
            record = StockPriceMinute(
                stock_code=stock_code,
                datetime=dt,
                open=int(item["stck_oprc"]),
                high=int(item["stck_hgpr"]),
                low=int(item["stck_lwpr"]),
                close=int(item["stck_prpr"]),
                volume=int(item["cntg_vol"]),
            )
            db.add(record)
            saved_count += 1

        db.commit()
        logger.info(f"✅ DB 저장 완료: {saved_count}건 (중복 {len(data) - saved_count}건 스킵)")

        # 2. DB 조회
        logger.info("\n2️⃣ DB에서 저장된 데이터 조회")

        # 날짜 범위 계산
        date_obj = datetime.strptime(data[0]["stck_bsop_date"], "%Y%m%d")
        start_datetime = date_obj.replace(hour=9, minute=0, second=0)
        end_datetime = date_obj.replace(hour=15, minute=30, second=0)

        query = db.query(StockPriceMinute).filter(
            StockPriceMinute.stock_code == stock_code,
            StockPriceMinute.datetime >= start_datetime,
            StockPriceMinute.datetime <= end_datetime
        ).order_by(StockPriceMinute.datetime)

        rows = query.all()
        logger.info(f"✅ 조회 완료: {len(rows)}건")

        if not rows:
            logger.warning("⚠️  조회된 데이터가 없습니다")
            return

        # 3. DataFrame 변환
        logger.info("\n3️⃣ DataFrame 변환")

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
        logger.info(f"✅ DataFrame 생성: {len(df)}건")
        logger.info(f"\n{df.head().to_string()}")

        # 4. 여러 시간대로 Resample
        logger.info("\n4️⃣ 여러 시간대로 Resample")

        timeframes = ["3T", "5T", "10T", "30T", "60T"]
        results = resample_to_multiple_timeframes(df, timeframes)

        logger.info("\nResample 결과:")
        for timeframe, resampled_df in results.items():
            logger.info(f"\n  📊 {timeframe} ({len(resampled_df)}건):")
            logger.info(f"  {resampled_df.head(3).to_string()}")

        # 5. 5분봉 상세 확인
        logger.info("\n5️⃣ 5분봉 상세 확인")

        df_5min = results["5T"]
        logger.info(f"\n5분봉 데이터 (총 {len(df_5min)}건):")
        logger.info(f"\n{df_5min.to_string()}")

        # 통계
        logger.info("\n📊 5분봉 통계:")
        logger.info(f"  - 시가 범위: {df_5min['open'].min():,} ~ {df_5min['open'].max():,}")
        logger.info(f"  - 고가 범위: {df_5min['high'].min():,} ~ {df_5min['high'].max():,}")
        logger.info(f"  - 저가 범위: {df_5min['low'].min():,} ~ {df_5min['low'].max():,}")
        logger.info(f"  - 종가 범위: {df_5min['close'].min():,} ~ {df_5min['close'].max():,}")
        logger.info(f"  - 총 거래량: {df_5min['volume'].sum():,}")

        logger.info("\n✅ Resample 테스트 완료!")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 에러 발생: {e}", exc_info=True)

    finally:
        db.close()


async def main():
    """메인 실행"""
    logger.info("=" * 80)
    logger.info("🚀 일별 1분봉 API & Resample 통합 테스트")
    logger.info("=" * 80)

    start_time = datetime.now()

    try:
        # 1. API 테스트
        data = await test_daily_minute_api()

        if not data:
            logger.warning("\n⚠️  API 테스트 실패 - Resample 테스트 스킵")
            return

        # 2. DB 저장 및 Resample
        await save_to_db_and_resample(data)

        # 소요 시간
        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️  총 소요 시간: {elapsed.total_seconds():.1f}초")

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테스트 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
