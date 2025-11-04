# Reddit Integration - Quick Reference

## Key Design Decisions

### ✅ Chosen: Unified Content Model
Extend `NewsArticle` with `content_type` field to support multiple platforms.

**Why?**
- Reuses 100% of existing pipeline (predictor, notifier, deduplicator)
- Enables cross-platform deduplication
- Single query for unified analytics
- Easy to add Twitter, Telegram later

### ❌ Rejected: Separate RedditPost Model
Would require duplicating all pipeline logic and prevents cross-platform intelligence.

---

## Implementation Checklist

### Database Changes
- [x] Add `content_type` field (news, reddit, twitter, telegram) - **String(20) instead of enum**
- [x] Add `url`, `author`, `upvotes`, `num_comments`, `subreddit` fields
- [x] Add `extra_metadata` JSONB field for platform-specific data
- [x] Create migration script and test (**scripts/migrate_add_reddit_fields.py**)
- [x] Fixed: SQLAlchemy metadata reserved word → renamed to `extra_metadata`
- [x] Fixed: Enum uppercase/lowercase issue → changed to String(20)

### New Components
- [x] `RedditCrawler` class extending `BaseNewsCrawler` (**backend/crawlers/reddit_crawler.py**)
- [x] PRAW integration with rate limiting (2s/request)
- [x] Keyword filtering (Samsung, SK Hynix, LG, Hyundai, Kia, KOSPI)
- [x] Quality filters (min upvotes: 10, min comments: 2, lookback: 24h)

### Pipeline Modifications
- [x] Extend `NewsArticleData` with author and metadata support
- [x] Modify `NewsSaver.save_news()` to handle content_type auto-detection
- [x] Integration test script created (**scripts/test_reddit_integration.py**)
- [ ] Add Reddit crawler to scheduler (30-min interval) - **Pending**

### Configuration
- [x] Set up Reddit API credentials (client_id, secret, user_agent)
- [x] Configure subreddits (stocks, investing, StockMarket)
- [x] Configure keywords and thresholds in .env
- [x] Add environment variables to backend/config.py

### A/B Testing Enhancement
- [x] A/B Test Config table migration (**scripts/migrate_create_ab_test_config.py**)
- [x] DB-based dynamic A/B testing (no hardcoding)
- [x] Enhanced A/B notification format with:
  - [x] Consensus highlighting (두 모델 일치 시 강조)
  - [x] Historical pattern analysis (T+1, T+3, T+5일)
  - [x] Confidence breakdown (유사 뉴스 품질, 패턴 일관성, 공시 영향)
  - [x] Prediction reasoning (150자 요약)

---

## Data Model Changes

```python
# Before: NewsArticle (news only)
class NewsArticle(Base):
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    content = Column(Text)
    published_at = Column(DateTime)
    source = Column(String(100))  # 'naver', 'hankyung'
    stock_code = Column(String(10))

# After: NewsArticle (multi-platform)
class NewsArticle(Base):
    # Existing fields (unchanged)
    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    content = Column(Text)
    published_at = Column(DateTime)
    source = Column(String(100))  # 'naver', 'reddit:r/stocks'
    stock_code = Column(String(10))

    # NEW: Platform support
    content_type = Column(Enum('news', 'reddit', 'twitter'))
    url = Column(String(1000))
    author = Column(String(200))

    # NEW: Reddit-specific
    upvotes = Column(Integer, nullable=True)
    num_comments = Column(Integer, nullable=True)
    subreddit = Column(String(100), nullable=True)
    metadata = Column(JSON, nullable=True)
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              Data Collection Layer                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Naver   │  │ Hankyung │  │ RedditCrawler    │  │
│  │ Crawler  │  │ Crawler  │  │ (NEW)            │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────────────┘  │
└───────┼─────────────┼─────────────┼────────────────┘
        │             │             │
        └─────────────┴─────────────┘
                      ▼
            ┌──────────────────┐
            │   NewsSaver      │ ← Modified to handle content_type
            │  (Unified Saver) │
            └─────────┬────────┘
                      ▼
         ┌────────────────────────┐
         │   NewsArticle Table    │
         │ ┌────────────────────┐ │
         │ │ content_type=news  │ │ ← Korean news articles
         │ └────────────────────┘ │
         │ ┌────────────────────┐ │
         │ │ content_type=reddit│ │ ← Reddit posts
         │ └────────────────────┘ │
         └─────────┬──────────────┘
                   ▼
    ┌──────────────────────────────┐
    │  Existing Pipeline (No Change)│
    ├──────────────────────────────┤
    │ 1. EmbeddingDeduplicator     │
    │    ↓                          │
    │ 2. StockPredictor            │
    │    ↓                          │
    │ 3. AutoNotify                │
    │    ↓                          │
    │ 4. Telegram Alert            │
    └──────────────────────────────┘
```

