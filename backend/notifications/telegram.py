"""
텔레그램 알림 모듈

텔레그램 봇을 통해 주가 예측 결과를 전송합니다.
"""
import logging
from typing import Dict, Any, Optional
import httpx

from backend.config import settings
from backend.utils.stock_mapping import get_stock_mapper
from backend.db.models.stock import StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    def __init__(self):
        """텔레그램 봇 초기화"""
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.stock_mapper = get_stock_mapper()

    def _get_current_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        현재 주가 정보를 조회합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            주가 정보 딕셔너리 또는 None
        """
        db = SessionLocal()
        try:
            # 최근 2일 데이터 조회 (변동률 계산용)
            recent_prices = (
                db.query(StockPrice)
                .filter(StockPrice.stock_code == stock_code)
                .order_by(StockPrice.date.desc())
                .limit(2)
                .all()
            )

            if not recent_prices:
                return None

            current = recent_prices[0]

            # 변동률 계산
            change_rate = 0.0
            if len(recent_prices) >= 2:
                previous = recent_prices[1]
                if previous.close > 0:
                    change_rate = ((current.close - previous.close) / previous.close) * 100

            return {
                "close": current.close,
                "change_rate": round(change_rate, 2),
                "volume": current.volume,
            }

        except Exception as e:
            logger.error(f"현재 주가 조회 실패 (종목코드: {stock_code}): {e}")
            return None
        finally:
            db.close()

    def _format_prediction_message(
        self,
        news_title: str,
        stock_code: str,
        prediction: Dict[str, Any],
    ) -> str:
        """
        예측 결과를 텔레그램 메시지 포맷으로 변환

        Args:
            news_title: 뉴스 제목
            stock_code: 종목 코드
            prediction: 예측 결과

        Returns:
            포맷된 메시지
        """
        # 예측 방향 이모지
        direction_emoji = {
            "상승": "📈",
            "하락": "📉",
            "유지": "➡️",
        }

        emoji = direction_emoji.get(prediction.get("prediction", "유지"), "❓")

        # 종목명 조회
        company_name = self.stock_mapper.get_company_name(stock_code)
        if company_name:
            stock_display = f"{company_name} ({stock_code})"
        else:
            stock_display = stock_code

        # 현재 주가 정보 조회
        stock_info = self._get_current_stock_info(stock_code)
        if stock_info:
            change_emoji = "📈" if stock_info["change_rate"] > 0 else "📉" if stock_info["change_rate"] < 0 else "➡️"
            current_price = f"{stock_info['close']:,.0f}원 ({change_emoji} {stock_info['change_rate']:+.2f}%)"
        else:
            current_price = "정보 없음"

        # 기간별 예측 간단 표시
        short_term = prediction.get('short_term', 'N/A')
        medium_term = prediction.get('medium_term', 'N/A')
        long_term = prediction.get('long_term', 'N/A')

        # 예측 근거 요약 (200자 제한)
        reasoning = prediction.get('reasoning', 'N/A')
        if len(reasoning) > 200:
            reasoning = reasoning[:200] + "..."

        message = f"""
{emoji} **주가 예측 알림** {emoji}

**📰 뉴스**
{news_title[:100]}{'...' if len(news_title) > 100 else ''}

**🏢 종목 정보**
{stock_display}
현재가: {current_price}

**📊 AI 예측**
{emoji} *{prediction.get('prediction', 'N/A')}* 예상

**📅 기간별 전망**
• 단기 (1일~1주): {short_term}
• 중기 (1주~1개월): {medium_term}
• 장기 (1개월 이상): {long_term}

**💡 예측 근거**
{reasoning}

_유사 뉴스 {prediction.get('similar_count', 0)}건 분석 | {prediction.get('model', 'N/A')}_
"""
        return message.strip()

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        텔레그램 메시지 전송

        Args:
            message: 전송할 메시지
            parse_mode: 파싱 모드 (Markdown, HTML)

        Returns:
            전송 성공 여부
        """
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }

            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)

            if response.status_code == 200:
                logger.info(f"텔레그램 메시지 전송 성공")
                return True
            else:
                logger.error(
                    f"텔레그램 메시지 전송 실패: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 오류: {e}", exc_info=True)
            return False

    def send_prediction(
        self,
        news_title: str,
        stock_code: str,
        prediction: Dict[str, Any],
    ) -> bool:
        """
        예측 결과를 텔레그램으로 전송

        Args:
            news_title: 뉴스 제목
            stock_code: 종목 코드
            prediction: 예측 결과

        Returns:
            전송 성공 여부
        """
        try:
            message = self._format_prediction_message(
                news_title=news_title,
                stock_code=stock_code,
                prediction=prediction,
            )

            return self.send_message(message)

        except Exception as e:
            logger.error(f"예측 결과 전송 실패: {e}", exc_info=True)
            return False

    def test_connection(self) -> bool:
        """
        텔레그램 봇 연결 테스트

        Returns:
            연결 성공 여부
        """
        try:
            url = f"{self.base_url}/getMe"

            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    bot_info = result.get("result", {})
                    logger.info(
                        f"텔레그램 봇 연결 성공: @{bot_info.get('username', 'N/A')}"
                    )
                    return True

            logger.error(f"텔레그램 봇 연결 실패: {response.text}")
            return False

        except Exception as e:
            logger.error(f"텔레그램 봇 연결 오류: {e}", exc_info=True)
            return False


# 싱글톤 인스턴스
_notifier: Optional[TelegramNotifier] = None


def get_telegram_notifier() -> TelegramNotifier:
    """
    TelegramNotifier 싱글톤 인스턴스를 반환합니다.

    Returns:
        TelegramNotifier 인스턴스
    """
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
