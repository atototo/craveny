# Craveny

**증권 뉴스 기반 예측 및 텔레그램 알림 시스템**

Craveny는 국내 증권 뉴스를 자동으로 수집하고, OpenAI GPT-4o-mini를 활용하여 관련 종목의 단기 주가 방향성을 예측한 후, 텔레그램 봇을 통해 사용자에게 실시간 알림을 제공하는 시스템입니다.

## 🎯 주요 기능

- **뉴스 크롤링**: 네이버 금융 및 주요 증권 뉴스 자동 수집
- **AI 예측**: GPT-4o-mini를 활용한 뉴스 분석 및 주가 방향성 예측
- **RAG 기반 분석**: Milvus 벡터 DB를 활용한 유사 뉴스 검색 및 컨텍스트 강화
- **텔레그램 알림**: 관심 종목에 대한 실시간 예측 결과 푸시
- **스케줄링**: APScheduler를 통한 자동화된 주기적 실행

## 🏗️ 아키텍처

- **패턴**: Monolith (단일 FastAPI 애플리케이션)
- **배포**: AWS EC2 (t3.small) + Docker Compose
- **데이터베이스**: PostgreSQL (관계형 데이터) + Milvus (벡터 검색) + Redis (캐시/큐)
- **LLM**: OpenAI GPT-4o-mini (예측), text-embedding-3-small (임베딩)

자세한 아키텍처는 [docs/architecture.md](docs/architecture.md)를 참조하세요.

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | Python 3.11, FastAPI 0.104+ |
| **Database** | PostgreSQL 13+, Milvus 2.3+, Redis 7.0+ |
| **LLM** | OpenAI GPT-4o-mini, text-embedding-3-small |
| **Job Queue** | Celery 5.3+ |
| **Scheduler** | APScheduler 3.10+ |
| **Notification** | python-telegram-bot 20.7+ |
| **Containerization** | Docker 24+, Docker Compose 2.20+ |
| **Cloud** | AWS EC2 |

## 📋 사전 요구사항

- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Python**: 3.11+ (로컬 개발 시)
- **OpenAI API Key**: GPT-4o-mini 액세스 권한
- **Telegram Bot Token**: 텔레그램 봇 생성 필요

## 🚀 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/your-org/craveny.git
cd craveny
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 다음 값을 설정하세요:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Telegram
TELEGRAM_BOT_TOKEN=your-bot-token-here

# PostgreSQL (기본값 사용 가능)
POSTGRES_PASSWORD=your_secure_password
```

### 3. 인프라 서비스 시작 (Docker Compose)

```bash
cd infrastructure
docker-compose up -d
```

다음 서비스가 시작됩니다:
- PostgreSQL (포트 5432)
- Redis (포트 6379)
- Milvus (포트 19530)
- etcd, MinIO (Milvus 의존성)

### 4. Python 가상 환경 설정 (로컬 개발)

```bash
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 개발 도구
```

### 5. 데이터베이스 초기화

```bash
# PostgreSQL 테이블 생성
python scripts/init_db.py

# Milvus 컬렉션 생성
python scripts/init_milvus.py
```

### 6. FastAPI 서버 실행

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 실행되면 다음 URL에서 접근 가능합니다:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- 헬스체크: http://localhost:8000/health

## 🧪 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=backend --cov-report=html

# 특정 테스트만 실행
pytest tests/unit/test_crawler.py
```

## 📝 코드 품질 도구

```bash
# 코드 포맷팅 (Black)
black backend/ tests/

# Import 정렬 (isort)
isort backend/ tests/

# Linting (Flake8)
flake8 backend/ tests/

# 타입 체크 (mypy)
mypy backend/
```

## 📁 프로젝트 구조

```
craveny/
├── backend/              # FastAPI 애플리케이션
│   ├── main.py          # 진입점
│   ├── config.py        # 설정 관리
│   ├── crawlers/        # 뉴스 크롤러
│   ├── llm/             # LLM 예측 엔진
│   ├── telegram/        # 텔레그램 봇
│   ├── db/              # 데이터베이스 모델 및 리포지토리
│   ├── scheduler/       # APScheduler 작업
│   └── api/             # REST API 엔드포인트
├── data/                # 로컬 데이터 저장소
├── docs/                # 문서
├── infrastructure/      # Docker 설정
├── scripts/             # 유틸리티 스크립트
├── tests/               # 테스트 코드
├── requirements.txt     # Python 의존성
└── .env.example         # 환경 변수 템플릿
```

## 🔧 개발 워크플로우

1. **기능 브랜치 생성**: `git checkout -b feature/new-feature`
2. **코드 작성 및 테스트**: 테스트 커버리지 70% 이상 유지
3. **코드 품질 검사**: Black, Flake8, mypy 통과
4. **커밋**: 명확한 커밋 메시지 작성
5. **Pull Request**: `main` 브랜치로 PR 생성

## 📚 문서

- [PRD (Product Requirements Document)](docs/prd.md)
- [아키텍처 문서](docs/architecture.md)

## 📄 라이선스

MIT License

## 👥 기여자

- 프로젝트 관리자: [Your Name]

## 📞 문의

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.
