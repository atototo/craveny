"""
Redis 기반 토큰 저장소 테스트

Usage:
    uv run python scripts/test_redis_token.py
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


async def test_redis_token():
    """Redis 토큰 저장소 테스트"""
    logger.info("=" * 80)
    logger.info("🧪 Redis 토큰 저장소 테스트")
    logger.info("=" * 80)

    try:
        # 첫 번째 클라이언트 생성
        logger.info("\n1. 첫 번째 KIS Client 생성...")
        client1 = await get_kis_client()

        logger.info("\n2. API 호출 (일봉 조회)...")
        result1 = await client1.get_daily_prices(
            stock_code="005930",
            start_date=datetime(2025, 11, 1)
        )
        logger.info(f"   ✅ API 호출 성공 (데이터 건수: {len(result1.get('output2', []))}건)")

        # 두 번째 클라이언트 생성 (토큰 재사용 확인)
        logger.info("\n3. 두 번째 KIS Client 생성 (토큰 재사용 확인)...")
        from backend.crawlers.kis_client import KISClient
        client2 = KISClient()

        logger.info("\n4. 두 번째 클라이언트로 API 호출...")
        result2 = await client2.get_daily_prices(
            stock_code="000660",  # SK하이닉스
            start_date=datetime(2025, 11, 1)
        )
        logger.info(f"   ✅ API 호출 성공 (데이터 건수: {len(result2.get('output2', []))}건)")

        logger.info("\n5. Redis 저장 확인...")
        import redis
        from backend.config import settings

        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        token = redis_client.get("kis:access_token")
        expiry = redis_client.get("kis:token_expires_at")
        token_ttl = redis_client.ttl("kis:access_token")

        logger.info(f"   토큰: {token[:50] if token else None}...")
        logger.info(f"   만료 시간: {expiry}")
        logger.info(f"   남은 TTL: {token_ttl}초 ({token_ttl/3600:.1f}시간)")

        if token and expiry:
            logger.info("   ✅ Redis에 토큰 저장 확인")
        else:
            logger.warning("   ⚠️  Redis에 토큰 없음")

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
        success = await test_redis_token()

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
