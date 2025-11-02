"""
종목코드 매핑 유틸리티

기업명과 종목코드를 매핑하는 기능을 제공합니다.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict

from backend.db.session import SessionLocal
from backend.db.models.stock import Stock

logger = logging.getLogger(__name__)


class StockMapper:
    """종목코드 매퍼 클래스"""

    def __init__(self, mapping_file: Optional[Path] = None, use_db: bool = True):
        """
        Args:
            mapping_file: 종목코드 매핑 JSON 파일 경로 (use_db=False일 때만 사용)
            use_db: DB에서 종목 로드 여부 (기본값: True)
        """
        self.use_db = use_db
        self.mapping_file = mapping_file
        self._mapping: Dict[str, str] = {}
        self._load_mapping()

    def _load_mapping(self) -> None:
        """매핑 파일을 로드합니다 (DB 우선, 없으면 JSON 파일)."""
        if self.use_db:
            # DB에서 활성화된 종목 로드
            try:
                db = SessionLocal()
                try:
                    stocks = db.query(Stock).filter(Stock.is_active == True).all()

                    self._mapping = {
                        stock.name: stock.code
                        for stock in stocks
                    }

                    logger.info(f"종목 매핑 로드 완료 (DB): {len(self._mapping)}개")
                    return
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"DB에서 종목 로드 실패, JSON 파일로 대체: {e}")

        # JSON 파일에서 로드 (fallback)
        if self.mapping_file is None:
            project_root = Path(__file__).parent.parent.parent
            self.mapping_file = project_root / "data" / "stock_codes.json"

        if not self.mapping_file.exists():
            raise FileNotFoundError(f"종목코드 매핑 파일을 찾을 수 없습니다: {self.mapping_file}")

        with open(self.mapping_file, "r", encoding="utf-8") as f:
            self._mapping = json.load(f)

        logger.info(f"종목 매핑 로드 완료 (JSON): {len(self._mapping)}개")

    def get_stock_code(self, company_name: str) -> Optional[str]:
        """
        기업명으로 종목코드를 조회합니다.

        Args:
            company_name: 기업명 (예: "삼성전자", "SK하이닉스")

        Returns:
            종목코드 (6자리 문자열) 또는 None (매칭 실패 시)

        Examples:
            >>> mapper = StockMapper()
            >>> mapper.get_stock_code("삼성전자")
            '005930'
            >>> mapper.get_stock_code("존재하지않는기업")
            None
        """
        return self._mapping.get(company_name)

    def get_company_name(self, stock_code: str) -> Optional[str]:
        """
        종목코드로 기업명을 조회합니다 (역방향 조회).

        Args:
            stock_code: 종목코드 (6자리 문자열, 예: "005930")

        Returns:
            기업명 또는 None (매칭 실패 시)

        Examples:
            >>> mapper = StockMapper()
            >>> mapper.get_company_name("005930")
            '삼성전자'
            >>> mapper.get_company_name("999999")
            None
        """
        for company_name, code in self._mapping.items():
            if code == stock_code:
                return company_name
        return None

    def find_stock_code_in_text(self, text: str) -> Optional[str]:
        """
        텍스트에서 기업명을 찾아 종목코드를 반환합니다.

        여러 기업명이 발견되면 첫 번째 기업의 종목코드를 반환합니다.

        Args:
            text: 검색할 텍스트 (뉴스 본문 등)

        Returns:
            종목코드 (6자리 문자열) 또는 None (매칭 실패 시)

        Examples:
            >>> mapper = StockMapper()
            >>> mapper.find_stock_code_in_text("삼성전자가 신규 공정을 개발했다")
            '005930'
        """
        for company_name, stock_code in self._mapping.items():
            if company_name in text:
                return stock_code
        return None

    def get_all_companies(self) -> list[str]:
        """
        등록된 모든 기업명 목록을 반환합니다.

        Returns:
            기업명 리스트
        """
        return list(self._mapping.keys())

    def get_all_stock_codes(self) -> list[str]:
        """
        등록된 모든 종목코드 목록을 반환합니다.

        Returns:
            종목코드 리스트
        """
        return list(self._mapping.values())


# 싱글톤 인스턴스
_stock_mapper: Optional[StockMapper] = None


def get_stock_mapper() -> StockMapper:
    """
    StockMapper 싱글톤 인스턴스를 반환합니다.

    Returns:
        StockMapper 인스턴스
    """
    global _stock_mapper
    if _stock_mapper is None:
        _stock_mapper = StockMapper()
    return _stock_mapper
