"""
텍스트 인코딩 정규화 유틸리티

깨진 한글 텍스트를 복구하고 정규화합니다.
"""
import logging
import re

try:
    import chardet
except ImportError:
    chardet = None

logger = logging.getLogger(__name__)


class EncodingNormalizer:
    """텍스트 인코딩 정규화 클래스"""

    # 깨진 문자 패턴 (주로 다이아몬드 모양의 대체 문자)
    BROKEN_CHAR_PATTERN = re.compile(r'[\ufffd\u2666\u2662]+')

    @staticmethod
    def has_broken_text(text: str) -> bool:
        """
        텍스트가 깨져 있는지 확인합니다.

        Args:
            text: 확인할 텍스트

        Returns:
            깨진 텍스트 여부
        """
        if not text:
            return False

        # 깨진 문자 패턴 확인
        if EncodingNormalizer.BROKEN_CHAR_PATTERN.search(text):
            return True

        # 제어 문자나 비정상적인 유니코드 문자 확인
        for char in text:
            # 한글 범위 확인 (AC00-D7A3)
            code_point = ord(char)
            if 0xAC00 <= code_point <= 0xD7A3:
                # 정상 범위
                continue
            elif code_point < 32 and code_point not in (9, 10, 13):
                # 제어 문자 (탭, 줄바꿈, 캐리지 리턴 제외)
                return True
            elif 0xFFFD == code_point:
                # 대체 문자
                return True
            elif 0x2600 <= code_point <= 0x27FF:
                # 특수 기호 범위 (다이아몬드 등)
                return True

        return False

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        텍스트를 정규화합니다.

        Args:
            text: 정규화할 텍스트

        Returns:
            정규화된 텍스트
        """
        if not text:
            return text

        # 명백하게 깨진 부분 제거
        normalized = EncodingNormalizer.BROKEN_CHAR_PATTERN.sub("", text)

        # 연속된 공백 정리
        normalized = re.sub(r' +', ' ', normalized)

        # 양쪽 공백 제거
        normalized = normalized.strip()

        return normalized

    @staticmethod
    def try_fix_broken_encoding(corrupted_text: str) -> str:
        """
        UTF-8을 다른 인코딩으로 잘못 해석된 텍스트를 복구합니다.

        Args:
            corrupted_text: 깨진 텍스트

        Returns:
            복구된 텍스트 (복구 실패 시 원본 반환)
        """
        if not corrupted_text:
            return corrupted_text

        try:
            # UTF-8 바이트를 라틴-1(ISO-8859-1)으로 인코딩했을 가능성
            fixed = corrupted_text.encode('iso-8859-1').decode('utf-8')
            return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

        try:
            # UTF-8 바이트를 EUC-KR로 인코딩했을 가능성
            fixed = corrupted_text.encode('euc-kr', errors='ignore').decode('utf-8')
            return fixed
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass

        # 복구 실패 시 정규화만 수행
        return EncodingNormalizer.normalize_text(corrupted_text)


def get_encoding_normalizer() -> EncodingNormalizer:
    """EncodingNormalizer 싱글톤 인스턴스를 반환합니다."""
    return EncodingNormalizer()
