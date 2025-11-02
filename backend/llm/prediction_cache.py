"""
예측 결과 캐싱 모듈

Redis를 사용하여 주가 예측 결과를 캐싱합니다.
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import timedelta

import redis

from backend.config import settings


logger = logging.getLogger(__name__)


class PredictionCache:
    """예측 결과 캐시 관리 클래스"""

    def __init__(self):
        """캐시 초기화"""
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )

        # 캐시 설정
        self.cache_ttl = 86400  # 24시간 (초 단위)
        self.key_prefix = "prediction:"

        # 통계 카운터
        self.stats_key = "prediction:stats"

    def _get_cache_key(self, news_id: int, stock_code: str) -> str:
        """
        캐시 키 생성

        Args:
            news_id: 뉴스 ID
            stock_code: 종목 코드

        Returns:
            Redis 캐시 키 (예: "prediction:123:005930")
        """
        return f"{self.key_prefix}{news_id}:{stock_code}"

    def get(self, news_id: int, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        캐시에서 예측 결과 조회

        Args:
            news_id: 뉴스 ID
            stock_code: 종목 코드

        Returns:
            예측 결과 딕셔너리 또는 None (캐시 미스)
        """
        try:
            cache_key = self._get_cache_key(news_id, stock_code)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                # 캐시 히트
                self._increment_stat("hits")
                logger.info(f"캐시 히트: news_id={news_id}, stock_code={stock_code}")
                return json.loads(cached_data)
            else:
                # 캐시 미스
                self._increment_stat("misses")
                logger.info(f"캐시 미스: news_id={news_id}, stock_code={stock_code}")
                return None

        except redis.RedisError as e:
            logger.error(f"Redis 조회 실패: {e}", exc_info=True)
            self._increment_stat("errors")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}", exc_info=True)
            self._increment_stat("errors")
            return None

    def set(
        self,
        news_id: int,
        stock_code: str,
        prediction: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        예측 결과를 캐시에 저장

        Args:
            news_id: 뉴스 ID
            stock_code: 종목 코드
            prediction: 예측 결과
            ttl: TTL (초), None이면 기본값 사용

        Returns:
            저장 성공 여부
        """
        try:
            cache_key = self._get_cache_key(news_id, stock_code)
            ttl = ttl or self.cache_ttl

            # JSON 직렬화
            cache_value = json.dumps(prediction, ensure_ascii=False)

            # Redis 저장 (TTL 포함)
            self.redis_client.setex(
                name=cache_key,
                time=timedelta(seconds=ttl),
                value=cache_value,
            )

            self._increment_stat("sets")
            logger.info(
                f"캐시 저장: news_id={news_id}, stock_code={stock_code}, ttl={ttl}s"
            )
            return True

        except redis.RedisError as e:
            logger.error(f"Redis 저장 실패: {e}", exc_info=True)
            self._increment_stat("errors")
            return False

        except (TypeError, ValueError) as e:
            logger.error(f"JSON 직렬화 실패: {e}", exc_info=True)
            self._increment_stat("errors")
            return False

    def delete(self, news_id: int, stock_code: str) -> bool:
        """
        캐시에서 예측 결과 삭제

        Args:
            news_id: 뉴스 ID
            stock_code: 종목 코드

        Returns:
            삭제 성공 여부
        """
        try:
            cache_key = self._get_cache_key(news_id, stock_code)
            result = self.redis_client.delete(cache_key)

            if result > 0:
                logger.info(f"캐시 삭제: news_id={news_id}, stock_code={stock_code}")
                self._increment_stat("deletes")
                return True
            else:
                logger.warning(f"캐시 삭제 실패 (키 없음): {cache_key}")
                return False

        except redis.RedisError as e:
            logger.error(f"Redis 삭제 실패: {e}", exc_info=True)
            self._increment_stat("errors")
            return False

    def clear_all(self) -> int:
        """
        모든 예측 캐시 삭제

        Returns:
            삭제된 키 개수
        """
        try:
            # 패턴 매칭으로 모든 prediction 키 찾기
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"캐시 전체 삭제: {deleted}개 키")
                return deleted
            else:
                logger.info("삭제할 캐시 없음")
                return 0

        except redis.RedisError as e:
            logger.error(f"Redis 전체 삭제 실패: {e}", exc_info=True)
            return 0

    def get_ttl(self, news_id: int, stock_code: str) -> Optional[int]:
        """
        캐시 TTL 조회

        Args:
            news_id: 뉴스 ID
            stock_code: 종목 코드

        Returns:
            남은 TTL (초) 또는 None
        """
        try:
            cache_key = self._get_cache_key(news_id, stock_code)
            ttl = self.redis_client.ttl(cache_key)

            if ttl > 0:
                return ttl
            else:
                return None

        except redis.RedisError as e:
            logger.error(f"TTL 조회 실패: {e}", exc_info=True)
            return None

    def _increment_stat(self, stat_name: str):
        """
        통계 카운터 증가

        Args:
            stat_name: 통계 항목명 (hits, misses, sets, deletes, errors)
        """
        try:
            self.redis_client.hincrby(self.stats_key, stat_name, 1)
        except redis.RedisError as e:
            logger.error(f"통계 증가 실패: {e}")

    def get_stats(self) -> Dict[str, int]:
        """
        캐시 통계 조회

        Returns:
            통계 딕셔너리 {hits, misses, sets, deletes, errors}
        """
        try:
            stats = self.redis_client.hgetall(self.stats_key)

            # 문자열을 정수로 변환
            return {
                "hits": int(stats.get("hits", 0)),
                "misses": int(stats.get("misses", 0)),
                "sets": int(stats.get("sets", 0)),
                "deletes": int(stats.get("deletes", 0)),
                "errors": int(stats.get("errors", 0)),
            }

        except redis.RedisError as e:
            logger.error(f"통계 조회 실패: {e}", exc_info=True)
            return {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "deletes": 0,
                "errors": 0,
            }

    def get_hit_rate(self) -> float:
        """
        캐시 히트율 계산

        Returns:
            히트율 (0.0 ~ 1.0)
        """
        stats = self.get_stats()
        total = stats["hits"] + stats["misses"]

        if total == 0:
            return 0.0

        return stats["hits"] / total

    def reset_stats(self):
        """통계 초기화"""
        try:
            self.redis_client.delete(self.stats_key)
            logger.info("캐시 통계 초기화")
        except redis.RedisError as e:
            logger.error(f"통계 초기화 실패: {e}", exc_info=True)


# 싱글톤 인스턴스
_cache: Optional[PredictionCache] = None


def get_prediction_cache() -> PredictionCache:
    """
    PredictionCache 싱글톤 인스턴스를 반환합니다.

    Returns:
        PredictionCache 인스턴스
    """
    global _cache
    if _cache is None:
        _cache = PredictionCache()
    return _cache
