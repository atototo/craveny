"""
데이터 소스 선택기

FDR과 KIS 데이터의 품질을 비교하여 최적의 소스를 선택합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Literal, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from backend.db.models.stock import StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


DataSource = Literal["fdr", "kis", "auto"]


class DataSourceSelector:
    """데이터 소스 선택 및 품질 모니터링"""

    def __init__(self, db: Optional[Session] = None):
        """
        Args:
            db: DB 세션 (None이면 자동 생성)
        """
        self.db = db or SessionLocal()
        self.should_close_db = db is None

    def get_data_quality_score(
        self,
        source: str,
        stock_code: str,
        days: int = 7
    ) -> float:
        """
        데이터 소스의 품질 점수 계산

        Args:
            source: 'fdr' 또는 'kis'
            stock_code: 종목 코드
            days: 평가 기간 (일)

        Returns:
            품질 점수 (0.0~1.0)
        """
        start_date = datetime.now() - timedelta(days=days)

        # 데이터 완전성 (availability)
        total_expected_days = self._get_expected_trading_days(days)
        actual_days = self.db.query(func.count(StockPrice.id)).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == source,
                StockPrice.date >= start_date
            )
        ).scalar()

        completeness_score = (actual_days / total_expected_days) if total_expected_days > 0 else 0

        # 데이터 신선도 (freshness)
        latest_price = self.db.query(StockPrice).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == source
            )
        ).order_by(StockPrice.date.desc()).first()

        if latest_price:
            days_old = (datetime.now() - latest_price.date).days
            freshness_score = max(0, 1 - (days_old / 7))  # 7일 이상 오래되면 0점
        else:
            freshness_score = 0

        # 가중 평균
        quality_score = (completeness_score * 0.6) + (freshness_score * 0.4)

        return quality_score

    def _get_expected_trading_days(self, days: int) -> int:
        """
        주어진 기간 내 예상 거래일 수 계산

        Args:
            days: 기간 (일)

        Returns:
            예상 거래일 수
        """
        # 간단히 주말 제외 (공휴일은 미고려)
        total_days = days
        weekends = (days // 7) * 2

        return max(1, total_days - weekends)

    def select_best_source(
        self,
        stock_code: str,
        prefer_kis: bool = True
    ) -> str:
        """
        최적의 데이터 소스 선택

        Args:
            stock_code: 종목 코드
            prefer_kis: KIS를 우선할지 여부 (기본: True)

        Returns:
            'fdr' 또는 'kis'
        """
        fdr_score = self.get_data_quality_score("fdr", stock_code)
        kis_score = self.get_data_quality_score("kis", stock_code)

        logger.debug(
            f"{stock_code} 데이터 품질: FDR {fdr_score:.2f}, KIS {kis_score:.2f}"
        )

        # KIS 우선 모드
        if prefer_kis:
            # KIS 점수가 0.8 이상이면 KIS 사용
            if kis_score >= 0.8:
                return "kis"
            # KIS가 부족하면 FDR로 폴백
            elif fdr_score >= 0.8:
                logger.warning(f"{stock_code}: KIS 데이터 부족, FDR로 폴백")
                return "fdr"
            # 둘 다 부족하면 점수 높은 쪽
            else:
                return "kis" if kis_score >= fdr_score else "fdr"
        else:
            # 품질 점수가 높은 쪽 선택
            return "kis" if kis_score > fdr_score else "fdr"

    def get_stock_price(
        self,
        stock_code: str,
        date: datetime,
        source: DataSource = "auto"
    ) -> Optional[StockPrice]:
        """
        주가 데이터 조회 (소스 자동 선택 지원)

        Args:
            stock_code: 종목 코드
            date: 날짜
            source: 데이터 소스 ('fdr', 'kis', 'auto')

        Returns:
            StockPrice 객체 또는 None
        """
        # 소스 자동 선택
        if source == "auto":
            source = self.select_best_source(stock_code)

        # 데이터 조회
        price = self.db.query(StockPrice).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == source,
                StockPrice.date >= date.replace(hour=0, minute=0, second=0),
                StockPrice.date < date.replace(hour=23, minute=59, second=59)
            )
        ).first()

        return price

    def get_recent_prices(
        self,
        stock_code: str,
        days: int = 30,
        source: DataSource = "auto"
    ) -> list[StockPrice]:
        """
        최근 N일 주가 데이터 조회

        Args:
            stock_code: 종목 코드
            days: 조회 일수
            source: 데이터 소스

        Returns:
            StockPrice 리스트
        """
        # 소스 자동 선택
        if source == "auto":
            source = self.select_best_source(stock_code)

        start_date = datetime.now() - timedelta(days=days)

        prices = self.db.query(StockPrice).filter(
            and_(
                StockPrice.stock_code == stock_code,
                StockPrice.source == source,
                StockPrice.date >= start_date
            )
        ).order_by(StockPrice.date.desc()).all()

        return prices

    def __del__(self):
        """소멸자"""
        if self.should_close_db and self.db:
            self.db.close()


# 싱글톤 인스턴스
_selector: Optional[DataSourceSelector] = None


def get_data_source_selector(db: Optional[Session] = None) -> DataSourceSelector:
    """
    DataSourceSelector 싱글톤 반환

    Args:
        db: DB 세션

    Returns:
        DataSourceSelector 인스턴스
    """
    global _selector
    if _selector is None or db is not None:
        _selector = DataSourceSelector(db)
    return _selector
