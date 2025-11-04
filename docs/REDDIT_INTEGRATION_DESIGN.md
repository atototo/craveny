# Reddit API Integration Architecture Design

## Executive Summary

This document proposes an architecture for integrating Reddit API to collect international community sentiment about Korean stocks (Samsung, SK Hynix, etc.) while leveraging the existing news crawling pipeline.

**Core Philosophy**:
- Unified content model with type discrimination
- Minimal modification to existing pipeline
- Extensible design for future platforms (Twitter, etc.)

---

## 1. Data Model Design

### 1.1 Design Decision: Unified Content Model

**Chosen Approach**: Extend `NewsArticle` model to support multiple content types

**Rationale**:
- ✅ Reuses existing pipeline (NewsSaver, EmbeddingDeduplicator, StockPredictor)
- ✅ Single prediction/notification workflow
- ✅ Cross-platform deduplication (Reddit post similar to news article)
- ✅ Unified search and analytics
- ✅ Minimal code changes

**Alternative Rejected**: Separate `RedditPost` model
- ❌ Duplicates 80% of NewsArticle logic
- ❌ Requires parallel prediction/notification pipelines
- ❌ Cannot detect cross-platform duplicates
- ❌ Complex JOIN queries for unified analytics

### 1.2 Database Schema Changes

```python
# backend/db/models/news.py (MODIFIED)

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, Enum as SQLEnum
from enum import Enum

class ContentType(str, Enum):
    """Content source type enum"""
    NEWS = "news"
    REDDIT = "reddit"
    TWITTER = "twitter"  # Future expansion
    TELEGRAM = "telegram"  # Future expansion

class NewsArticle(Base):
    """
    Multi-source content model (News, Reddit, Twitter, etc.)

    Attributes:
        id: Primary key
        title: Content title
        content: Content body
        published_at: Publication timestamp
        source: Source identifier (e.g., 'naver', 'reddit:r/stocks')
        content_type: Content type (news, reddit, twitter)
        stock_code: Related stock code
        created_at: DB creation timestamp
        notified_at: Telegram notification timestamp

        # Reddit-specific fields
        url: Source URL (Reddit post link, news URL)
        author: Content author (Reddit username, news author)
        upvotes: Reddit upvotes (NULL for news)
        num_comments: Reddit comment count (NULL for news)
        subreddit: Subreddit name (NULL for news)

        # Metadata
        metadata: JSON field for platform-specific data
    """

    __tablename__ = "news_articles"

    # Existing fields
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=False)
    source = Column(String(100), nullable=False)  # 'naver', 'reddit:r/stocks'
    stock_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notified_at = Column(DateTime, nullable=True)

    # NEW: Content type discrimination
    content_type = Column(
        SQLEnum(ContentType),
        nullable=False,
        default=ContentType.NEWS,
        index=True
    )

    # NEW: Multi-platform support fields
    url = Column(String(1000), nullable=True)
    author = Column(String(200), nullable=True)

    # NEW: Reddit-specific metrics
    upvotes = Column(Integer, nullable=True)
    num_comments = Column(Integer, nullable=True)
    subreddit = Column(String(100), nullable=True, index=True)

    # NEW: Flexible metadata for platform-specific data
    metadata = Column(JSON, nullable=True)

    # Updated indexes
    __table_args__ = (
        Index("idx_news_articles_stock_code_published_at", "stock_code", "published_at"),
        Index("idx_news_articles_content_type", "content_type"),
        Index("idx_news_articles_subreddit", "subreddit"),
        Index("idx_news_articles_source_type", "source", "content_type"),
    )
```

