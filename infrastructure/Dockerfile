# Python 3.11 베이스 이미지
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/

# 로그 디렉토리 생성
RUN mkdir -p /app/data/logs

# 포트 노출
EXPOSE 8000

# 기본 명령어 (docker-compose에서 오버라이드 가능)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
