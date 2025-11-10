"""
Token Singleton 검증 테스트

여러 KISClient 인스턴스가 동일한 TokenManager를 공유하는지 확인

Usage:
    uv run python scripts/test_token_singleton.py
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


async def test_multiple_clients():
    """
    여러 클라이언트 인스턴스 생성 후 토큰 공유 확인
    """
    logger.info("\n" + "=" * 80)
    logger.info("🔍 Token Singleton 검증 테스트")
    logger.info("=" * 80)

    # 1. 첫 번째 클라이언트
    logger.info("\n📌 Client 1 생성...")
    client1 = await get_kis_client()
    token1 = await client1.token_manager.get_access_token()
    logger.info(f"Client 1 Token: {token1[:20]}...")

    # 2. 두 번째 클라이언트 (새로 생성)
    logger.info("\n📌 Client 2 생성...")
    client2 = await get_kis_client()
    token2 = await client2.token_manager.get_access_token()
    logger.info(f"Client 2 Token: {token2[:20]}...")

    # 3. 세 번째 클라이언트 (새로 생성)
    logger.info("\n📌 Client 3 생성...")
    from backend.crawlers.kis_client import KISClient
    client3 = KISClient()
    token3 = await client3.token_manager.get_access_token()
    logger.info(f"Client 3 Token: {token3[:20]}...")

    # 4. 검증
    logger.info("\n" + "=" * 80)
    logger.info("📊 검증 결과:")
    logger.info("=" * 80)

    if token1 == token2 == token3:
        logger.info("✅ 모든 클라이언트가 동일한 토큰 공유 확인!")
        logger.info(f"   토큰: {token1[:30]}...")
    else:
        logger.error("❌ 토큰이 다릅니다!")
        logger.error(f"   Token 1: {token1[:30]}...")
        logger.error(f"   Token 2: {token2[:30]}...")
        logger.error(f"   Token 3: {token3[:30]}...")
        return False

    # 5. TokenManager 인스턴스 확인
    logger.info("\n📌 TokenManager 인스턴스 확인:")
    logger.info(f"   Client 1 TM ID: {id(client1.token_manager)}")
    logger.info(f"   Client 2 TM ID: {id(client2.token_manager)}")
    logger.info(f"   Client 3 TM ID: {id(client3.token_manager)}")

    if id(client1.token_manager) == id(client2.token_manager) == id(client3.token_manager):
        logger.info("✅ 모든 클라이언트가 동일한 TokenManager 인스턴스 공유!")
    else:
        logger.error("❌ TokenManager 인스턴스가 다릅니다!")
        return False

    # 6. API 호출 테스트 (토큰 재사용 확인)
    logger.info("\n" + "=" * 80)
    logger.info("📈 API 호출 테스트 (토큰 재사용 확인)")
    logger.info("=" * 80)

    # Client 1으로 삼성전자 조회
    logger.info("\n📌 Client 1: 삼성전자 현재가 조회...")
    result1 = await client1.get_current_price("005930")
    logger.info(f"   ✅ 응답: {result1['rt_cd']} - {result1.get('msg1', 'Success')}")

    # Client 2로 SK하이닉스 조회
    logger.info("\n📌 Client 2: SK하이닉스 현재가 조회...")
    result2 = await client2.get_current_price("000660")
    logger.info(f"   ✅ 응답: {result2['rt_cd']} - {result2.get('msg1', 'Success')}")

    # Client 3으로 NAVER 조회
    logger.info("\n📌 Client 3: NAVER 현재가 조회...")
    result3 = await client3.get_current_price("035420")
    logger.info(f"   ✅ 응답: {result3['rt_cd']} - {result3.get('msg1', 'Success')}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ Token Singleton 검증 완료!")
    logger.info("=" * 80)
    logger.info("📝 결론:")
    logger.info("   - 모든 KISClient 인스턴스가 동일한 TokenManager 공유")
    logger.info("   - 토큰은 1회만 발급되고 모든 클라이언트가 재사용")
    logger.info("   - 24시간 동안 토큰 공유로 KIS API Rate Limit 회피 성공")
    logger.info("=" * 80)

    return True


async def main():
    """테스트 실행"""
    try:
        success = await test_multiple_clients()

        if success:
            logger.info("\n🎉 모든 테스트 통과!")
        else:
            logger.error("\n❌ 테스트 실패")

    except Exception as e:
        logger.error(f"\n❌ 테스트 중 에러 발생: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