**Migration Strategy**:
```python
# scripts/migrate_add_reddit_fields.py

def upgrade():
    """Add Reddit support fields"""
    op.add_column('news_articles', sa.Column('content_type', sa.Enum('news', 'reddit', 'twitter', 'telegram', name='contenttype'), nullable=False, server_default='news'))
    op.add_column('news_articles', sa.Column('url', sa.String(1000), nullable=True))
    op.add_column('news_articles', sa.Column('author', sa.String(200), nullable=True))
    op.add_column('news_articles', sa.Column('upvotes', sa.Integer(), nullable=True))
    op.add_column('news_articles', sa.Column('num_comments', sa.Integer(), nullable=True))
    op.add_column('news_articles', sa.Column('subreddit', sa.String(100), nullable=True))
    op.add_column('news_articles', sa.Column('metadata', sa.JSON(), nullable=True))

    # Create indexes
    op.create_index('idx_news_articles_content_type', 'news_articles', ['content_type'])
    op.create_index('idx_news_articles_subreddit', 'news_articles', ['subreddit'])
    op.create_index('idx_news_articles_source_type', 'news_articles', ['source', 'content_type'])
```

---

## 2. Crawler Design

### 2.1 Reddit Crawler Architecture

**Approach**: Extend `BaseNewsCrawler` to leverage existing HTTP session management, rate limiting, and error handling.

```python
# backend/crawlers/reddit_crawler.py

import praw
from typing import List, Optional
from datetime import datetime, timedelta
from backend.crawlers.base_crawler import BaseNewsCrawler, NewsArticleData
from backend.config import settings

class RedditCrawler(BaseNewsCrawler):
    """
    Reddit post crawler using PRAW (Python Reddit API Wrapper)

    Target subreddits:
    - r/stocks (2.5M members)
    - r/investing (2.0M members)
    - r/wallstreetbets (15M members)
    - r/StockMarket (1.5M members)
    - r/Korea_Stock (smaller but focused)

    Search keywords:
    - Samsung, SK Hynix, LG, Hyundai, Kia
    - Korean stocks, KOSPI, Korean market
    """

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        user_agent: str = None,
        subreddits: List[str] = None,
        keywords: List[str] = None,
        min_upvotes: int = 10,
        min_comments: int = 2,
        lookback_hours: int = 24,
    ):
        """
        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API secret
            user_agent: Reddit API user agent
            subreddits: Target subreddits (default: stocks, investing, Korea_Stock)
            keywords: Search keywords (default: Samsung, Hynix, Korean stocks)
            min_upvotes: Minimum upvotes threshold
            min_comments: Minimum comment count threshold
            lookback_hours: How far back to search
        """
        super().__init__(
            source_name="reddit",
            timeout=30,
            max_retries=3,
            rate_limit_seconds=2.0  # Reddit rate limit: 60 req/min
        )

        self.client_id = client_id or settings.REDDIT_CLIENT_ID
        self.client_secret = client_secret or settings.REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or settings.REDDIT_USER_AGENT

        # Default configuration
        self.subreddits = subreddits or ["stocks", "investing", "Korea_Stock", "StockMarket"]
        self.keywords = keywords or [
            "Samsung", "SK Hynix", "LG", "Hyundai", "Kia",
            "Korean stocks", "KOSPI", "Korea market"
        ]
        self.min_upvotes = min_upvotes
        self.min_comments = min_comments
        self.lookback_hours = lookback_hours

        # Initialize PRAW client
        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
            check_for_async=False
        )

        logger.info(
            f"RedditCrawler initialized: "
            f"subreddits={self.subreddits}, "
            f"keywords={len(self.keywords)}, "
            f"min_upvotes={self.min_upvotes}"
        )

    def fetch_news(self, limit: int = 50) -> List[NewsArticleData]:
        """
        Fetch Reddit posts matching Korean stock keywords

        Args:
            limit: Maximum posts to fetch per subreddit

        Returns:
            List of NewsArticleData objects
        """
        all_posts = []
        cutoff_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)

        for subreddit_name in self.subreddits:
            try:
                logger.info(f"Fetching from r/{subreddit_name}...")
                posts = self._fetch_from_subreddit(subreddit_name, limit)

                # Filter by keywords and quality thresholds
                filtered_posts = [
                    post for post in posts
                    if self._matches_keywords(post.title + " " + post.content)
                    and post.published_at >= cutoff_time
                ]

                all_posts.extend(filtered_posts)
                logger.info(
                    f"r/{subreddit_name}: {len(filtered_posts)}/{len(posts)} posts matched"
                )

            except Exception as e:
                logger.error(f"Failed to fetch from r/{subreddit_name}: {e}")

        logger.info(f"Total Reddit posts collected: {len(all_posts)}")
        return all_posts

    def _fetch_from_subreddit(self, subreddit_name: str, limit: int) -> List[NewsArticleData]:
        """Fetch posts from a single subreddit"""
        posts = []
        subreddit = self.reddit.subreddit(subreddit_name)

        # Fetch from multiple sources for better coverage
        sources = [
            ("hot", subreddit.hot(limit=limit)),
            ("new", subreddit.new(limit=limit // 2)),
            ("top_day", subreddit.top(time_filter="day", limit=limit // 2)),
        ]

        seen_ids = set()

        for source_name, submissions in sources:
            for submission in submissions:
                # Skip duplicates
                if submission.id in seen_ids:
                    continue
                seen_ids.add(submission.id)

                # Apply quality filters
                if submission.score < self.min_upvotes:
                    continue
                if submission.num_comments < self.min_comments:
                    continue

                # Convert to NewsArticleData
                post_data = self._convert_submission(submission, subreddit_name)
                if post_data:
                    posts.append(post_data)

        return posts

    def _convert_submission(self, submission, subreddit_name: str) -> Optional[NewsArticleData]:
        """Convert Reddit submission to NewsArticleData"""
        try:
            # Extract content (title + selftext or first comment)
            content = submission.selftext
            if not content or len(content) < 50:
                # If post has no body, use top comment
                submission.comments.replace_more(limit=0)
                if submission.comments:
                    content = submission.comments[0].body

            # Create NewsArticleData with Reddit metadata
            return NewsArticleData(
                title=submission.title,
                content=content or "No content",
                published_at=datetime.fromtimestamp(submission.created_utc),
                source=f"reddit:r/{subreddit_name}",
                url=f"https://reddit.com{submission.permalink}",
                company_name=None,  # Will be extracted by StockMapper
                # Store Reddit-specific data in metadata
                metadata={
                    "upvotes": submission.score,
                    "num_comments": submission.num_comments,
                    "author": str(submission.author),
                    "subreddit": subreddit_name,
                    "post_id": submission.id,
                    "is_self": submission.is_self,
                    "link_flair_text": submission.link_flair_text,
                }
            )

        except Exception as e:
            logger.error(f"Failed to convert submission {submission.id}: {e}")
            return None

    def _matches_keywords(self, text: str) -> bool:
        """Check if text contains any target keywords"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in self.keywords)
```

