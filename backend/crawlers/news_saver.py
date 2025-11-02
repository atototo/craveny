"""
뉴스 저장 로직

크롤링한 뉴스를 데이터베이스에 저장합니다.
"""
import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from backend.crawlers.base_crawler import NewsArticleData
from backend.db.models.news import NewsArticle
from backend.db.models.prediction import Prediction
from backend.utils.stock_mapping import get_stock_mapper
from backend.utils.deduplicator import get_deduplicator
from backend.utils.encoding_normalizer import get_encoding_normalizer
from backend.llm.predictor import StockPredictor
from backend.llm.vector_search import get_vector_search
from backend.services.stock_analysis_service import update_stock_analysis_summary
import asyncio


logger = logging.getLogger(__name__)


class NewsSaver:
    """뉴스 저장 클래스"""

    def __init__(self, db: Session, auto_predict: bool = True):
        """
        Args:
            db: 데이터베이스 세션
            auto_predict: 뉴스 저장 시 자동 예측 실행 여부 (기본값: True)
        """
        self.db = db
        self.auto_predict = auto_predict
        self.stock_mapper = get_stock_mapper()
        self.deduplicator = get_deduplicator()
        self.encoding_normalizer = get_encoding_normalizer()

        # 자동 예측이 활성화되어 있으면 predictor 초기화
        self.predictor = None
        if self.auto_predict:
            try:
                self.predictor = StockPredictor()
                logger.info("자동 예측 시스템 활성화")
            except Exception as e:
                logger.warning(f"예측 시스템 초기화 실패, 자동 예측 비활성화: {e}")
                self.auto_predict = False

    def _extract_stock_code(self, news_data: NewsArticleData) -> Optional[str]:
        """
        뉴스 데이터에서 종목코드를 추출합니다.

        Args:
            news_data: 뉴스 데이터

        Returns:
            종목코드 또는 None
        """
        # 1. 뉴스 데이터에 기업명이 있으면 직접 매핑
        if news_data.company_name:
            stock_code = self.stock_mapper.get_stock_code(news_data.company_name)
            if stock_code:
                logger.debug(f"기업명으로 종목코드 매칭: {news_data.company_name} -> {stock_code}")
                return stock_code

        # 2. 제목에서 기업명 찾기
        stock_code = self.stock_mapper.find_stock_code_in_text(news_data.title)
        if stock_code:
            logger.debug(f"제목에서 종목코드 발견: {news_data.title[:50]} -> {stock_code}")
            return stock_code

        # 3. 본문에서 기업명 찾기
        stock_code = self.stock_mapper.find_stock_code_in_text(news_data.content)
        if stock_code:
            logger.debug(f"본문에서 종목코드 발견 -> {stock_code}")
            return stock_code

        logger.debug("종목코드를 찾을 수 없음")
        return None

    def save_news(self, news_data: NewsArticleData) -> Optional[NewsArticle]:
        """
        뉴스를 데이터베이스에 저장합니다.

        중복 검사를 수행하고, 중복이 아닌 경우에만 저장합니다.

        Args:
            news_data: 뉴스 데이터

        Returns:
            저장된 NewsArticle 또는 None (중복인 경우)
        """
        # 인코딩 검증 및 정규화
        title = news_data.title
        content = news_data.content

        if self.encoding_normalizer.has_broken_text(title):
            logger.warning(f"깨진 제목 감지: {title[:50]}, 복구 시도")
            title = self.encoding_normalizer.try_fix_broken_encoding(title)
            if not title:
                logger.error(f"제목 복구 실패, 뉴스 스킵")
                return None

        if self.encoding_normalizer.has_broken_text(content):
            logger.warning(f"깨진 본문 감지, 복구 시도")
            content = self.encoding_normalizer.try_fix_broken_encoding(content)

        # 중복 검사
        is_duplicate, duplicate_id = self.deduplicator.find_duplicate_in_db(
            title, self.db
        )

        if is_duplicate:
            logger.info(f"중복 뉴스 스킵: {title[:50]}")
            return None

        # 종목코드 추출
        stock_code = self._extract_stock_code(news_data)

        # NewsArticle 모델 인스턴스 생성
        news_article = NewsArticle(
            title=title,
            content=content,
            published_at=news_data.published_at,
            source=news_data.source,
            stock_code=stock_code,
        )

        # DB에 저장
        try:
            self.db.add(news_article)
            self.db.commit()
            self.db.refresh(news_article)

            logger.info(
                f"뉴스 저장 완료: ID={news_article.id}, "
                f"제목='{news_article.title[:50]}', "
                f"종목코드={stock_code or 'N/A'}"
            )

            # 자동 예측 실행 (종목코드가 있을 때만)
            if self.auto_predict and self.predictor and stock_code:
                self._run_prediction(news_article, stock_code)

            return news_article

        except Exception as e:
            self.db.rollback()
            logger.error(f"뉴스 저장 실패: {e}")
            return None

    def _run_prediction(self, news_article: NewsArticle, stock_code: str):
        """
        뉴스에 대한 예측을 실행하고 저장합니다.

        Args:
            news_article: 저장된 뉴스 기사
            stock_code: 종목 코드
        """
        try:
            logger.info(f"예측 실행 중: 뉴스 ID={news_article.id}, 종목={stock_code}")

            # 1. 유사 뉴스 검색
            vector_search = get_vector_search()
            news_text = f"{news_article.title} {news_article.content}"
            similar_news = vector_search.get_news_with_price_changes(
                news_text=news_text,
                stock_code=stock_code,
                db=self.db,
                top_k=5,
                similarity_threshold=0.7
            )

            logger.info(f"유사 뉴스 검색 완료: {len(similar_news)}건")

            # 2. 예측 실행
            current_news = {
                "title": news_article.title,
                "content": news_article.content,
                "stock_code": stock_code,
            }

            prediction_result = self.predictor.predict(
                current_news=current_news,
                similar_news=similar_news,
                news_id=news_article.id,
                use_cache=True
            )

            if prediction_result:
                # 예측 방향 변환 (한글 → 영문)
                prediction_text = prediction_result.get("prediction", "유지")
                direction_map = {"상승": "up", "하락": "down", "유지": "hold"}
                direction = direction_map.get(prediction_text, "hold")

                # 신뢰도 변환 (0-100 → 0.0-1.0)
                confidence_percent = prediction_result.get("confidence", 0)
                confidence = confidence_percent / 100.0

                # 예측 결과를 DB에 저장
                prediction = Prediction(
                    news_id=news_article.id,
                    stock_code=stock_code,
                    direction=direction,
                    confidence=confidence,
                    reasoning=prediction_result.get("reasoning", ""),
                    current_price=prediction_result.get("current_price"),
                    target_period="1일"
                )

                self.db.add(prediction)
                self.db.commit()

                logger.info(
                    f"예측 저장 완료: 뉴스 ID={news_article.id}, "
                    f"방향={prediction.direction}, 신뢰도={prediction.confidence:.2f}"
                )

                # 새 예측 저장 후 종합 분석 리포트 업데이트
                try:
                    logger.info(f"종목 {stock_code}의 종합 분석 리포트 업데이트 시작")
                    asyncio.run(update_stock_analysis_summary(stock_code, self.db, force_update=False))
                    logger.info(f"종목 {stock_code}의 종합 분석 리포트 업데이트 완료")
                except Exception as report_error:
                    logger.error(f"종합 분석 리포트 업데이트 실패: {report_error}", exc_info=True)
                    # 리포트 업데이트 실패해도 예측 저장은 유지

            else:
                logger.warning(f"예측 결과 없음: 뉴스 ID={news_article.id}")

        except Exception as e:
            logger.error(f"예측 실행 실패: 뉴스 ID={news_article.id}, {e}", exc_info=True)
            # 예측 실패해도 뉴스 저장은 유지
            self.db.rollback()

    def save_news_batch(
        self, news_list: List[NewsArticleData]
    ) -> tuple[int, int]:
        """
        여러 뉴스를 배치로 저장합니다.

        Args:
            news_list: 뉴스 데이터 리스트

        Returns:
            (저장 성공 수, 중복 스킵 수) 튜플
        """
        saved_count = 0
        skipped_count = 0

        for news_data in news_list:
            result = self.save_news(news_data)
            if result:
                saved_count += 1
            else:
                skipped_count += 1

        logger.info(
            f"배치 저장 완료: 총 {len(news_list)}건 -> "
            f"저장 {saved_count}건, 중복 스킵 {skipped_count}건"
        )

        return (saved_count, skipped_count)
