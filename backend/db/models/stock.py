"""
StockPrice model for storing daily stock price data.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from backend.db.base import Base


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

    # 복합 인덱스: stock_code와 date로 빠른 조회
    __table_args__ = (
        Index("idx_stock_prices_stock_code_date", "stock_code", "date"),
    )

    def __repr__(self) -> str:
        return (
            f"<StockPrice(id={self.id}, stock_code='{self.stock_code}', "
            f"date={self.date}, close={self.close})>"
        )