### 2.2 NewsArticleData Extension

```python
# backend/crawlers/base_crawler.py (MODIFIED)

class NewsArticleData:
    """Data class for crawled content (News, Reddit, etc.)"""

    def __init__(
        self,
        title: str,
        content: str,
        published_at: datetime,
        source: str,
        url: Optional[str] = None,
        company_name: Optional[str] = None,
        # NEW: Multi-platform support
        author: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.title = title
        self.content = content
        self.published_at = published_at
        self.source = source
        self.url = url
        self.company_name = company_name
        self.author = author
        self.metadata = metadata or {}
```

---

## 3. Pipeline Integration

### 3.1 NewsSaver Extension

**Approach**: Minimal modification to support `content_type` and new fields.

```python
# backend/crawlers/news_saver.py (MODIFIED)

from backend.db.models.news import ContentType

class NewsSaver:
    """Content saver supporting multi-platform sources"""

    def save_news(self, news_data: NewsArticleData) -> Optional[NewsArticle]:
        """
        Save content to database (News, Reddit, etc.)

        Automatically detects content_type from source field:
        - 'reddit:*' → ContentType.REDDIT
        - 'twitter:*' → ContentType.TWITTER
        - Default → ContentType.NEWS
        """
        # ... existing validation and deduplication logic ...

        # Determine content type from source
        content_type = self._determine_content_type(news_data.source)

        # Extract platform-specific fields
        upvotes = news_data.metadata.get('upvotes')
        num_comments = news_data.metadata.get('num_comments')
        subreddit = news_data.metadata.get('subreddit')

        # Create NewsArticle instance
        news_article = NewsArticle(
            title=title,
            content=content,
            published_at=news_data.published_at,
            source=news_data.source,
            stock_code=stock_code,
            # NEW: Multi-platform fields
            content_type=content_type,
            url=news_data.url,
            author=news_data.author,
            upvotes=upvotes,
            num_comments=num_comments,
            subreddit=subreddit,
            metadata=news_data.metadata,
        )

        # ... existing save and prediction logic ...

    def _determine_content_type(self, source: str) -> ContentType:
        """Determine content type from source identifier"""
        if source.startswith('reddit:'):
            return ContentType.REDDIT
        elif source.startswith('twitter:'):
            return ContentType.TWITTER
        else:
            return ContentType.NEWS
```

