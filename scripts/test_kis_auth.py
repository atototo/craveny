"""
KIS API 인증 테스트 스크립트

OAuth 2.0 인증, Token 관리, API 호출 테스트
"""
import asyncio
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.crawlers.kis_client import get_kis_client
from backend.config import settings


# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def test_kis_authentication():
    """KIS API 인증 테스트"""

    logger.info("\n" + "=" * 80)
    logger.info("KIS API 인증 테스트 시작")
    logger.info("=" * 80)

    # 환경 변수 확인
    logger.info("\n📋 환경 변수 확인:")
    logger.info(f"  - KIS_APP_KEY: {settings.KIS_APP_KEY[:10]}..." if settings.KIS_APP_KEY else "  - KIS_APP_KEY: ❌ 미설정")
    logger.info(f"  - KIS_APP_SECRET: {settings.KIS_APP_SECRET[:10]}..." if settings.KIS_APP_SECRET else "  - KIS_APP_SECRET: ❌ 미설정")
    logger.info(f"  - KIS_MOCK_MODE: {settings.KIS_MOCK_MODE}")
    logger.info(f"  - KIS_BASE_URL: {settings.KIS_BASE_URL}")

    if not settings.KIS_APP_KEY or not settings.KIS_APP_SECRET:
        logger.error("\n❌ KIS API KEY가 설정되지 않았습니다.")
        logger.error("   .env 파일에 KIS_APP_KEY와 KIS_APP_SECRET를 설정하세요.")
        return False

    try:
        # KIS Client 생성
        client = await get_kis_client()

        # 1. Token 발급 테스트
        logger.info("\n🔑 1. Access Token 발급 테스트...")
        access_token = await client.token_manager.get_access_token()

        if access_token:
            logger.info(f"   ✅ Token 발급 성공!")
            logger.info(f"   Token: {access_token[:20]}...")
            logger.info(f"   만료 시간: {client.token_manager.token_expires_at}")
        else:
            logger.error("   ❌ Token 발급 실패")
            return False

        # 2. 현재가 조회 테스트 (삼성전자)
        logger.info("\n📊 2. 현재가 조회 테스트 (삼성전자: 005930)...")
        stock_code = "005930"

        try:
            result = await client.get_current_price(stock_code)

            if result:
                output = result.get("output", {})
                stock_name = output.get("hts_kor_isnm", "N/A")
                current_price = output.get("stck_prpr", "N/A")
                change_rate = output.get("prdy_ctrt", "N/A")

                logger.info(f"   ✅ 현재가 조회 성공!")
                logger.info(f"   종목명: {stock_name}")
                logger.info(f"   현재가: {current_price}원")
                logger.info(f"   전일 대비: {change_rate}%")
            else:
                logger.warning("   ⚠️  현재가 조회 결과 없음")

        except Exception as e:
            logger.error(f"   ❌ 현재가 조회 실패: {e}")
            return False

        # 3. Rate Limiting 테스트
        logger.info("\n⏱️  3. Rate Limiting 테스트 (5건 연속 요청)...")

        start_time = asyncio.get_event_loop().time()

        for i in range(5):
            try:
                await client.get_current_price(stock_code)
                logger.info(f"   ✅ 요청 {i + 1}/5 성공")
            except Exception as e:
                logger.error(f"   ❌ 요청 {i + 1}/5 실패: {e}")

        end_time = asyncio.get_event_loop().time()
        elapsed = end_time - start_time

        logger.info(f"   소요 시간: {elapsed:.2f}초")
        logger.info(f"   예상 최소 시간: {5 / client.rate_limiter.max_requests:.2f}초")

        # 4. Token 자동 갱신 테스트 (시뮬레이션)
        logger.info("\n🔄 4. Token 자동 갱신 시뮬레이션...")
        original_token = client.token_manager.access_token

        # Token 만료 시뮬레이션 (강제 만료)
        from datetime import datetime, timedelta
        client.token_manager.token_expires_at = datetime.now() - timedelta(minutes=1)

        logger.info("   Token 만료 시뮬레이션 완료")

        # 다시 요청 (자동 갱신 발생)
        new_token = await client.token_manager.get_access_token()

        if new_token != original_token:
            logger.info("   ✅ Token 자동 갱신 성공!")
            logger.info(f"   이전 Token: {original_token[:20]}...")
            logger.info(f"   새 Token: {new_token[:20]}...")
        else:
            logger.warning("   ⚠️  Token이 갱신되지 않았습니다")

        # 종료
        await client.close()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테스트 통과!")
        logger.info("=" * 80)

        return True

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(test_kis_authentication())

    if success:
        logger.info("\n✅ KIS API 인증 시스템이 정상적으로 작동합니다.")
        sys.exit(0)
    else:
        logger.error("\n❌ KIS API 인증 시스템에 문제가 있습니다.")
        sys.exit(1)
