"""
NewsStockMatch model for storing news-stock price correlations.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.db.base import Base


class NewsStockMatch(Base):
    """
    뉴스-주가 매칭 모델.
    뉴스 발표 후 1일, 3일, 5일 간의 주가 변동률을 저장.

    Attributes:
        id: Primary key
        news_id: 뉴스 기사 ID (Foreign Key)
        stock_code: 종목 코드
        price_change_1d: 1일 후 가격 변동률 (%)
        price_change_3d: 3일 후 가격 변동률 (%)
        price_change_5d: 5일 후 가격 변동률 (%)
        calculated_at: 계산 시간
    """

    __tablename__ = "news_stock_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    stock_code = Column(String(10), nullable=False)
    price_change_1d = Column(Float, nullable=True)
    price_change_3d = Column(Float, nullable=True)
    price_change_5d = Column(Float, nullable=True)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    news_article = relationship("NewsArticle", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<NewsStockMatch(id={self.id}, news_id={self.news_id}, "
            f"stock_code='{self.stock_code}', price_change_1d={self.price_change_1d})>"
        )
