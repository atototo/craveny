# Database Initialization

다른 PC에서 프로젝트를 실행하기 위한 데이터베이스 초기화 가이드입니다.

## 파일 설명

- `01-schema.sql` - PostgreSQL 테이블 스키마 (75KB)
- `02-data.sql` - 초기 데이터 (사용자, 설정 등, 대용량 테이블 제외)

## 초기화 방법

### 방법 1: Docker Compose 자동 초기화 (권장)

Docker Compose가 자동으로 이 디렉토리의 SQL 파일들을 실행합니다.

```bash
# 1. 프로젝트 루트에서
cd /path/to/craveny

# 2. Docker 컨테이너 시작 (최초 실행시 자동으로 DB 초기화)
docker-compose -f infrastructure/docker-compose.yml up -d postgres

# 3. DB 초기화 완료 확인
docker-compose -f infrastructure/docker-compose.yml logs postgres
```

### 방법 2: 수동 복원

이미 실행 중인 PostgreSQL에 수동으로 복원:

```bash
# 1. 스키마 복원
docker exec -i craveny-postgres psql -U postgres -d craveny < infrastructure/db-init/01-schema.sql

# 2. 데이터 복원
docker exec -i craveny-postgres psql -U postgres -d craveny < infrastructure/db-init/02-data.sql
```

## 주의사항

- `news`, `stock_prices`, `predictions` 테이블의 데이터는 용량 문제로 제외되었습니다
- 이 테이블들은 백엔드 실행 후 크롤러를 통해 다시 수집됩니다
- 사용자 계정 정보는 포함되어 있습니다 (테스트 계정 사용 가능)

## 테스트 계정

초기 데이터에 포함된 테스트 계정:
- Username: `test_user`
- Password: `test1234`

## 문제 해결

### DB 초기화가 안되는 경우

```bash
# 1. 기존 볼륨 삭제
docker-compose -f infrastructure/docker-compose.yml down -v

# 2. 다시 시작
docker-compose -f infrastructure/docker-compose.yml up -d postgres
```

### 특정 테이블만 복원하고 싶은 경우

```bash
# 예: users 테이블만 복원
docker exec -i craveny-postgres psql -U postgres -d craveny -c "\\copy users FROM STDIN WITH CSV" < users.csv
```