**Impact**:
- ✅ No changes to prediction pipeline
- ✅ No changes to notification pipeline
- ✅ Automatic cross-platform deduplication via embedding

---

## 4. Scheduler Integration

### 4.1 Scheduler Extension

```python
# backend/scheduler/crawler_scheduler.py (MODIFIED)

from backend.crawlers.reddit_crawler import RedditCrawler

class CrawlerScheduler:

    def _crawl_reddit_posts(self) -> None:
        """
        Crawl Reddit posts about Korean stocks
        """
        logger.info("=" * 60)
        logger.info("🔴 Reddit 포스트 수집 시작")
        logger.info("=" * 60)

        db = SessionLocal()
        saver = NewsSaver(db)

        saved_total = 0
        skipped_total = 0

        try:
            with RedditCrawler() as reddit:
                posts = reddit.fetch_news(limit=50)

                if posts:
                    saved, skipped = saver.save_news_batch(posts)
                    saved_total += saved
                    skipped_total += skipped
                    logger.info(f"✅ Reddit: {saved}건 저장, {skipped}건 스킵")
                else:
                    logger.warning("⚠️ Reddit: 포스트 없음")

        except Exception as e:
            logger.error(f"❌ Reddit 크롤링 실패: {e}")
        finally:
            db.close()

        logger.info("=" * 60)
        logger.info(f"✅ Reddit 수집 완료: {saved_total}건 저장, {skipped_total}건 스킵")
        logger.info("=" * 60)

    def start(self) -> None:
        """Start scheduler with Reddit crawler"""
        # ... existing schedulers ...

        # NEW: Reddit crawler (30분 간격 - less frequent than news)
        reddit_trigger = IntervalTrigger(minutes=30)
        self.scheduler.add_job(
            func=self._crawl_reddit_posts,
            trigger=reddit_trigger,
            id="reddit_crawler_job",
            name="Reddit 크롤러",
            replace_existing=True,
        )

        logger.info("   - Reddit 포스트: 30분마다")
```

**Rationale for 30-minute interval**:
- Reddit posts update slower than news articles
- Reduces API quota usage
- Reddit rate limit: 60 requests/minute (our crawler uses ~10 requests per run)

---

## 5. Configuration

### 5.1 Environment Variables

```bash
# .env (ADD)

# Reddit API Credentials
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=Craveny/1.0 (Stock Analysis Bot)

# Reddit Crawler Settings
REDDIT_SUBREDDITS=stocks,investing,Korea_Stock,StockMarket
REDDIT_KEYWORDS=Samsung,SK Hynix,LG,Hyundai,Kia,Korean stocks,KOSPI
REDDIT_MIN_UPVOTES=10
REDDIT_MIN_COMMENTS=2
REDDIT_LOOKBACK_HOURS=24
```

### 5.2 Settings Configuration

```python
# backend/config.py (MODIFIED)

class Settings(BaseSettings):
    # ... existing settings ...

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "Craveny/1.0"

    # Reddit Crawler
    REDDIT_SUBREDDITS: str = "stocks,investing,Korea_Stock,StockMarket"
    REDDIT_KEYWORDS: str = "Samsung,SK Hynix,LG,Hyundai,Kia,Korean stocks,KOSPI"
    REDDIT_MIN_UPVOTES: int = 10
    REDDIT_MIN_COMMENTS: int = 2
    REDDIT_LOOKBACK_HOURS: int = 24
```

---

## 6. Filtering and Quality Control

### 6.1 Multi-Level Filtering Strategy

