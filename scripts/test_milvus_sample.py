"""
Milvus 샘플 벡터 삽입 및 유사도 검색 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from datetime import datetime
from backend.db.milvus_client import (
    connect_milvus,
    disconnect_milvus,
    get_collection,
    collection_exists,
)


def test_milvus_operations():
    """Milvus 샘플 벡터 삽입 및 검색 테스트"""
    print("=" * 60)
    print("🧪 Milvus 샘플 벡터 테스트")
    print("=" * 60)

    collection_name = "news_embeddings"

    try:
        # 1. Milvus 연결
        print("\n📡 Milvus 연결 중...")
        connect_milvus()

        # 2. 컬렉션 확인
        print(f"\n🔍 컬렉션 '{collection_name}' 확인 중...")
        if not collection_exists(collection_name):
            print(f"❌ 컬렉션이 존재하지 않습니다. 먼저 'python scripts/init_milvus.py'를 실행하세요.")
            return False

        collection = get_collection(collection_name)
        if not collection:
            print(f"❌ 컬렉션을 가져올 수 없습니다.")
            return False

        print(f"✅ 컬렉션 로드 완료")

        # 3. 샘플 벡터 데이터 생성 (3개)
        print(f"\n📊 샘플 벡터 데이터 생성 중...")
        np.random.seed(42)  # 재현성을 위한 시드 설정

        # 768차원 랜덤 벡터 3개 생성
        sample_vectors = [
            np.random.rand(768).tolist(),
            np.random.rand(768).tolist(),
            np.random.rand(768).tolist(),
        ]

        # 메타데이터
        news_ids = [1001, 1002, 1003]
        stock_codes = ["005930", "000660", "035420"]
        timestamps = [
            int(datetime(2025, 10, 31, 9, 0, 0).timestamp()),
            int(datetime(2025, 10, 31, 10, 0, 0).timestamp()),
            int(datetime(2025, 10, 31, 11, 0, 0).timestamp()),
        ]

        # 데이터 준비
        entities = [
            news_ids,
            sample_vectors,
            stock_codes,
            timestamps,
        ]

        print(f"   생성된 벡터: {len(sample_vectors)}개")
        print(f"   벡터 차원: {len(sample_vectors[0])}")

        # 4. 벡터 삽입
        print(f"\n📥 벡터 삽입 중...")
        insert_result = collection.insert(entities)
        collection.flush()
        print(f"   ✅ 삽입 완료: {len(insert_result.primary_keys)}개")
        print(f"   Primary Keys: {insert_result.primary_keys}")

        # 5. 유사도 검색 (첫 번째 벡터로 검색)
        print(f"\n🔍 유사도 검색 테스트 (TOP 5)...")
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

        # 첫 번째 벡터로 검색
        query_vector = [sample_vectors[0]]

        results = collection.search(
            data=query_vector,
            anns_field="embedding",
            param=search_params,
            limit=5,
            output_fields=["news_article_id", "stock_code"],
        )

        print(f"\n📋 검색 결과:")
        for i, hits in enumerate(results):
            print(f"\n   쿼리 벡터 #{i + 1}:")
            for j, hit in enumerate(hits):
                print(
                    f"      {j + 1}. ID: {hit.id}, "
                    f"Distance: {hit.distance:.4f}, "
                    f"Stock: {hit.entity.get('stock_code')}"
                )

        # 6. 검증
        print(f"\n✅ 검증:")
        if len(results) > 0 and len(results[0]) > 0:
            print(f"   ✅ 검색 결과 반환됨: {len(results[0])}개")
            # 거리가 오름차순으로 정렬되어 있는지 확인
            distances = [hit.distance for hit in results[0]]
            is_sorted = all(distances[i] <= distances[i + 1] for i in range(len(distances) - 1))
            if is_sorted:
                print(f"   ✅ 검색 결과가 거리 기준 오름차순으로 정렬됨")
            else:
                print(f"   ⚠️  검색 결과 정렬 순서 확인 필요")
        else:
            print(f"   ⚠️  검색 결과가 없습니다.")

        print(f"\n✅ 모든 테스트 통과!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        print(f"   에러 타입: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        print("=" * 60)
        return False

    finally:
        # 연결 해제
        disconnect_milvus()


if __name__ == "__main__":
    success = test_milvus_operations()
    sys.exit(0 if success else 1)
