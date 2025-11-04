"""
Reddit 크롤러 구현

PRAW (Python Reddit API Wrapper)를 사용하여 Reddit 게시글을 수집합니다.
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

import praw
from praw.models import Submission

from backend.crawlers.base_crawler import BaseNewsCrawler, NewsArticleData
from backend.config import settings


logger = logging.getLogger(__name__)


class RedditCrawler(BaseNewsCrawler):
    """Reddit 크롤러 클래스"""

    def __init__(
        self,
        subreddits: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        min_upvotes: int = 10,
        min_comments: int = 2,
        lookback_hours: int = 24,
    ):
        """
        Args:
            subreddits: 수집할 subreddit 목록 (기본값: config 설정)
            keywords: 필터링 키워드 목록 (기본값: config 설정)
            min_upvotes: 최소 upvote 수 (기본값: 10)
            min_comments: 최소 댓글 수 (기본값: 2)
            lookback_hours: 수집 기간 (시간, 기본값: 24)
        """
        super().__init__(
            source_name="reddit",
            timeout=30,
            max_retries=3,
            rate_limit_seconds=2.0,  # Reddit API rate limit
        )

        # Reddit API 초기화
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )

        # 크롤링 설정
        self.subreddits = subreddits or settings.REDDIT_SUBREDDITS.split(',')
        self.keywords = keywords or settings.REDDIT_KEYWORDS.split(',')
        self.min_upvotes = min_upvotes
        self.min_comments = min_comments
        self.lookback_hours = lookback_hours

        # 키워드 정규화 (소문자 변환, 공백 제거)
        self.keywords = [kw.strip().lower() for kw in self.keywords]

        logger.info(
            f"RedditCrawler 초기화: "
            f"subreddits={self.subreddits}, "
            f"keywords={len(self.keywords)}개, "
            f"lookback_hours={self.lookback_hours}"
        )

    def _is_relevant(self, submission: Submission) -> bool:
        """
        게시글이 수집 대상인지 확인합니다.

        Args:
            submission: Reddit 게시글

        Returns:
            수집 대상 여부
        """
        # 1. upvote 수 확인
        if submission.score < self.min_upvotes:
            return False

        # 2. 댓글 수 확인
        if submission.num_comments < self.min_comments:
            return False

        # 3. 작성 시간 확인
        created_time = datetime.fromtimestamp(submission.created_utc)
        cutoff_time = datetime.utcnow() - timedelta(hours=self.lookback_hours)
        if created_time < cutoff_time:
            return False

        # 4. 키워드 확인 (제목 또는 본문에 포함)
        text = f"{submission.title} {submission.selftext}".lower()

        for keyword in self.keywords:
            if keyword in text:
                return True

        return False

    def _submission_to_news_data(self, submission: Submission) -> NewsArticleData:
        """
        Reddit 게시글을 NewsArticleData로 변환합니다.

        Args:
            submission: Reddit 게시글

        Returns:
            NewsArticleData 객체
        """
        # 제목
        title = submission.title

        # 본문 (selftext가 없으면 제목만 사용)
        content = submission.selftext if submission.selftext else submission.title

        # 발표 시간
        published_at = datetime.fromtimestamp(submission.created_utc)

        # 소스 식별자 (예: "reddit:r/stocks")
        source = f"reddit:r/{submission.subreddit.display_name}"

        # URL
        url = f"https://www.reddit.com{submission.permalink}"

        # 작성자
        author = str(submission.author) if submission.author else "[deleted]"

        # 메타데이터
        metadata = {
            "upvotes": submission.score,
            "num_comments": submission.num_comments,
            "subreddit": submission.subreddit.display_name,
            "post_id": submission.id,
            "upvote_ratio": submission.upvote_ratio,
            "is_self": submission.is_self,
            "link_flair_text": submission.link_flair_text,
        }

        return NewsArticleData(
            title=title,
            content=content,
            published_at=published_at,
            source=source,
            url=url,
            author=author,
            metadata=metadata,
        )

    def fetch_news(self, limit: int = 100) -> List[NewsArticleData]:
        """
        Reddit 게시글을 크롤링합니다.

        Args:
            limit: subreddit당 가져올 최대 게시글 수

        Returns:
            NewsArticleData 리스트
        """
        all_news = []

        for subreddit_name in self.subreddits:
            try:
                logger.info(f"r/{subreddit_name} 크롤링 시작...")

                subreddit = self.reddit.subreddit(subreddit_name)

                # 최근 게시글 수집 (hot, new 조합)
                submissions = list(subreddit.hot(limit=limit // 2)) + \
                             list(subreddit.new(limit=limit // 2))

                relevant_count = 0

                for submission in submissions:
                    # Rate limiting 적용
                    self._apply_rate_limit()

                    # 관련성 검사
                    if not self._is_relevant(submission):
                        continue

                    # NewsArticleData로 변환
                    try:
                        news_data = self._submission_to_news_data(submission)
                        all_news.append(news_data)
                        relevant_count += 1

                        logger.debug(
                            f"✅ {submission.title[:50]} "
                            f"(↑{submission.score}, 💬{submission.num_comments})"
                        )

                    except Exception as e:
                        logger.warning(f"게시글 변환 실패: {submission.id}, {e}")
                        continue

                logger.info(
                    f"r/{subreddit_name} 크롤링 완료: "
                    f"{relevant_count}개 수집 (총 {len(submissions)}개 중)"
                )

            except Exception as e:
                logger.error(f"r/{subreddit_name} 크롤링 실패: {e}", exc_info=True)
                continue

        logger.info(f"Reddit 크롤링 총 {len(all_news)}개 게시글 수집")
        return all_news


if __name__ == "__main__":
    """테스트 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    crawler = RedditCrawler()
    news_list = crawler.fetch_news(limit=50)

    print(f"\n총 {len(news_list)}개 게시글 수집:")
    for news in news_list[:5]:  # 처음 5개만 출력
        print(f"\n제목: {news.title}")
        print(f"소스: {news.source}")
        print(f"작성자: {news.author}")
        print(f"URL: {news.url}")
        print(f"Upvotes: {news.metadata.get('upvotes')}")
        print(f"Comments: {news.metadata.get('num_comments')}")