---

## Reddit Crawler Configuration

### Target Subreddits
- r/stocks (2.5M members)
- r/investing (2.0M members)
- r/Korea_Stock (focused community)
- r/StockMarket (1.5M members)

### Search Keywords
- Samsung, SK Hynix, LG, Hyundai, Kia
- Korean stocks, KOSPI, Korea market

### Quality Filters
- Minimum upvotes: 10
- Minimum comments: 2
- Lookback period: 24 hours
- Content length: >100 characters

### Scheduler
- Crawl interval: 30 minutes (less frequent than news)
- Rate limit: 2 seconds between requests
- Max posts per run: 50

---

## Example Data Flow

### Reddit Post
```json
{
  "title": "Samsung Q4 earnings look strong - thoughts?",
  "selftext": "Samsung reported better than expected Q4 earnings...",
  "subreddit": "stocks",
  "score": 45,
  "num_comments": 12,
  "created_utc": 1234567890
}
```

### Converted to NewsArticle
```python
NewsArticle(
    title="Samsung Q4 earnings look strong - thoughts?",
    content="Samsung reported better than expected Q4 earnings...",
    published_at=datetime(2024, 1, 15, 10, 30),
    source="reddit:r/stocks",
    stock_code="005930",  # Auto-mapped to Samsung

    # Platform fields
    content_type=ContentType.REDDIT,
    url="https://reddit.com/r/stocks/comments/abc123",
    author="stock_analyst_42",

    # Reddit-specific
    upvotes=45,
    num_comments=12,
    subreddit="stocks",
    metadata={
        "post_id": "abc123",
        "link_flair_text": "Discussion"
    }
)
```

### Prediction Result
```python
Prediction(
    news_id=123,
    stock_code="005930",
    direction="up",
    confidence=0.72,
    reasoning="Positive sentiment from international investors...",
    source_type="reddit"  # For analytics
)
```

---

## Query Examples

### Get All Content (News + Reddit)
```python
# Single query for all content types
articles = db.query(NewsArticle).filter(
    NewsArticle.stock_code == "005930"
).all()
```

### Get Reddit Posts Only
```python
reddit_posts = db.query(NewsArticle).filter(
    NewsArticle.content_type == ContentType.REDDIT,
    NewsArticle.stock_code == "005930"
).all()
```

### Cross-Platform Analysis
```python
# Compare news vs reddit sentiment
news_predictions = db.query(Prediction).join(NewsArticle).filter(
    NewsArticle.content_type == ContentType.NEWS,
    NewsArticle.stock_code == "005930"
).all()

reddit_predictions = db.query(Prediction).join(NewsArticle).filter(
    NewsArticle.content_type == ContentType.REDDIT,
    NewsArticle.stock_code == "005930"
).all()
```

---

## Monitoring Metrics

### Collection Metrics
- Reddit crawl success rate
- Posts collected per run
- Keyword match rate
- Quality filter pass rate

### Quality Metrics
- Reddit vs News prediction accuracy
- Cross-platform duplication rate
- Average engagement (upvotes, comments)
- Reddit-specific alert value

### Performance Metrics
- Reddit API quota usage
- Crawler execution time
- Database query performance
- Storage growth rate

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Reddit API quota exceeded | Rate limiting, monitor usage, fallback |
| Migration breaks news pipeline | Extensive testing, rollback plan, staging |
| Poor Reddit content quality | Multi-level filters, quality metrics |
| Database performance | Indexes on content_type, subreddit, monitor queries |

---

## Timeline

### Week 1: Development
- Days 1-2: Database migration
- Days 3-5: Reddit crawler development
- Days 5-7: Pipeline integration and testing

### Week 2: Deployment
- Days 8-9: Scheduler integration
- Days 10-12: End-to-end testing
- Days 13-14: Production rollout

### Week 3: Optimization
- Days 15-17: Quality tuning
- Days 18-21: Feature enhancement

---

## Success Criteria