```python
# backend/crawlers/reddit_crawler.py

class RedditCrawler:

    def _apply_quality_filters(self, posts: List[NewsArticleData]) -> List[NewsArticleData]:
        """
        Apply multi-level quality filters

        Level 1: Engagement metrics
        - Upvote ratio > 0.7 (controversial posts filtered)
        - Comment/upvote ratio > 0.01 (discussion quality)

        Level 2: Content quality
        - Title + content length > 100 chars
        - Not marked as spam/removed

        Level 3: Language detection
        - English content (langdetect library)
        - Korean company names recognized
        """
        filtered = []

        for post in posts:
            # Level 1: Engagement
            upvotes = post.metadata.get('upvotes', 0)
            comments = post.metadata.get('num_comments', 0)

            if upvotes < self.min_upvotes:
                continue
            if comments < self.min_comments:
                continue

            # Level 2: Content quality
            content_length = len(post.title) + len(post.content)
            if content_length < 100:
                continue

            # Level 3: Language (basic check - can be enhanced)
            if not self._is_relevant_language(post.title + " " + post.content):
                continue

            filtered.append(post)

        return filtered

    def _is_relevant_language(self, text: str) -> bool:
        """Check if text is in English or contains Korean company names"""
        # Simple heuristic: if contains ASCII and Korean company names
        has_ascii = any(ord(c) < 128 for c in text)
        has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
        return has_ascii and has_keyword
```

### 6.2 Deduplication Strategy

**Leverage existing `EmbeddingDeduplicator`**:
- ✅ Cross-platform deduplication (Reddit post similar to news article)
- ✅ Same embedding similarity threshold (0.95 for high similarity)
- ✅ No changes needed to deduplication logic

**Example scenario**:
```
News: "삼성전자, 미국 AI 칩 시장 진출"
Reddit: "Samsung entering US AI chip market - thoughts?"
→ Embedding similarity: 0.96 → Skip prediction for Reddit post
```

---

## 7. Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Basic Reddit integration without breaking existing system

1. **Database Migration** (Day 1-2)
   - [ ] Add `content_type`, `url`, `author`, Reddit fields to `NewsArticle`
   - [ ] Create and test migration script
   - [ ] Backup production database

2. **Reddit Crawler Development** (Day 3-5)
   - [ ] Implement `RedditCrawler` class
   - [ ] PRAW integration and authentication
   - [ ] Keyword filtering logic
   - [ ] Unit tests for crawler

3. **Pipeline Integration** (Day 5-7)
   - [ ] Extend `NewsArticleData` with metadata
   - [ ] Modify `NewsSaver` to handle Reddit posts
   - [ ] Test cross-platform deduplication
   - [ ] Verify prediction pipeline works

### Phase 2: Production Deployment (Week 2)
**Goal**: Deploy to production and monitor

4. **Scheduler Integration** (Day 8-9)
   - [ ] Add Reddit crawler to `CrawlerScheduler`
   - [ ] Configure 30-minute interval
   - [ ] Test scheduler in staging environment

5. **Configuration and Testing** (Day 10-12)
   - [ ] Reddit API credentials setup
   - [ ] Environment variable configuration
   - [ ] End-to-end testing with real Reddit data
   - [ ] Performance monitoring setup

6. **Production Rollout** (Day 13-14)
   - [ ] Deploy migration to production
   - [ ] Enable Reddit crawler with monitoring
   - [ ] Validate data quality and prediction accuracy
   - [ ] Monitor API quota usage

### Phase 3: Optimization (Week 3)
**Goal**: Fine-tune quality and expand coverage

7. **Quality Tuning** (Day 15-17)
   - [ ] Analyze collected Reddit data quality
   - [ ] Adjust min_upvotes, min_comments thresholds
   - [ ] Refine keyword list based on results
   - [ ] Improve language detection

8. **Feature Enhancement** (Day 18-21)
   - [ ] Add Reddit-specific notification templates
   - [ ] Dashboard visualization for Reddit vs News
   - [ ] Sentiment analysis for Reddit comments
   - [ ] Performance optimization

---

## 8. Considerations and Trade-offs

