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
from sqlalchemy import func

from backend.db.models.stock import Stock, StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


class StockCrawler:
    """주가 데이터 수집 클래스"""

    def __init__(self, target_stocks_file: Optional[Path] = None, use_db: bool = True):
        """
        Args:
            target_stocks_file: 종목 리스트 JSON 파일 경로 (use_db=False일 때만 사용)
            use_db: DB에서 종목 리스트 로드 여부 (기본값: True)
        """
        self.use_db = use_db
        self.target_stocks_file = target_stocks_file
        self.target_stocks: List[Dict] = []
        self._load_target_stocks()

    def _load_target_stocks(self) -> None:
        """종목 리스트를 로드합니다 (DB 우선, 없으면 JSON 파일)."""
        if self.use_db:
            # DB에서 활성화된 종목 로드
            try:
                db = SessionLocal()
                try:
                    stocks = db.query(Stock).filter(Stock.is_active == True).all()

                    self.target_stocks = [
                        {
                            "code": stock.code,
                            "name": stock.name,
                            "priority": stock.priority
                        }
                        for stock in stocks
                    ]

                    logger.info(f"종목 리스트 로드 완료 (DB): {len(self.target_stocks)}개")
                    return
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"DB에서 종목 로드 실패, JSON 파일로 대체: {e}")

        # JSON 파일에서 로드 (fallback)
        if self.target_stocks_file is None:
            project_root = Path(__file__).parent.parent.parent
            self.target_stocks_file = project_root / "data" / "target_stocks.json"

        if not self.target_stocks_file.exists():
            raise FileNotFoundError(
                f"종목 리스트 파일을 찾을 수 없습니다: {self.target_stocks_file}"
            )

        with open(self.target_stocks_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.target_stocks = data.get("stocks", [])

        logger.info(f"종목 리스트 로드 완료 (JSON): {len(self.target_stocks)}개")

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

    def _check_historical_data(
        self, stock_code: str, db: Session, required_days: int = 90
    ) -> bool:
        """
        종목의 과거 데이터가 충분한지 확인합니다.

        Args:
            stock_code: 종목 코드
            db: 데이터베이스 세션
            required_days: 필요한 과거 일수 (기본 90일)

        Returns:
            True: 충분한 데이터 존재, False: 데이터 부족 또는 없음
        """
        earliest_date = db.query(func.min(StockPrice.date)).filter(
            StockPrice.stock_code == stock_code
        ).scalar()

        if earliest_date is None:
            # 데이터가 전혀 없음
            return False

        # 필요한 시작 날짜
        target_start = datetime.now() - timedelta(days=required_days)

        # 기존 데이터가 충분한지 확인
        return earliest_date.date() <= target_start.date()

    def _collect_historical_data(
        self, stock_code: str, db: Session, days: int = 90
    ) -> int:
        """
        신규 종목의 과거 데이터를 수집합니다.

        Args:
            stock_code: 종목 코드
            db: 데이터베이스 세션
            days: 수집할 과거 일수

        Returns:
            저장된 레코드 수
        """
        logger.info(f"📈 {stock_code} 과거 {days}일 데이터 수집 시작")

        # 시작 날짜 계산
        start_date = datetime.now() - timedelta(days=days)

        # 데이터 수집
        df = self.fetch_stock_data(stock_code, start_date=start_date)

        if df is None or df.empty:
            logger.warning(f"⚠️  {stock_code}: 과거 데이터 없음")
            return 0

        # 저장
        saved_count = self.save_stock_data(stock_code, df, db)
        logger.info(f"✅ {stock_code}: 과거 데이터 {saved_count}건 저장 완료")

        return saved_count

    def collect_all_stocks(
        self, priority: Optional[int] = None, db: Optional[Session] = None
    ) -> Dict[str, int]:
        """
        모든 대상 종목의 주가 데이터를 수집합니다.
        신규 종목의 경우 과거 3개월 데이터를 자동으로 수집합니다.

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
                # 과거 데이터 확인
                has_sufficient_data = self._check_historical_data(
                    stock_code, db_session, required_days=90
                )

                if not has_sufficient_data:
                    # 신규 종목 또는 데이터 부족 → 과거 3개월 수집
                    logger.info(f"🆕 {stock_code}: 신규 종목 감지, 과거 데이터 수집 시작")
                    historical_count = self._collect_historical_data(
                        stock_code, db_session, days=90
                    )
                    results[stock_code] = historical_count
                else:
                    # 기존 종목 → 오늘 데이터만 수집
                    df = self.fetch_stock_data(stock_code)

                    if df is not None:
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
