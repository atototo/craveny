# Redis Initialization

Redis 캐시 데이터 초기화 가이드입니다.

## 백업 파일

- `dump.rdb` - Redis 스냅샷 (171B)

## 자동 초기화

docker-compose.yml에 설정된 볼륨 마운트로 자동 복원됩니다:

```yaml
volumes:
  - ./redis-init/dump.rdb:/data/dump.rdb
```

## 사용 용도

현재 Redis는 다음 용도로 사용됩니다:
- API 응답 캐시
- 세션 관리 (선택적)
- Rate limiting
- 임시 데이터 저장

## 초기 상태

현재 백업된 dump.rdb는 거의 비어있는 상태입니다 (171 bytes).
실제 운영 중에는 캐시 데이터가 자동으로 채워집니다.

## 수동 백업 (필요시)

```bash
# 1. Redis 스냅샷 생성
docker exec craveny-redis redis-cli SAVE

# 2. 덤프 파일 복사
docker cp craveny-redis:/data/dump.rdb ./infrastructure/redis-init/dump.rdb
```

## 캐시 초기화

새로 시작시 캐시를 비우고 싶다면:

```bash
docker exec craveny-redis redis-cli FLUSHALL
```