✅ **Technical**
- Zero downtime during migration
- Reddit crawler runs successfully every 30 minutes
- <5% error rate
- Existing news pipeline unaffected

✅ **Business**
- Collect ≥20 quality Reddit posts per day
- Prediction accuracy ≥60% for Reddit posts
- Identify unique insights not in Korean news
- Positive user feedback

---

## Environment Variables (.env)

```bash
# Reddit API Credentials
REDDIT_CLIENT_ID=your_14_char_client_id
REDDIT_CLIENT_SECRET=your_27_char_secret
REDDIT_USER_AGENT=Craveny/1.0 by /u/your_username

# Reddit Crawler Settings
REDDIT_SUBREDDITS=stocks,investing,Korea_Stock,StockMarket
REDDIT_KEYWORDS=Samsung,SK Hynix,LG,Hyundai,Kia,Korean stocks,KOSPI
REDDIT_MIN_UPVOTES=10
REDDIT_MIN_COMMENTS=2
REDDIT_LOOKBACK_HOURS=24
```

---

## Implementation Status

### ✅ Completed (2025-01-04)
1. ✅ Review architecture design
2. ✅ Set up Reddit API credentials (client_id: WVg2aj0Evr4H7Cgc2H6X-w)
3. ✅ Create migration script (migrate_add_reddit_fields.py)
4. ✅ Run migration successfully (7 columns + 3 indexes, 887 existing records preserved)
5. ✅ Implement RedditCrawler with PRAW
6. ✅ Test Reddit integration (1 post collected and saved with ID=975)
7. ✅ Fix SQLEnum → String(20) conversion
8. ✅ Fix metadata reserved word issue
9. ✅ Enhanced A/B notification format
10. ✅ DB-based A/B test configuration

### 🔄 In Progress
- Add Reddit crawler to scheduler (30-min interval)
- Production monitoring setup

### ⬜ Remaining
- Performance optimization based on production metrics
- Extended Reddit feature (comment sentiment analysis)

---

## Implementation Results & Lessons Learned

### Database Migration Success
- **Migration**: Successfully added 7 columns + 3 indexes
- **Data Preservation**: 887 existing news articles preserved with `content_type='news'`
- **Critical Fixes**:
  - SQLAlchemy reserved word: `metadata` → `extra_metadata` (Python attribute) while keeping DB column name as `metadata`
  - Enum type mismatch: Changed from `SQLEnum(ContentType)` to `String(20)` to avoid uppercase/lowercase issues

### Reddit API Integration
- **Credentials**: Successfully created Reddit app (Script type)
- **First Collection**: 2 posts collected from r/investing (r/Korea_Stock doesn't exist)
- **First Save**: Reddit post ID=975 saved successfully with all fields populated

### A/B Testing Enhancement
- **Before**: Hardcoded A/B test (environment variables)
- **After**: DB-based dynamic configuration (`ab_test_config` table)
- **Current Setup**: Qwen3 Max vs DeepSeek V3.2
- **Notification Format**: Enhanced with:
  - Consensus highlighting (🎯 두 모델 모두 상승 예측!)
  - Historical pattern analysis (과거 유사 사례 T+1/T+3/T+5일)
  - Confidence breakdown (유사 뉴스 품질 85/100, 패턴 일관성 70/100)
  - Prediction reasoning (150자 요약)

### Technical Challenges Resolved
1. **SQLEnum Issue**: Python enum `.name` (uppercase) vs DB enum value (lowercase)
   - Solution: Changed to `String(20)` for flexibility
2. **Reserved Word**: `metadata` conflicts with SQLAlchemy's internal attribute
   - Solution: `extra_metadata = Column('metadata', JSONB)`
3. **Content Type Detection**: Auto-detect platform from source prefix
   - `reddit:r/stocks` → `content_type='reddit'`
   - `naver` → `content_type='news'`

### Performance Metrics
- **Reddit Crawling**: 2 posts/20 attempted (10% relevant rate)
- **Rate Limiting**: 2 seconds/request (compliant with Reddit API)
- **Prediction**: Automatic prediction triggered when stock code detected
- **Notification**: A/B comparison format working correctly

---

## Future Expansion

### Easy to Add Later
- **Twitter Integration**: Similar pattern, `content_type=ContentType.TWITTER`
- **Telegram Channels**: Monitor investment channels
- **Advanced Reddit Features**:
  - Analyze comment sentiment
  - User reputation scoring
  - Real-time streaming API

