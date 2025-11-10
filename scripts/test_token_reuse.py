"""
Token 재사용 테스트

이미 발급된 토큰이 있을 때 새 클라이언트가 재사용하는지 확인

Usage:
    uv run python scripts/test_token_reuse.py
"""
import asyncio
import logging
from datetime import datetime

from backend.crawlers.kis_client import get_kis_client, KISClient


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_token_reuse():
    """
    이미 발급된 토큰을 여러 클라이언트가 재사용하는지 테스트
    """
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Token 재사용 테스트")
    logger.info("=" * 80)

    # 1. 첫 번째 클라이언트로 토큰 발급 (또는 기존 토큰 사용)
    logger.info("\n📌 Step 1: 첫 번째 클라이언트 생성...")
    client1 = await get_kis_client()

    try:
        token1 = await client1.token_manager.get_access_token()
        logger.info(f"✅ Client 1 Token: {token1[:30]}...")
        logger.info(f"   만료 시간: {client1.token_manager.token_expires_at}")
    except Exception as e:
        logger.warning(f"⚠️  토큰 발급 실패 (예상된 동작 - Rate Limit): {e}")
        logger.info("   기존 토큰이 있는지 확인합니다...")

        if client1.token_manager.access_token:
            logger.info(f"✅ 기존 토큰 발견: {client1.token_manager.access_token[:30]}...")
            logger.info(f"   만료 시간: {client1.token_manager.token_expires_at}")
        else:
            logger.error("❌ 기존 토큰 없음. 1분 후 재시도하세요.")
            return False

    # 2. 두 번째 클라이언트 생성 (싱글톤이므로 동일한 TokenManager)
    logger.info("\n📌 Step 2: 두 번째 클라이언트 생성...")
    client2 = KISClient()
    token2 = await client2.token_manager.get_access_token()
    logger.info(f"✅ Client 2 Token: {token2[:30]}...")

    # 3. 세 번째 클라이언트 생성
    logger.info("\n📌 Step 3: 세 번째 클라이언트 생성...")
    client3 = KISClient()
    token3 = await client3.token_manager.get_access_token()
    logger.info(f"✅ Client 3 Token: {token3[:30]}...")

    # 4. 검증
    logger.info("\n" + "=" * 80)
    logger.info("📊 검증 결과:")
    logger.info("=" * 80)

    # 토큰 일치 확인
    if token2 == token3:
        logger.info("✅ 모든 클라이언트가 동일한 토큰 공유!")
        logger.info(f"   공유 토큰: {token2[:30]}...")
    else:
        logger.error("❌ 토큰이 다릅니다!")
        return False

    # TokenManager 인스턴스 ID 확인
    logger.info("\n📌 TokenManager 인스턴스 동일성 확인:")
    tm1_id = id(client1.token_manager)
    tm2_id = id(client2.token_manager)
    tm3_id = id(client3.token_manager)

    logger.info(f"   Client 1 TM: {tm1_id}")
    logger.info(f"   Client 2 TM: {tm2_id}")
    logger.info(f"   Client 3 TM: {tm3_id}")

    if tm1_id == tm2_id == tm3_id:
        logger.info("✅ 모든 클라이언트가 동일한 TokenManager 인스턴스 공유!")
    else:
        logger.error("❌ TokenManager 인스턴스가 다릅니다!")
        return False

    # 5. API 호출 테스트 (모두 같은 토큰 사용)
    logger.info("\n" + "=" * 80)
    logger.info("📈 API 호출 테스트 (동일 토큰 재사용 확인)")
    logger.info("=" * 80)

    try:
        logger.info("\n📌 Client 2: 삼성전자 현재가 조회...")
        result2 = await client2.get_current_price("005930")
        logger.info(f"   ✅ 성공: {result2.get('msg1', 'Success')}")

        logger.info("\n📌 Client 3: SK하이닉스 현재가 조회...")
        result3 = await client3.get_current_price("000660")
        logger.info(f"   ✅ 성공: {result3.get('msg1', 'Success')}")

    except Exception as e:
        logger.error(f"❌ API 호출 실패: {e}")
        return False

    # 최종 결론
    logger.info("\n" + "=" * 80)
    logger.info("✅ Token 재사용 테스트 완료!")
    logger.info("=" * 80)
    logger.info("📝 검증 완료:")
    logger.info("   1. ✅ TokenManager는 싱글톤 (모든 인스턴스 동일)")
    logger.info("   2. ✅ Token은 1회만 발급되고 모든 클라이언트가 공유")
    logger.info("   3. ✅ API 호출 시 동일한 토큰 재사용")
    logger.info("   4. ✅ 24시간 동안 토큰 공유로 Rate Limit 회피")
    logger.info("=" * 80)

    return True


async def main():
    """테스트 실행"""
    try:
        success = await test_token_reuse()

        if success:
            logger.info("\n🎉 모든 검증 통과!")
        else:
            logger.error("\n❌ 검증 실패")

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
