"""
NewsArticle model for storing news articles and other content sources.
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from backend.db.base import Base


class ContentType(str, Enum):
    """콘텐츠 소스 타입 enum"""
    NEWS = "news"
    REDDIT = "reddit"
    TWITTER = "twitter"
    TELEGRAM = "telegram"


class NewsArticle(Base):
    """
    다중 플랫폼 콘텐츠 모델 (뉴스, Reddit, Twitter 등)

    Attributes:
        id: Primary key
        title: 콘텐츠 제목
        content: 콘텐츠 본문
        published_at: 발행 시간
        source: 소스 식별자 (예: 'naver', 'reddit:r/stocks')
        stock_code: 관련 종목 코드 (예: '005930')
        created_at: 데이터 생성 시간
        notified_at: 텔레그램 알림 전송 시간 (None이면 미전송)

        # 멀티 플랫폼 지원 필드
        content_type: 콘텐츠 타입 (news, reddit, twitter 등)
        url: 원본 URL
        author: 작성자

        # Reddit 전용 필드
        upvotes: Reddit upvote 수 (뉴스의 경우 NULL)
        num_comments: Reddit 댓글 수 (뉴스의 경우 NULL)
        subreddit: Subreddit 이름 (뉴스의 경우 NULL)

        # 메타데이터
        metadata: 플랫폼별 추가 데이터를 위한 JSON 필드
    """

    __tablename__ = "news_articles"

    # 기존 필드
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False)
    source = Column(String(100), nullable=False)
    stock_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notified_at = Column(DateTime, nullable=True)

    # 멀티 플랫폼 지원 필드
    content_type = Column(
        String(20),
        nullable=False,
        default='news',
        index=True
    )
    url = Column(String(1000), nullable=True)
    author = Column(String(200), nullable=True)

    # Reddit 전용 메트릭
    upvotes = Column(Integer, nullable=True)
    num_comments = Column(Integer, nullable=True)
    subreddit = Column(String(100), nullable=True, index=True)

    # 플랫폼별 추가 데이터
    extra_metadata = Column('metadata', JSONB, nullable=True)

    # 인덱스
    __table_args__ = (
        Index("idx_news_articles_stock_code_published_at", "stock_code", "published_at"),
        Index("idx_news_articles_content_type", "content_type"),
        Index("idx_news_articles_subreddit", "subreddit"),
        Index("idx_news_articles_source_type", "source", "content_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<NewsArticle(id={self.id}, title='{self.title[:30]}...', "
            f"stock_code='{self.stock_code}', published_at={self.published_at})>"
        )
