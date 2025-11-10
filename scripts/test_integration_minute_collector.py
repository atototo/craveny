"""
1분봉 수집 시스템 통합 테스트

SK하이닉스(000660) 1분봉 데이터 수집 및 Resample까지 전 과정 검증

Usage:
    KIS_MOCK_MODE=False uv run python scripts/test_integration_minute_collector.py
"""
import asyncio
import logging
from datetime import datetime, timedelta

import pandas as pd

from backend.crawlers.kis_client import KISClient
from backend.db.session import SessionLocal
from backend.db.models.stock import StockPriceMinute
from backend.utils.resample import resample_to_multiple_timeframes
from backend.utils.market_hours import is_market_open


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_api_collection():
    """API 1분봉 수집 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 Step 1: API 1분봉 수집 테스트 (SK하이닉스)")
    logger.info("=" * 80)

    try:
        client = KISClient()
        stock_code = "000660"  # SK하이닉스

        logger.info(f"\n📊 종목: {stock_code} (SK하이닉스)")
        logger.info(f"장 상태: {'✅ 열림' if is_market_open() else '⏸️  닫힘'}")

        # API 호출
        logger.info("\n🔍 1분봉 데이터 조회 중...")
        response = await client.get_minute_prices(stock_code)

        if response.get("rt_cd") != "0":
            logger.error(f"❌ API 호출 실패: {response.get('msg1')}")
            return None

        output = response.get("output2", [])
        logger.info(f"✅ 조회 성공: {len(output)}건")

        if not output:
            logger.warning("⚠️  조회된 데이터가 없습니다")
            return None

        # 데이터 샘플 출력
        logger.info(f"\n📋 데이터 샘플 (첫 5개):")
        for i, item in enumerate(output[:5], 1):
            logger.info(
                f"  {i}. {item['stck_bsop_date']} {item['stck_cntg_hour']}: "
                f"종가={item['stck_prpr']:>8} 거래량={item['cntg_vol']:>10}"
            )

        return output

    except Exception as e:
        logger.error(f"❌ API 테스트 실패: {e}", exc_info=True)
        return None


async def test_db_save(data: list):
    """DB 저장 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("💾 Step 2: DB 저장 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        stock_code = "000660"
        saved_count = 0
        duplicate_count = 0

        logger.info(f"\n저장할 데이터: {len(data)}건")

        for item in data:
            # 날짜/시간 파싱
            date_str = item["stck_bsop_date"]  # YYYYMMDD
            time_str = item["stck_cntg_hour"]  # HHMMSS
            dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")

            # 중복 체크
            existing = db.query(StockPriceMinute).filter(
                StockPriceMinute.stock_code == stock_code,
                StockPriceMinute.datetime == dt
            ).first()

            if existing:
                duplicate_count += 1
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

        logger.info(f"\n✅ DB 저장 완료:")
        logger.info(f"  - 신규 저장: {saved_count}건")
        logger.info(f"  - 중복 스킵: {duplicate_count}건")

        return saved_count

    except Exception as e:
        db.rollback()
        logger.error(f"❌ DB 저장 실패: {e}", exc_info=True)
        return 0

    finally:
        db.close()


def test_db_query():
    """DB 조회 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Step 3: DB 조회 테스트")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        stock_code = "000660"

        # 최근 30분치 데이터 조회
        end_datetime = datetime.now()
        start_datetime = end_datetime - timedelta(minutes=30)

        query = db.query(StockPriceMinute).filter(
            StockPriceMinute.stock_code == stock_code,
            StockPriceMinute.datetime >= start_datetime,
            StockPriceMinute.datetime <= end_datetime
        ).order_by(StockPriceMinute.datetime.desc())

        rows = query.all()

        logger.info(f"\n조회 조건:")
        logger.info(f"  - 종목: {stock_code}")
        logger.info(f"  - 기간: 최근 30분")
        logger.info(f"\n✅ 조회 결과: {len(rows)}건")

        if rows:
            logger.info(f"\n📊 최근 데이터 (최신 5개):")
            for i, row in enumerate(rows[:5], 1):
                logger.info(
                    f"  {i}. {row.datetime}: "
                    f"종가={row.close:>8,.0f} 거래량={row.volume:>10,}"
                )

        return rows

    except Exception as e:
        logger.error(f"❌ DB 조회 실패: {e}", exc_info=True)
        return []

    finally:
        db.close()


def test_resample(rows: list):
    """Resample 테스트"""
    logger.info("\n" + "=" * 80)
    logger.info("📊 Step 4: Resample 테스트")
    logger.info("=" * 80)

    if len(rows) < 5:
        logger.warning(f"⚠️  데이터가 부족합니다 ({len(rows)}건)")
        logger.info("💡 더 많은 데이터를 수집한 후 테스트하세요")
        return

    try:
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
        df = df.sort_values('datetime')  # 시간순 정렬

        logger.info(f"\n원본 1분봉: {len(df)}건")
        logger.info(f"\n{df.head().to_string()}")

        # 여러 시간대로 Resample
        timeframes = ["3T", "5T", "10T"]
        results = resample_to_multiple_timeframes(df, timeframes)

        logger.info(f"\n📈 Resample 결과:")
        for timeframe, resampled_df in results.items():
            logger.info(f"\n  ▶ {timeframe} ({len(resampled_df)}건):")
            if len(resampled_df) > 0:
                logger.info(f"  {resampled_df.to_string()}")
            else:
                logger.info(f"    데이터 없음")

        # 5분봉 상세 검증
        if "5T" in results and len(results["5T"]) > 0:
            df_5min = results["5T"]
            logger.info(f"\n✅ 5분봉 검증:")
            logger.info(f"  - 생성된 5분봉: {len(df_5min)}건")
            logger.info(f"  - 가격 범위: {df_5min['low'].min():,.0f} ~ {df_5min['high'].max():,.0f}")
            logger.info(f"  - 총 거래량: {df_5min['volume'].sum():,}")

    except Exception as e:
        logger.error(f"❌ Resample 실패: {e}", exc_info=True)


def test_table_stats():
    """테이블 통계 확인"""
    logger.info("\n" + "=" * 80)
    logger.info("📊 Step 5: 테이블 통계")
    logger.info("=" * 80)

    db = SessionLocal()

    try:
        # 전체 데이터 건수
        total_count = db.query(StockPriceMinute).count()

        # SK하이닉스 데이터 건수
        sk_count = db.query(StockPriceMinute).filter(
            StockPriceMinute.stock_code == "000660"
        ).count()

        # 종목별 집계
        from sqlalchemy import func
        stock_stats = db.query(
            StockPriceMinute.stock_code,
            func.count(StockPriceMinute.id).label('count'),
            func.min(StockPriceMinute.datetime).label('oldest'),
            func.max(StockPriceMinute.datetime).label('latest')
        ).group_by(StockPriceMinute.stock_code).all()

        logger.info(f"\n전체 통계:")
        logger.info(f"  - 총 데이터: {total_count:,}건")
        logger.info(f"  - SK하이닉스: {sk_count:,}건")

        logger.info(f"\n종목별 통계:")
        for stat in stock_stats:
            logger.info(
                f"  - {stat.stock_code}: {stat.count:>6,}건 "
                f"({stat.oldest.strftime('%m-%d %H:%M')} ~ {stat.latest.strftime('%m-%d %H:%M')})"
            )

    except Exception as e:
        logger.error(f"❌ 통계 조회 실패: {e}", exc_info=True)

    finally:
        db.close()


async def main():
    """통합 테스트 메인"""
    logger.info("=" * 80)
    logger.info("🚀 1분봉 수집 시스템 통합 테스트")
    logger.info("=" * 80)

    start_time = datetime.now()

    try:
        # Step 1: API 수집
        data = await test_api_collection()

        if not data:
            logger.warning("\n⚠️  API 테스트 실패 - 나머지 테스트 스킵")
            return

        # Step 2: DB 저장
        saved_count = await test_db_save(data)

        # Step 3: DB 조회
        rows = test_db_query()

        # Step 4: Resample
        test_resample(rows)

        # Step 5: 테이블 통계
        test_table_stats()

        # 소요 시간
        elapsed = datetime.now() - start_time

        logger.info("\n" + "=" * 80)
        logger.info("📊 테스트 결과 요약")
        logger.info("=" * 80)
        logger.info(f"  - API 조회: {len(data)}건")
        logger.info(f"  - DB 저장: {saved_count}건")
        logger.info(f"  - DB 조회: {len(rows)}건")
        logger.info(f"  - 소요 시간: {elapsed.total_seconds():.1f}초")

        logger.info("\n✅ 통합 테스트 완료!")

    except Exception as e:
        logger.error(f"❌ 테스트 실패: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