### 8.1 Pros of Unified Model Approach

✅ **Code Reusability**
- Zero changes to `StockPredictor`, `AutoNotify`, `EmbeddingDeduplicator`
- Existing prediction pipeline works out-of-box

✅ **Cross-Platform Intelligence**
- Detect when Reddit post duplicates news article
- Unified analytics and search

✅ **Extensibility**
- Easy to add Twitter, Telegram, etc. in future
- Single codebase for all content types

✅ **Query Simplicity**
- Single table query for all content
- No complex JOINs needed

### 8.2 Cons and Mitigation

❌ **Table Bloat**
- Mitigation: Add `content_type` index, partition by type in future

❌ **Nullable Fields**
- Reddit posts have upvotes, news don't (NULL values)
- Mitigation: Clear documentation, use JSON metadata for platform-specific data

❌ **Schema Migration Risk**
- Mitigation: Thorough testing, reversible migration script, backup

### 8.3 Alternative Considered: Separate RedditPost Model

**If We Had Chosen Separate Model**:

```python
class RedditPost(Base):
    __tablename__ = "reddit_posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    content = Column(Text)
    subreddit = Column(String(100))
    upvotes = Column(Integer)
    # ... Reddit-specific fields ...
```

**Problems**:
- Need `RedditSaver` (duplicate of `NewsSaver`)
- Need `RedditPredictor` wrapper (duplicate prediction logic)
- Need `RedditNotifier` (duplicate notification logic)
- Cannot detect cross-platform duplicates
- Complex analytics queries (UNION of news + reddit)

**Conclusion**: Rejected in favor of unified model.

---

## 9. Monitoring and Metrics

### 9.1 New Metrics to Track

```python
# backend/scheduler/crawler_scheduler.py

class CrawlerScheduler:
    def __init__(self):
        # ... existing stats ...

        # Reddit 수집 통계
        self.reddit_total_crawls = 0
        self.reddit_total_saved = 0
        self.reddit_total_skipped = 0
        self.reddit_total_errors = 0

    def get_stats(self) -> dict:
        return {
            # ... existing stats ...
            "reddit": {
                "total_crawls": self.reddit_total_crawls,
                "total_saved": self.reddit_total_saved,
                "total_skipped": self.reddit_total_skipped,
                "total_errors": self.reddit_total_errors,
                "success_rate": ...,
                "avg_posts_per_run": ...,
                "api_quota_usage": ...,
            }
        }
```

### 9.2 Quality Metrics

- **Reddit vs News prediction accuracy**
  - Track separately to validate Reddit content quality

- **Cross-platform duplication rate**
  - Monitor how often Reddit posts duplicate news

- **Engagement correlation**
  - Does upvote count correlate with prediction accuracy?

---

## 10. Future Expansion

### 10.1 Additional Platforms (Future)

**Twitter Integration** (Similar pattern):
```python
class TwitterCrawler(BaseNewsCrawler):
    # Fetch tweets about Korean stocks
    # Store as content_type=ContentType.TWITTER
```

**Telegram Channels** (Similar pattern):
```python
class TelegramCrawler(BaseNewsCrawler):
    # Monitor investment Telegram channels
    # Store as content_type=ContentType.TELEGRAM
```

### 10.2 Advanced Features

- **Reddit Comment Analysis**: Analyze sentiment from top comments
- **User Reputation Scoring**: Weight posts from users with high karma
- **Flair-based Filtering**: Prioritize posts with "DD" (Due Diligence) flair
- **Real-time Stream**: Use Reddit streaming API for instant alerts

---

## 11. Risk Analysis

### 11.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Reddit API quota exceeded | High | Medium | Implement rate limiting, monitor usage |
| Migration breaks existing news | Critical | Low | Extensive testing, rollback plan |
| Reddit content quality poor | Medium | Medium | Multi-level filtering, quality metrics |
| Prediction accuracy drops | High | Low | A/B test Reddit vs News predictions |
| Database performance degradation | Medium | Low | Add indexes, monitor query performance |

### 11.2 Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Reddit API changes | Medium | PRAW library handles API changes |
| Increased storage costs | Low | Archive old Reddit posts after 30 days |
| False positives in keyword matching | Medium | Refine keywords based on data |

