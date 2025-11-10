"""
KIS API 1분봉 조회 테스트

Usage:
    uv run python scripts/test_kis_minute_api.py
"""
import asyncio
import logging
from datetime import datetime

from backend.crawlers.kis_client import get_kis_client


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_get_minute_prices():
    """1분봉 조회 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 KIS API 1분봉 조회 테스트")
    logger.info("=" * 80)

    # 삼성전자 (005930)
    stock_code = "005930"

    try:
        # KIS Client 생성
        client = await get_kis_client()
        logger.info(f"📊 종목: {stock_code} (삼성전자)")

        # 1분봉 조회
        logger.info("\n1. 1분봉 데이터 조회 중...")
        result = await client.get_minute_prices(stock_code=stock_code)

        # 전체 응답 출력 (디버깅용)
        logger.info(f"\n   전체 응답: {result}")

        # 응답 확인
        rt_cd = result.get("rt_cd")
        logger.info(f"\n   응답 코드: {rt_cd}")

        if rt_cd == "0":
            logger.info("   ✅ API 호출 성공")

            # output1 확인
            output1 = result.get("output1", {})
            logger.info(f"   상품 타입: {output1.get('prdt_type_cd')}")

            # output2 확인 (1분봉 데이터)
            output2 = result.get("output2", [])
            logger.info(f"   수신 데이터 건수: {len(output2)}건")

            if output2:
                logger.info("\n2. 최근 1분봉 데이터 샘플:")
                for i, bar in enumerate(output2[:5]):  # 최근 5개만 출력
                    date = bar.get("stck_bsop_date")
                    time = bar.get("stck_cntg_hour")
                    open_price = bar.get("stck_oprc")
                    high_price = bar.get("stck_hgpr")
                    low_price = bar.get("stck_lwpr")
                    close_price = bar.get("stck_prpr")
                    volume = bar.get("cntg_vol")

                    # datetime 파싱
                    dt_str = f"{date} {time[:2]}:{time[2:4]}:{time[4:6]}"
                    logger.info(
                        f"   [{i+1}] {dt_str}: "
                        f"시가 {open_price}, 고가 {high_price}, "
                        f"저가 {low_price}, 종가 {close_price}, "
                        f"거래량 {volume}"
                    )

                logger.info("\n3. 데이터 필드 확인:")
                first_bar = output2[0]
                logger.info(f"   사용 가능 필드: {list(first_bar.keys())}")

            else:
                logger.warning("   ⚠️  1분봉 데이터 없음 (장 시간 외일 수 있음)")

        else:
            msg = result.get("msg1", "Unknown error")
            logger.error(f"   ❌ API 호출 실패: {msg}")
            return False

        logger.info("\n" + "=" * 80)
        logger.info("✅ 테스트 완료!")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        return False


async def main():
    """메인 실행"""
    start_time = datetime.now()

    try:
        success = await test_get_minute_prices()

        # 소요 시간 계산
        elapsed = datetime.now() - start_time
        logger.info(f"\n⏱️  소요 시간: {elapsed.total_seconds():.1f}초")

        if success:
            logger.info("✅ 모든 테스트 통과!")
        else:
            logger.error("❌ 테스트 실패")

    except Exception as e:
        logger.error(f"❌ 실행 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
