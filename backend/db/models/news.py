"""
NewsArticle model for storing news articles.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from backend.db.base import Base


class NewsArticle(Base):
    """
    뉴스 기사 모델.

    Attributes:
        id: Primary key
        title: 뉴스 제목
        content: 뉴스 본문
        published_at: 뉴스 발행 시간
        source: 뉴스 출처 (예: 'naver', 'hankyung', 'maeil')
        stock_code: 관련 종목 코드 (예: '005930')
        created_at: 데이터 생성 시간
        notified_at: 텔레그램 알림 전송 시간 (None이면 미전송)
    """

    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False)
    source = Column(String(100), nullable=False)
    stock_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notified_at = Column(DateTime, nullable=True)

    # 복합 인덱스: stock_code와 published_at으로 빠른 조회
    __table_args__ = (
        Index("idx_news_articles_stock_code_published_at", "stock_code", "published_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<NewsArticle(id={self.id}, title='{self.title[:30]}...', "
            f"stock_code='{self.stock_code}', published_at={self.published_at})>"
        )