---

## 12. Success Criteria

### 12.1 Technical Success

- ✅ Zero downtime during migration
- ✅ Existing news pipeline unaffected
- ✅ Reddit crawler runs successfully every 30 minutes
- ✅ <5% error rate in Reddit data collection
- ✅ Prediction pipeline works for Reddit posts

### 12.2 Business Success

- ✅ Collect ≥20 quality Reddit posts per day
- ✅ Prediction accuracy for Reddit posts ≥60%
- ✅ Identify at least 1 unique insight per week not found in Korean news
- ✅ User feedback: Reddit data provides value

---

## 13. API Credentials Setup

### 13.1 Reddit API Application

**Steps**:
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in:
   - Name: Craveny Stock Analysis
   - Type: script
   - Description: Korean stock sentiment analysis
   - About URL: (your website)
   - Redirect URI: http://localhost:8000 (not used for script apps)
4. Copy `client_id` and `client_secret`

**Add to `.env`**:
```bash
REDDIT_CLIENT_ID=your_14_char_client_id
REDDIT_CLIENT_SECRET=your_27_char_secret
REDDIT_USER_AGENT=Craveny/1.0 by /u/your_reddit_username
```

---

## Appendix A: Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Collection Layer                   │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ NaverCrawler │HankyungCrawler│ MaeilCrawler│ RedditCrawler │
│  (news)      │   (news)      │   (news)     │  (reddit)     │
└──────┬───────┴──────┬────────┴──────┬───────┴───────┬───────┘
       │              │               │               │
       └──────────────┴───────────────┴───────────────┘
                             ▼
                    ┌─────────────────┐
                    │   NewsSaver     │
                    │ (Unified Saver) │
                    └────────┬────────┘
                             ▼
              ┌──────────────────────────────┐
              │     NewsArticle Model        │
              │  (content_type discriminator)│
              ├──────────────────────────────┤
              │ - news (Korean sources)      │
              │ - reddit (r/stocks, etc.)    │
              │ - twitter (future)           │
              └──────────┬───────────────────┘
                         ▼
         ┌───────────────────────────────────────┐
         │      Unified Processing Pipeline      │
         ├───────────────────────────────────────┤
         │ 1. EmbeddingDeduplicator              │
         │    (cross-platform dedup)             │
         │ 2. StockPredictor                     │
         │    (AI prediction)                    │
         │ 3. AutoNotify                         │
         │    (Telegram alerts)                  │
         └───────────────────────────────────────┘
```

## Appendix B: Data Flow Diagram

```
Reddit r/stocks
      ↓
RedditCrawler.fetch_news()
      ↓
[Filter by keywords: Samsung, Hynix, ...]
[Filter by quality: upvotes≥10, comments≥2]
      ↓
NewsArticleData(
  title="Samsung Q4 earnings thoughts?",
  content="...",
  source="reddit:r/stocks",
  metadata={upvotes: 45, comments: 12}
)
      ↓
NewsSaver.save_news()
      ↓
EmbeddingDeduplicator.should_skip_prediction()
      ↓
[Compare with existing news and Reddit posts]
      ↓
StockPredictor.predict()
      ↓
Prediction(
  news_id=123,
  stock_code="005930",
  direction="up",
  confidence=0.72
)
      ↓
AutoNotify.send_notification()
      ↓
Telegram: "🔴 Reddit r/stocks: Samsung Q4 earnings..."
```

---

## Conclusion

This architecture design provides a **minimal-impact, extensible solution** for Reddit API integration:

1. **Unified data model** reduces code duplication and enables cross-platform intelligence
2. **Extends existing pipeline** without breaking news crawling
3. **Production-ready** with monitoring, error handling, and quality filters
4. **Future-proof** design supports Twitter, Telegram, and other platforms

**Estimated Effort**: 3 weeks (1 developer)
- Week 1: Development and testing
- Week 2: Production deployment
- Week 3: Optimization and monitoring

**Next Steps**:
1. Review and approve this design
2. Set up Reddit API credentials
3. Create database backup
4. Begin Phase 1 implementation

