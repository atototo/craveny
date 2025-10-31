"""
Milvus 벡터 데이터베이스 초기화 스크립트
컬렉션 생성 및 인덱스 설정
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)
from backend.config import settings

# 컬렉션 설정
COLLECTION_NAME = "news_embeddings"
EMBEDDING_DIM = 768  # text-embedding-3-small 차원


def init_milvus():
    """Milvus 데이터베이스 초기화 함수"""
    print("=" * 60)
    print("🔍 Milvus 벡터 데이터베이스 초기화 시작")
    print("=" * 60)

    try:
        # Milvus 연결
        print(f"\n📡 Milvus 연결 중...")
        print(f"   호스트: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        print(f"   ✅ 연결 성공")

        # 기존 컬렉션 확인 및 삭제
        if utility.has_collection(COLLECTION_NAME):
            print(f"\n⚠️  기존 컬렉션 '{COLLECTION_NAME}' 발견")
            print(f"   🗑️  기존 컬렉션 삭제 중...")
            utility.drop_collection(COLLECTION_NAME)
            print(f"   ✅ 삭제 완료")

        # 필드 스키마 정의
        print(f"\n📋 컬렉션 스키마 정의 중...")
        fields = [
            FieldSchema(
                name="news_article_id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=False,
                description="뉴스 기사 ID (PostgreSQL foreign key)",
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=EMBEDDING_DIM,
                description="뉴스 임베딩 벡터 (768-dim)",
            ),
            FieldSchema(
                name="stock_code",
                dtype=DataType.VARCHAR,
                max_length=10,
                description="종목 코드 (필터링용)",
            ),
            FieldSchema(
                name="published_timestamp",
                dtype=DataType.INT64,
                description="발행 시간 (Unix timestamp, 필터링용)",
            ),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="뉴스 기사 임베딩 컬렉션 (RAG용)",
        )

        # 컬렉션 생성
        print(f"\n🏗️  컬렉션 '{COLLECTION_NAME}' 생성 중...")
        collection = Collection(name=COLLECTION_NAME, schema=schema)
        print(f"   ✅ 컬렉션 생성 완료")

        # 인덱스 생성
        print(f"\n🔧 인덱스 생성 중...")
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 128},
        }

        collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )
        print(f"   ✅ 인덱스 생성 완료 (IVF_FLAT, L2)")

        # 컬렉션 로드
        print(f"\n⚡ 컬렉션 메모리 로드 중...")
        collection.load()
        print(f"   ✅ 로드 완료")

        # 정보 출력
        print(f"\n📊 컬렉션 정보:")
        print(f"   이름: {collection.name}")
        print(f"   스키마: {collection.schema}")
        print(f"   엔티티 수: {collection.num_entities}")

        print(f"\n✅ Milvus 초기화 완료!")
        print("=" * 60)

        # 연결 해제
        connections.disconnect("default")
        return True

    except Exception as e:
        print(f"\n❌ Milvus 초기화 실패: {e}")
        print("=" * 60)
        try:
            connections.disconnect("default")
        except:
            pass
        return False


if __name__ == "__main__":
    success = init_milvus()
    sys.exit(0 if success else 1)
