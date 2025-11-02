"""
텔레그램 알림 테스트 스크립트

텔레그램 봇 연결 및 메시지 전송을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from backend.notifications.telegram import get_telegram_notifier
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_connection():
    """텔레그램 봇 연결 테스트"""
    logger.info("=" * 70)
    logger.info("🔌 텔레그램 봇 연결 테스트")
    logger.info("=" * 70)

    notifier = get_telegram_notifier()

    if notifier.test_connection():
        logger.info("✅ 텔레그램 봇 연결 성공")
        return True
    else:
        logger.error("❌ 텔레그램 봇 연결 실패")
        return False


def test_simple_message():
    """간단한 메시지 전송 테스트"""
    logger.info("=" * 70)
    logger.info("💬 간단한 메시지 전송 테스트")
    logger.info("=" * 70)

    notifier = get_telegram_notifier()

    message = """
🤖 **Craveny 테스트 메시지**

텔레그램 봇 연동이 정상적으로 작동합니다!

✅ 메시지 전송 성공
📅 테스트 시각: 2025-11-01
"""

    if notifier.send_message(message.strip()):
        logger.info("✅ 메시지 전송 성공")
        return True
    else:
        logger.error("❌ 메시지 전송 실패")
        return False


def test_prediction_message():
    """예측 결과 메시지 전송 테스트"""
    logger.info("=" * 70)
    logger.info("📊 예측 결과 메시지 전송 테스트")
    logger.info("=" * 70)

    db = SessionLocal()
    notifier = get_telegram_notifier()

    try:
        # 실제 뉴스 가져오기
        sample_news = (
            db.query(NewsArticle)
            .filter(NewsArticle.stock_code.isnot(None))
            .first()
        )

        if not sample_news:
            logger.warning("⚠️  테스트할 뉴스가 없습니다")
            return False

        # 가상 예측 결과
        prediction = {
            "prediction": "상승",
            "confidence": 85,
            "reasoning": "과거 유사 뉴스에서 T+5일 7.8% 상승 패턴이 확인되었습니다. "
            "기술적 혁신이 시장에서 긍정적으로 받아들여질 것으로 예상됩니다.",
            "short_term": "T+1일: 2.5% 상승 예상",
            "medium_term": "T+3일: 5.3% 상승 예상",
            "long_term": "T+5일: 7.8% 상승 예상",
            "similar_count": 2,
            "model": "gpt-4o",
            "timestamp": "2025-11-01T15:00:00",
        }

        logger.info(f"📰 테스트 뉴스: {sample_news.title[:50]}...")
        logger.info(f"🏢 종목: {sample_news.stock_code}")
        logger.info("")

        if notifier.send_prediction(
            news_title=sample_news.title,
            stock_code=sample_news.stock_code,
            prediction=prediction,
        ):
            logger.info("✅ 예측 결과 메시지 전송 성공")
            return True
        else:
            logger.error("❌ 예측 결과 메시지 전송 실패")
            return False

    finally:
        db.close()


def main():
    """메인 실행 함수"""
    logger.info("🚀 텔레그램 알림 테스트 시작")
    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. 연결 테스트
    tests_total += 1
    if test_connection():
        tests_passed += 1
    else:
        logger.error("❌ 연결 실패로 다음 테스트 건너뜀")
        sys.exit(1)

    logger.info("")

    # 2. 간단한 메시지
    tests_total += 1
    if test_simple_message():
        tests_passed += 1

    logger.info("")

    # 3. 예측 결과 메시지
    tests_total += 1
    if test_prediction_message():
        tests_passed += 1

    # 결과 출력
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"✅ 테스트 결과: {tests_passed}/{tests_total}개 통과")
    logger.info("=" * 70)

    if tests_passed == tests_total:
        logger.info("🎉 모든 테스트 통과!")
        logger.info("")
        logger.info("💡 텔레그램 앱에서 메시지를 확인하세요!")
        sys.exit(0)
    else:
        logger.error(f"❌ {tests_total - tests_passed}개 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
