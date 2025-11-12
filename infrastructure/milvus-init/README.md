# Milvus Initialization

Milvus 벡터 데이터베이스 초기화 가이드입니다.

## 컬렉션 구조

현재 프로젝트에서 사용하는 Milvus 컬렉션:
- `news_embeddings` - 뉴스 기사 벡터 임베딩

## 초기화 방법

Milvus는 첫 실행시 백엔드 애플리케이션이 자동으로 컬렉션을 생성합니다.

```python
# backend/main.py에서 자동 초기화
# - 컬렉션 존재 확인
# - 없으면 자동 생성
# - 스키마 및 인덱스 설정
```

## 수동 초기화 (필요시)

백엔드가 자동으로 초기화하지 못하는 경우:

```bash
# 1. Python 환경에서
cd backend
uv run python -c "
from core.database import init_milvus
init_milvus()
"
```

## 데이터 마이그레이션

기존 Milvus 데이터를 옮기려면:

```bash
# 1. 기존 서버에서 컬렉션 내보내기
docker cp craveny-milvus:/var/lib/milvus ./milvus-backup

# 2. 새 서버로 복사
scp -r ./milvus-backup user@newserver:/path/to/craveny/infrastructure/

# 3. 새 서버에서 복원
docker cp ./milvus-backup craveny-milvus:/var/lib/milvus
docker restart craveny-milvus
```

## 주의사항

- Milvus 데이터는 용량이 클 수 있어 Git에 포함하지 않습니다
- 임베딩 데이터는 뉴스 크롤러 실행 후 다시 생성됩니다
- 컬렉션 스키마는 백엔드 코드로 관리됩니다
