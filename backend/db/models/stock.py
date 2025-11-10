"""
Stock models for storing stock master data and daily stock price data.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Index, BigInteger
from datetime import datetime
from backend.db.base import Base


class Stock(Base):
    """
    종목 마스터 테이블.

    Attributes:
        id: Primary key
        code: 종목 코드 (예: '005930')
        name: 종목명 (예: '삼성전자')
        priority: 크롤링 우선순위 (1~5, 낮을수록 우선)
        is_active: 활성화 여부
        created_at: 생성일시
        updated_at: 수정일시
    """

    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    priority = Column(Integer, default=5, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<Stock(id={self.id}, code='{self.code}', name='{self.name}', "
            f"priority={self.priority}, is_active={self.is_active})>"
        )


class StockPrice(Base):
    """
    주가 데이터 모델.

    Attributes:
        id: Primary key
        stock_code: 종목 코드 (예: '005930')
        date: 주가 날짜
        open: 시가
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량
    """

    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    source = Column(String(10), nullable=False, default="fdr", server_default="fdr")  # fdr 또는 kis

    # 복합 인덱스: stock_code와 date로 빠른 조회
    __table_args__ = (
        Index("idx_stock_prices_stock_code_date", "stock_code", "date"),
        Index("idx_stock_prices_date_source", "date", "source"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockPrice(id={self.id}, stock_code='{self.stock_code}', "
            f"date={self.date}, close={self.close})>"
        )


class StockPriceMinute(Base):
    """
    1분봉 주가 데이터 모델.

    Attributes:
        id: Primary key
        stock_code: 종목 코드 (예: '005930')
        datetime: 1분봉 시간 (YYYY-MM-DD HH:MM:00)
        open: 시가
        high: 고가
        low: 저가
        close: 종가
        volume: 거래량
        source: 데이터 소스 (kis)
        created_at: 생성일시
    """

    __tablename__ = "stock_prices_minute"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), nullable=False)
    datetime = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=True)
    source = Column(String(20), default="kis", server_default="kis")
    created_at = Column(DateTime)

    # 복합 인덱스: stock_code와 datetime로 빠른 조회
    __table_args__ = (
        Index("idx_minute_stock_datetime", "stock_code", "datetime"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockPriceMinute(id={self.id}, stock_code='{self.stock_code}', "
            f"datetime={self.datetime}, close={self.close})>"
        )
