"""
KIS API 데이터 검증기

FDR vs KIS 데이터를 비교하여 정합성을 검증합니다.
"""
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.db.models.stock import StockPrice
from backend.db.session import SessionLocal


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""

    stock_code: str
    date: date

    # FDR 데이터
    fdr_open: float
    fdr_high: float
    fdr_low: float
    fdr_close: float
    fdr_volume: int

    # KIS 데이터
    kis_open: float
    kis_high: float
    kis_low: float
    kis_close: float
    kis_volume: int

    # 차이 (절대값)
    diff_open: float
    diff_high: float
    diff_low: float
    diff_close: float
    diff_volume: int

    # 차이 (상대값, %)
    diff_open_pct: float
    diff_high_pct: float
    diff_low_pct: float
    diff_close_pct: float
    diff_volume_pct: float

    # 일치 여부
    is_match: bool
    is_anomaly: bool


class KISValidator:
    """KIS vs FDR 데이터 검증기"""

    def __init__(
        self,
        db: Optional[Session] = None,
        threshold_pct: float = 0.1,  # 일치 임계값 (0.1%)
        anomaly_pct: float = 5.0      # 이상치 임계값 (5%)
    ):
        """
        Args:
            db: DB 세션
            threshold_pct: 일치 판정 임계값 (%)
            anomaly_pct: 이상치 판정 임계값 (%)
        """
        self.db = db or SessionLocal()
        self.should_close_db = db is None
        self.threshold_pct = threshold_pct
        self.anomaly_pct = anomaly_pct

    def validate_stock(
        self,
        stock_code: str,
        start_date: date,
        end_date: date
    ) -> List[ValidationResult]:
        """
        특정 종목의 FDR vs KIS 데이터 비교

        Args:
            stock_code: 종목 코드
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            검증 결과 리스트
        """
        results = []

        # FDR 데이터 조회
        fdr_data = (
            self.db.query(StockPrice)
            .filter(
                StockPrice.stock_code == stock_code,
                StockPrice.source.in_(["FDR", "fdr"]),
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            )
            .order_by(StockPrice.date)
            .all()
        )

        # KIS 데이터 조회
        kis_data = (
            self.db.query(StockPrice)
            .filter(
                StockPrice.stock_code == stock_code,
                StockPrice.source.in_(["KIS", "kis"]),
                StockPrice.date >= start_date,
                StockPrice.date <= end_date
            )
            .order_by(StockPrice.date)
            .all()
        )

        # 날짜별 매핑
        fdr_map = {record.date: record for record in fdr_data}
        kis_map = {record.date: record for record in kis_data}

        # 공통 날짜
        common_dates = set(fdr_map.keys()) & set(kis_map.keys())

        logger.debug(
            f"{stock_code}: FDR={len(fdr_data)}건, KIS={len(kis_data)}건, "
            f"공통={len(common_dates)}건"
        )

        for trade_date in sorted(common_dates):
            fdr_record = fdr_map[trade_date]
            kis_record = kis_map[trade_date]

            result = self._compare_records(stock_code, trade_date, fdr_record, kis_record)
            results.append(result)

        return results

    def _compare_records(
        self,
        stock_code: str,
        trade_date: date,
        fdr_record: StockPrice,
        kis_record: StockPrice
    ) -> ValidationResult:
        """
        두 레코드 비교

        Returns:
            ValidationResult
        """
        # 차이 계산
        diff_open = abs(kis_record.open - fdr_record.open)
        diff_high = abs(kis_record.high - fdr_record.high)
        diff_low = abs(kis_record.low - fdr_record.low)
        diff_close = abs(kis_record.close - fdr_record.close)
        diff_volume = abs(kis_record.volume - fdr_record.volume) if kis_record.volume and fdr_record.volume else 0

        # 상대 차이 (%)
        diff_open_pct = (diff_open / fdr_record.open * 100) if fdr_record.open else 0
        diff_high_pct = (diff_high / fdr_record.high * 100) if fdr_record.high else 0
        diff_low_pct = (diff_low / fdr_record.low * 100) if fdr_record.low else 0
        diff_close_pct = (diff_close / fdr_record.close * 100) if fdr_record.close else 0
        diff_volume_pct = (diff_volume / fdr_record.volume * 100) if fdr_record.volume else 0

        # 일치 여부
        is_match = (
            diff_open_pct <= self.threshold_pct
            and diff_high_pct <= self.threshold_pct
            and diff_low_pct <= self.threshold_pct
            and diff_close_pct <= self.threshold_pct
        )

        # 이상치 여부
        is_anomaly = (
            diff_open_pct > self.anomaly_pct
            or diff_high_pct > self.anomaly_pct
            or diff_low_pct > self.anomaly_pct
            or diff_close_pct > self.anomaly_pct
        )

        return ValidationResult(
            stock_code=stock_code,
            date=trade_date,
            fdr_open=fdr_record.open,
            fdr_high=fdr_record.high,
            fdr_low=fdr_record.low,
            fdr_close=fdr_record.close,
            fdr_volume=fdr_record.volume or 0,
            kis_open=kis_record.open,
            kis_high=kis_record.high,
            kis_low=kis_record.low,
            kis_close=kis_record.close,
            kis_volume=kis_record.volume or 0,
            diff_open=diff_open,
            diff_high=diff_high,
            diff_low=diff_low,
            diff_close=diff_close,
            diff_volume=diff_volume,
            diff_open_pct=diff_open_pct,
            diff_high_pct=diff_high_pct,
            diff_low_pct=diff_low_pct,
            diff_close_pct=diff_close_pct,
            diff_volume_pct=diff_volume_pct,
            is_match=is_match,
            is_anomaly=is_anomaly
        )

    def calculate_metrics(self, results: List[ValidationResult]) -> dict:
        """
        검증 결과 통계 계산

        Returns:
            통계 딕셔너리
        """
        if not results:
            return {
                "total_count": 0,
                "match_count": 0,
                "match_rate": 0.0,
                "anomaly_count": 0,
                "anomaly_rate": 0.0,
                "avg_diff_close_pct": 0.0,
                "max_diff_close_pct": 0.0,
                "max_diff_stock": "",
                "max_diff_date": ""
            }

        total_count = len(results)
        match_count = sum(1 for r in results if r.is_match)
        anomaly_count = sum(1 for r in results if r.is_anomaly)

        # 평균 차이 (종가 기준)
        avg_diff_close_pct = sum(r.diff_close_pct for r in results) / total_count

        # 최대 차이
        max_diff = max(results, key=lambda r: r.diff_close_pct)

        return {
            "total_count": total_count,
            "match_count": match_count,
            "match_rate": match_count / total_count * 100,
            "anomaly_count": anomaly_count,
            "anomaly_rate": anomaly_count / total_count * 100,
            "avg_diff_close_pct": avg_diff_close_pct,
            "max_diff_close_pct": max_diff.diff_close_pct,
            "max_diff_stock": max_diff.stock_code,
            "max_diff_date": max_diff.date.isoformat()
        }

    def __del__(self):
        if self.should_close_db and self.db:
            self.db.close()


# 싱글톤 팩토리
def get_validator(db: Optional[Session] = None) -> KISValidator:
    """
    KIS Validator 인스턴스 생성

    Args:
        db: DB 세션 (Optional)

    Returns:
        KISValidator 인스턴스
    """
    return KISValidator(db)
