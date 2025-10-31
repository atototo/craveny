"""
Milvus vector database connection and utility functions.
"""
from typing import Optional
from pymilvus import connections, Collection, utility
from backend.config import settings


def connect_milvus(alias: str = "default") -> None:
    """
    Connect to Milvus server.

    Args:
        alias: Connection alias name (default: "default")

    Raises:
        ConnectionError: If connection to Milvus fails
    """
    try:
        connections.connect(
            alias=alias,
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        print(f"✅ Milvus 연결 성공: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
    except Exception as e:
        print(f"❌ Milvus 연결 실패: {e}")
        raise ConnectionError(f"Failed to connect to Milvus: {e}")


def disconnect_milvus(alias: str = "default") -> None:
    """
    Disconnect from Milvus server.

    Args:
        alias: Connection alias name (default: "default")
    """
    try:
        connections.disconnect(alias=alias)
        print(f"✅ Milvus 연결 해제 완료")
    except Exception as e:
        print(f"⚠️  Milvus 연결 해제 중 경고: {e}")


def get_collection(collection_name: str, alias: str = "default") -> Optional[Collection]:
    """
    Get a Milvus collection object.

    Args:
        collection_name: Name of the collection
        alias: Connection alias name (default: "default")

    Returns:
        Collection object if exists, None otherwise

    Raises:
        Exception: If collection doesn't exist or connection error
    """
    try:
        if utility.has_collection(collection_name, using=alias):
            collection = Collection(name=collection_name, using=alias)
            return collection
        else:
            print(f"⚠️  컬렉션 '{collection_name}'이 존재하지 않습니다.")
            return None
    except Exception as e:
        print(f"❌ 컬렉션 조회 실패: {e}")
        raise


def collection_exists(collection_name: str, alias: str = "default") -> bool:
    """
    Check if a collection exists in Milvus.

    Args:
        collection_name: Name of the collection
        alias: Connection alias name (default: "default")

    Returns:
        True if collection exists, False otherwise
    """
    try:
        return utility.has_collection(collection_name, using=alias)
    except Exception as e:
        print(f"❌ 컬렉션 존재 확인 실패: {e}")
        return False


def drop_collection(collection_name: str, alias: str = "default") -> bool:
    """
    Drop a collection from Milvus.

    Args:
        collection_name: Name of the collection to drop
        alias: Connection alias name (default: "default")

    Returns:
        True if dropped successfully, False otherwise
    """
    try:
        if utility.has_collection(collection_name, using=alias):
            utility.drop_collection(collection_name, using=alias)
            print(f"✅ 컬렉션 '{collection_name}' 삭제 완료")
            return True
        else:
            print(f"⚠️  컬렉션 '{collection_name}'이 존재하지 않습니다.")
            return False
    except Exception as e:
        print(f"❌ 컬렉션 삭제 실패: {e}")
        return False
