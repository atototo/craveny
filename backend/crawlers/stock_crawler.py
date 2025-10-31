"""
주가 수집기

FinanceDataReader를 사용하여 실시간 주가 데이터를 수집합니다.
"""
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta

import FinanceDataReader as fdr
import pandas as pd
from sqlalchemy.orm import Session

from backend.db.models.stock import StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class StockCrawler:
    """주가 데이터 수집 클래스"""

    def __init__(self, target_stocks_file: Optional[Path] = None):
        """
        Args:
            target_stocks_file: 종목 리스트 JSON 파일 경로
        """
        if target_stocks_file is None:
            # 프로젝트 루트 기준 경로
            project_root = Path(__file__).parent.parent.parent
            target_stocks_file = project_root / "data" / "target_stocks.json"

        self.target_stocks_file = target_stocks_file
        self.target_stocks: List[Dict] = []
        self._load_target_stocks()

    def _load_target_stocks(self) -> None:
        """종목 리스트를 로드합니다."""
        if not self.target_stocks_file.exists():
            raise FileNotFoundError(
                f"종목 리스트 파일을 찾을 수 없습니다: {self.target_stocks_file}"
            )

        with open(self.target_stocks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.target_stocks = data.get("stocks", [])

        logger.info(f"종목 리스트 로드 완료: {len(self.target_stocks)}개")

    def get_stock_codes(self, priority: Optional[int] = None) -> List[str]:
        """
        종목 코드 리스트를 반환합니다.

        Args:
            priority: 우선순위 필터 (1~5, None이면 전체)

        Returns:
            종목 코드 리스트
        """
        if priority is None:
            return [stock["code"] for stock in self.target_stocks]
        else:
            return [
                stock["code"]
                for stock in self.target_stocks
                if stock.get("priority") == priority
            ]

    def fetch_stock_data(
        self, stock_code: str, start_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        특정 종목의 주가 데이터를 가져옵니다.

        Args:
            stock_code: 종목 코드 (6자리)
            start_date: 시작 날짜 (기본값: 오늘)

        Returns:
            DataFrame (columns: Date, Open, High, Low, Close, Volume) 또는 None
        """
        if start_date is None:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        start_str = start_date.strftime("%Y-%m-%d")

        try:
            logger.debug(f"주가 데이터 수집 시작: {stock_code} (from {start_str})")

            # FinanceDataReader로 데이터 수집
            df = fdr.DataReader(stock_code, start=start_str)

            if df is None or df.empty:
                logger.warning(f"데이터 없음: {stock_code}")
                return None

            logger.debug(f"데이터 수집 완료: {stock_code}, {len(df)}건")
            return df

        except Exception as e:
            logger.error(f"주가 데이터 수집 실패: {stock_code}, {e}")
            return None

    def save_stock_data(
        self, stock_code: str, df: pd.DataFrame, db: Session
    ) -> int:
        """
        주가 데이터를 데이터베이스에 저장합니다.

        Args:
            stock_code: 종목 코드
            df: 주가 DataFrame
            db: 데이터베이스 세션

        Returns:
            저장된 레코드 수
        """
        saved_count = 0

        try:
            for index, row in df.iterrows():
                # 날짜 변환
                if isinstance(index, pd.Timestamp):
                    date = index.to_pydatetime()
                else:
                    date = pd.to_datetime(index).to_pydatetime()

                # 중복 체크 (stock_code + date 조합)
                existing = (
                    db.query(StockPrice)
                    .filter(
                        StockPrice.stock_code == stock_code,
                        StockPrice.date == date,
                    )
                    .first()
                )

                if existing:
                    # 기존 데이터 업데이트
                    existing.open = float(row["Open"])
                    existing.high = float(row["High"])
                    existing.low = float(row["Low"])
                    existing.close = float(row["Close"])
                    existing.volume = int(row["Volume"]) if "Volume" in row else None
                    logger.debug(f"주가 데이터 업데이트: {stock_code} {date}")
                else:
                    # 새 데이터 삽입
                    stock_price = StockPrice(
                        stock_code=stock_code,
                        date=date,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        volume=int(row["Volume"]) if "Volume" in row else None,
                    )
                    db.add(stock_price)
                    logger.debug(f"주가 데이터 삽입: {stock_code} {date}")

                saved_count += 1

            db.commit()
            logger.info(f"주가 데이터 저장 완료: {stock_code}, {saved_count}건")

        except Exception as e:
            db.rollback()
            logger.error(f"주가 데이터 저장 실패: {stock_code}, {e}")
            return 0

        return saved_count

    def collect_all_stocks(
        self, priority: Optional[int] = None, db: Optional[Session] = None
    ) -> Dict[str, int]:
        """
        모든 대상 종목의 주가 데이터를 수집합니다.

        Args:
            priority: 우선순위 필터 (None이면 전체)
            db: 데이터베이스 세션 (None이면 새로 생성)

        Returns:
            {종목코드: 저장 건수} 딕셔너리
        """
        stock_codes = self.get_stock_codes(priority)
        results = {}

        # DB 세션 생성
        db_session = db or SessionLocal()
        should_close = db is None

        try:
            for stock_code in stock_codes:
                # 주가 데이터 수집
                df = self.fetch_stock_data(stock_code)

                if df is not None:
                    # DB에 저장
                    saved = self.save_stock_data(stock_code, df, db_session)
                    results[stock_code] = saved
                else:
                    results[stock_code] = 0

        finally:
            if should_close:
                db_session.close()

        # 결과 요약
        total_saved = sum(results.values())
        success_count = sum(1 for count in results.values() if count > 0)

        logger.info(
            f"전체 주가 수집 완료: {success_count}/{len(stock_codes)}개 종목, "
            f"총 {total_saved}건 저장"
        )

        return results


# 싱글톤 인스턴스
_stock_crawler: Optional[StockCrawler] = None


def get_stock_crawler() -> StockCrawler:
    """
    StockCrawler 싱글톤 인스턴스를 반환합니다.

    Returns:
        StockCrawler 인스턴스
    """
    global _stock_crawler
    if _stock_crawler is None:
        _stock_crawler = StockCrawler()
    return _stock_crawler
