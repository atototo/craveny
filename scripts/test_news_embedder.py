"""
뉴스 임베딩 테스트 스크립트

OpenAI Embedding API 호출, Milvus 저장을 테스트합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import os

from backend.llm.embedder import NewsEmbedder, run_daily_embedding
from backend.db.session import SessionLocal
from backend.db.models.news import NewsArticle
from backend.config import settings
from pymilvus import Collection, connections

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_openai_api_key():
    """OpenAI API 키 확인"""
    logger.info("=" * 60)
    logger.info("🔑 OpenAI API 키 확인")
    logger.info("=" * 60)

    if not settings.OPENAI_API_KEY:
        logger.error("❌ OPENAI_API_KEY가 설정되지 않았습니다")
        logger.info("   .env 파일에 OPENAI_API_KEY를 추가해주세요")
        return False

    # API 키 마스킹 (앞 8자리만 표시)
    masked_key = settings.OPENAI_API_KEY[:8] + "..." + settings.OPENAI_API_KEY[-4:]
    logger.info(f"✅ OpenAI API 키: {masked_key}")
    logger.info(f"   임베딩 모델: {settings.OPENAI_EMBEDDING_MODEL}")
    logger.info("")
    return True


def test_single_embedding():
    """단일 텍스트 임베딩 테스트"""
    logger.info("=" * 60)
    logger.info("🔤 단일 텍스트 임베딩 테스트")
    logger.info("=" * 60)

    embedder = NewsEmbedder()

    test_text = "삼성전자가 3나노 공정 개발에 성공했다."
    logger.info(f"테스트 텍스트: {test_text}")

    embedding = embedder.embed_text(test_text)

    if embedding:
        logger.info(f"✅ 임베딩 생성 성공")
        logger.info(f"   차원: {len(embedding)}")
        logger.info(f"   처음 5개 값: {embedding[:5]}")
        logger.info("")
        return True
    else:
        logger.error("❌ 임베딩 생성 실패")
        logger.info("")
        return False


def test_get_unembedded_news():
    """미임베딩 뉴스 조회 테스트"""
    logger.info("=" * 60)
    logger.info("📋 미임베딩 뉴스 조회 테스트")
    logger.info("=" * 60)

    db = SessionLocal()
    embedder = NewsEmbedder()

    try:
        unembedded_news = embedder.get_unembedded_news(db, limit=10)
        logger.info(f"✅ 미임베딩 뉴스: {len(unembedded_news)}건")

        if unembedded_news:
            logger.info("   최근 3건:")
            for news in unembedded_news[:3]:
                logger.info(f"      ID={news.id}: {news.title[:40]}...")

        logger.info("")
        return True

    except Exception as e:
        logger.error(f"❌ 미임베딩 뉴스 조회 실패: {e}")
        logger.info("")
        return False

    finally:
        db.close()


def test_batch_embedding_and_save():
    """배치 임베딩 및 Milvus 저장 테스트"""
    logger.info("=" * 60)
    logger.info("📦 배치 임베딩 및 저장 테스트")
    logger.info("=" * 60)

    db = SessionLocal()
    embedder = NewsEmbedder()

    try:
        # 미임베딩 뉴스 조회 (최대 3건만 테스트)
        unembedded_news = embedder.get_unembedded_news(db, limit=3)

        if not unembedded_news:
            logger.info("⚠️  임베딩할 뉴스가 없습니다")
            logger.info("")
            return True

        logger.info(f"임베딩 대상: {len(unembedded_news)}건")

        # 텍스트 준비
        texts = [f"{news.title}\n{news.content}" for news in unembedded_news]

        # 배치 임베딩
        logger.info("OpenAI API 호출 중...")
        embeddings = embedder.embed_batch(texts)

        # 성공/실패 확인
        success_news = []
        success_embeddings = []

        for news, embedding in zip(unembedded_news, embeddings):
            if embedding is not None:
                success_news.append(news)
                success_embeddings.append(embedding)
                logger.info(f"   ✅ 뉴스 ID {news.id}: 임베딩 생성 완료")
            else:
                logger.warning(f"   ❌ 뉴스 ID {news.id}: 임베딩 생성 실패")

        # Milvus 저장
        if success_embeddings:
            logger.info(f"Milvus에 {len(success_embeddings)}건 저장 중...")
            saved_count = embedder.save_to_milvus(success_news, success_embeddings)

            if saved_count > 0:
                logger.info(f"✅ Milvus 저장 완료: {saved_count}건")
                logger.info("")
                return True
            else:
                logger.error("❌ Milvus 저장 실패")
                logger.info("")
                return False
        else:
            logger.warning("저장할 임베딩이 없습니다")
            logger.info("")
            return False

    except Exception as e:
        logger.error(f"❌ 배치 임베딩 및 저장 실패: {e}", exc_info=True)
        logger.info("")
        return False

    finally:
        db.close()


def test_milvus_query():
    """Milvus 쿼리 테스트"""
    logger.info("=" * 60)
    logger.info("🔍 Milvus 쿼리 테스트")
    logger.info("=" * 60)

    try:
        # Milvus 연결
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )

        # 컬렉션 로드
        collection = Collection("news_embeddings")
        collection.load()

        # 전체 레코드 수 조회
        count = collection.num_entities
        logger.info(f"✅ Milvus에 저장된 뉴스: {count}건")

        # 최근 3건 조회
        if count > 0:
            results = collection.query(
                expr="",
                output_fields=["news_id", "stock_code"],
                limit=3,
            )

            logger.info("   최근 3건:")
            for result in results:
                logger.info(f"      뉴스 ID: {result['news_id']}, 종목: {result.get('stock_code', 'N/A')}")

        logger.info("")
        return True

    except Exception as e:
        logger.error(f"❌ Milvus 쿼리 실패: {e}")
        logger.info("")
        return False


def main():
    """메인 실행 함수"""
    logger.info("🚀 뉴스 임베딩 시스템 테스트 시작")
    logger.info("")

    tests_passed = 0
    tests_total = 0

    # 1. API 키 확인
    tests_total += 1
    if test_openai_api_key():
        tests_passed += 1
    else:
        logger.error("API 키가 없어 나머지 테스트를 스킵합니다")
        sys.exit(1)

    # 2. 단일 임베딩 테스트
    tests_total += 1
    if test_single_embedding():
        tests_passed += 1

    # 3. 미임베딩 뉴스 조회
    tests_total += 1
    if test_get_unembedded_news():
        tests_passed += 1

    # 4. 배치 임베딩 및 저장
    tests_total += 1
    if test_batch_embedding_and_save():
        tests_passed += 1

    # 5. Milvus 쿼리
    tests_total += 1
    if test_milvus_query():
        tests_passed += 1

    # 결과 출력
    logger.info("=" * 60)
    logger.info(f"✅ 테스트 결과: {tests_passed}/{tests_total}개 통과")
    logger.info("=" * 60)

    if tests_passed == tests_total:
        logger.info("🎉 모든 테스트 통과!")
        sys.exit(0)
    else:
        logger.error(f"❌ {tests_total - tests_passed}개 테스트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
