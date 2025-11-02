# Craveny Fullstack Architecture Document

**버전:** 2.0
**날짜:** 2025-11-02
**상태:** Phase 2 완료 (Epic 1 & Epic 2)

---

## 목차

1. [소개](#1-소개)
2. [고수준 아키텍처](#2-고수준-아키텍처)
3. [기술 스택](#3-기술-스택)
4. [데이터 모델](#4-데이터-모델)
5. [API 명세](#5-api-명세)
6. [컴포넌트](#6-컴포넌트)
7. [데이터베이스 스키마](#7-데이터베이스-스키마)
8. [통합 프로젝트 구조](#8-통합-프로젝트-구조)
9. [코딩 표준](#9-코딩-표준)
10. [개발 워크플로우](#10-개발-워크플로우)
11. [배포 아키텍처](#11-배포-아키텍처)
12. [보안 및 성능](#12-보안-및-성능)
13. [테스팅 전략](#13-테스팅-전략)
14. [에러 핸들링 전략](#14-에러-핸들링-전략)
15. [모니터링 및 관찰성](#15-모니터링-및-관찰성)

---

## 1. 소개

### 1.1 개요

이 문서는 **Craveny**의 전체 풀스택 아키텍처를 정의합니다. 백엔드 시스템, 프론트엔드 구현(텔레그램 봇 인터페이스), 그리고 이들의 통합 방식을 포함합니다. AI 기반 개발의 단일 진실 공급원(Single Source of Truth)으로 기능하며, 전체 기술 스택의 일관성을 보장합니다.

이 통합 접근 방식은 백엔드 데이터 처리, LLM 기반 예측, 텔레그램 알림 전송이 긴밀하게 통합된 현대적 풀스택 애플리케이션의 개발 프로세스를 간소화합니다.

### 1.2 스타터 템플릿 또는 기존 프로젝트

**상태:** N/A - 완전 신규 프로젝트 (Greenfield)

**분석:**
- PRD에 기존 스타터 템플릿이나 코드베이스 언급 없음
- 맞춤형 요구사항으로 처음부터 구축
- 기술 스택 선택은 PRD Technical Assumptions에 명시되어 있음
- 프레임워크별 스타터 불필요 (FastAPI + 텔레그램 봇은 직관적)

**결정:** 다음 방식으로 신규 개발 진행:
- 표준 FastAPI 프로젝트 구조
- Docker Compose로 인프라 오케스트레이션
- Python 모범 사례 (Black, Flake8, pytest)

### 1.3 변경 이력

| 날짜 | 버전 | 설명 | 작성자 |
|------|------|------|--------|
| 2025-10-31 | 1.0 | PRD v1.1 기반 초기 아키텍처 문서 생성 | Winston (Architect) |
| 2025-11-02 | 2.0 | Epic 1 & Epic 2 Phase 2 완료 반영: Next.js Frontend, API 확장, LLM 예측, 텔레그램 알림 | Winston (Architect) |

---

## 2. 고수준 아키텍처

### 2.1 기술 요약

Craveny는 **Full-Stack Monolith 아키텍처**로 구성됩니다. Next.js 웹 대시보드, FastAPI 백엔드, 텔레그램 봇이 통합된 시스템에서 뉴스/주가 데이터 수집, LLM 기반 예측, 다채널 알림 전송을 처리합니다.

**핵심 구성:**
- **프론트엔드:** Next.js 15 (App Router) - 사용자/관리자 대시보드, 종목 분석 페이지
- **백엔드:** Python 3.11+ FastAPI - RESTful API, 비동기 작업 처리, LLM 예측
- **데이터 파이프라인:** APScheduler (주기적 크롤링), Celery (비동기 LLM 분석)
- **알림 채널:** 텔레그램 봇 (python-telegram-bot), 웹 대시보드 (실시간 업데이트)
- **AI/ML:** OpenAI GPT-4o (예측 생성), text-embedding-3-small (768차원 벡터)
- **데이터 저장:** PostgreSQL (관계형 데이터), Milvus (벡터 검색), Redis (캐싱/큐)
- **배포:** Docker Compose로 모든 서비스 오케스트레이션, AWS EC2 단일 인스턴스 배포

이 아키텍처는 Epic 1 (데이터 인프라) 및 Epic 2 Phase 2 (LLM 예측 & 알림)를 완료하였으며, 웹 UI를 통한 사용자 경험 개선과 관리자 모니터링 기능을 제공합니다.

### 2.2 플랫폼 및 인프라 선택

**최종 선택:**

**플랫폼:** AWS EC2 (t3.small, 2 vCPU, 2GB RAM)
**핵심 서비스:**
- **컴퓨팅:** EC2 단일 인스턴스 (모든 서비스 Docker Compose로 실행)
- **데이터베이스:** PostgreSQL 13+ (Docker 컨테이너)
- **벡터 DB:** Milvus 2.x (etcd, MinIO 포함 Docker 구성)
- **캐시/큐:** Redis 7+ (Docker 컨테이너)
- **백업:** AWS S3 (PostgreSQL/Milvus 일일/주간 백업)

**배포 호스트 및 리전:**
- **리전:** ap-northeast-2 (서울) - 한국 증시 데이터 수집 및 사용자 위치 최적화
- **가용 영역:** Single AZ (MVP, 고가용성 불필요)

**선택 근거:**
- ✅ **비용 통제:** EC2 t3.small ~$15/월, S3 백업 ~$5/월 → 총 $50/월 이내
- ✅ **Milvus 완전 제어:** Docker로 로컬 운영, 벡터 수 무제한
- ✅ **단순성:** 단일 인스턴스 관리, docker-compose up 배포
- ✅ **확장성:** Phase 2에서 AWS RDS, ElastiCache, ECS 전환 가능

### 2.3 레포지토리 구조

**구조:** Monorepo
**Monorepo 도구:** 없음 (단순 Python 프로젝트, 복잡도 낮음)
**패키지 구성 전략:**

```
단일 레포지토리 내 논리적 모듈 분리:
- backend/ (FastAPI 앱, 크롤러, LLM, 텔레그램 봇)
- data/ (수집된 원본 데이터, 로그)
- scripts/ (초기 데이터 수집, DB 마이그레이션)
- tests/ (Unit, Integration 테스트)
- docs/ (PRD, 아키텍처 문서)
```

**근거:**
- MVP 규모에서 Nx/Turborepo 같은 Monorepo 도구는 과도한 복잡도
- Python 프로젝트는 모듈 시스템으로 충분히 구조화 가능
- 단일 팀 개발, 코드 공유 용이, CI/CD 단순화

### 2.4 고수준 아키텍처 다이어그램

```mermaid
graph TB
    subgraph "사용자"
        WEB_USER[웹 사용자<br/>대시보드 접속]
        TEL_USER[텔레그램 사용자<br/>알림 구독]
    end

    subgraph "외부 데이터 소스"
        NEWS[뉴스 사이트<br/>네이버/한경/매경]
        STOCK[주가 데이터<br/>FinanceDataReader]
    end

    subgraph "AWS EC2 t3.small - Docker Compose"
        subgraph "프론트엔드"
            NEXTJS[Next.js 15<br/>포트 3000<br/>App Router]
        end

        subgraph "FastAPI 애플리케이션"
            API[FastAPI Server<br/>포트 8000<br/>REST API]
            CRAWLER[크롤러<br/>APScheduler]
            CELERY[Celery Worker<br/>비동기 LLM 분석]
            BOT[텔레그램 봇<br/>python-telegram-bot]
        end

        subgraph "데이터 레이어"
            PG[(PostgreSQL<br/>뉴스/주가/예측)]
            MILVUS[(Milvus<br/>벡터 검색)]
            REDIS[(Redis<br/>캐싱/큐)]
            ETCD[etcd]
            MINIO[MinIO]
        end
    end

    subgraph "외부 AI 서비스"
        OPENAI[OpenAI API<br/>GPT-4o<br/>text-embedding-3-small]
    end

    subgraph "백업 스토리지"
        S3[AWS S3<br/>일일/주간 백업]
    end

    WEB_USER -->|대시보드 접속| NEXTJS
    NEXTJS -->|API 프록시| API
    API -->|데이터 제공| NEXTJS

    TEL_USER -->|/start, /stop| BOT
    BOT -->|알림 전송| TEL_USER

    CRAWLER -->|10분 주기| NEWS
    CRAWLER -->|1분 주기| STOCK
    CRAWLER -->|저장| PG

    API -->|REST API| PG
    API -->|벡터 검색| MILVUS
    API -->|캐싱| REDIS

    CELERY -->|새 뉴스 감지| PG
    CELERY -->|임베딩| OPENAI
    CELERY -->|벡터 저장| MILVUS
    CELERY -->|유사도 검색| MILVUS
    CELERY -->|LLM 예측| OPENAI
    CELERY -->|예측 저장| PG
    CELERY -->|알림 트리거| BOT
    CELERY -->|작업 큐| REDIS

    MILVUS -->|의존성| ETCD
    MILVUS -->|스토리지| MINIO

    PG -.->|일일 백업| S3
    MILVUS -.->|주간 백업| S3

    style WEB_USER fill:#e1f5ff
    style TEL_USER fill:#e1f5ff
    style NEXTJS fill:#d4f1f4
    style OPENAI fill:#fff4e1
    style S3 fill:#f0f0f0
```

### 2.5 아키텍처 패턴

**적용된 패턴 및 근거:**

- **Monolith Architecture:** 단일 FastAPI 애플리케이션 - _근거: 2주 MVP, <100 사용자 규모에 최적, 빠른 개발 및 배포_

- **Background Job Processing (Celery):** 비동기 작업 큐 패턴 - _근거: 뉴스 크롤링, LLM 분석, 알림 전송을 메인 요청 흐름과 분리하여 성능 최적화_

- **RAG (Retrieval-Augmented Generation):** 벡터 검색 + LLM 생성 - _근거: 과거 유사 뉴스 패턴을 활용하여 예측 정확도 향상, LLM 환각(hallucination) 감소_

- **Repository Pattern:** 데이터 접근 추상화 - _근거: PostgreSQL/Milvus 접근 로직 캡슐화, 테스트 용이성, 향후 DB 마이그레이션 유연성_

- **Scheduled Task Pattern (APScheduler):** 주기적 작업 실행 - _근거: 뉴스 크롤링(10분), 주가 수집(1분), 매칭 계산(일일)을 안정적으로 자동화_

- **Event-Driven Notification:** 이벤트 기반 알림 트리거 - _근거: 새 뉴스 발생 → 예측 → 필터링 → 알림 파이프라인을 느슨하게 결합_

- **Microservices-Ready Modular Design:** 모듈화된 코드 구조 - _근거: Phase 2 마이크로서비스 전환 대비, 크롤러/LLM/봇을 독립 모듈로 설계_

---

## 3. 기술 스택

### 3.1 기술 스택 테이블

이 테이블은 프로젝트의 **단일 진실 공급원(Single Source of Truth)**입니다. 모든 개발은 아래 명시된 정확한 버전을 사용해야 합니다.

| 카테고리 | 기술 | 버전 | 목적 | 선택 근거 |
|---------|------|------|------|-----------|
| **프론트엔드 프레임워크** | Next.js | 15.1.4 | 웹 대시보드, 사용자/관리자 UI | React SSR, App Router, 빠른 개발, API 프록시 내장 |
| **프론트엔드 언어** | TypeScript | 5.x | 타입 안전 프론트엔드 개발 | 타입 안정성, IDE 지원, 런타임 오류 방지 |
| **UI 라이브러리** | React | 19.x | 컴포넌트 기반 UI 구축 | Next.js 기본, 풍부한 생태계, 팀 경험 |
| **CSS 프레임워크** | Tailwind CSS | 3.x | 유틸리티 퍼스트 스타일링 | 빠른 개발, 일관된 디자인, Next.js 통합 |
| **백엔드 언어** | Python | 3.11+ | 백엔드 개발, 데이터 처리, ML 통합 | 데이터/ML/API에 최적, 풍부한 라이브러리 생태계, 팀 숙련도 |
| **백엔드 프레임워크** | FastAPI | 0.104+ | RESTful API, 비동기 처리, 헬스체크 엔드포인트 | 비동기 우수, 자동 문서화, 타입 힌트 지원, 빠른 개발 속도 |
| **API 스타일** | REST | - | 헬스체크/메트릭 조회 API | 단순 CRUD 충분, 텔레그램 봇이 주 인터페이스 |
| **스케줄러** | APScheduler | 3.10+ | 주기적 크롤링 (뉴스 10분, 주가 1분) | 간단한 스케줄링에 충분, FastAPI 통합 용이 |
| **비동기 작업 큐** | Celery | 5.3+ | LLM 예측, 임베딩, 알림 전송 비동기 처리 | 표준 Python 비동기 작업, 재시도/모니터링 기능 |
| **메시지 브로커/캐시** | Redis | 7.0+ | Celery 메시지 브로커, 중복 방지 캐시 | 빠른 인메모리 저장소, Celery 표준 백엔드 |
| **관계형 데이터베이스** | PostgreSQL | 13+ | 뉴스, 주가, 매칭 결과, 사용자 데이터 | 안정적, ACID 보장, 한국어 지원, JSON 컬럼 지원 |
| **벡터 데이터베이스** | Milvus | 2.3+ | 뉴스 임베딩 저장 및 유사도 검색 | 무료, 무제한, 데이터 주권, L2/IP 거리 지원 |
| **벡터 DB 의존성** | etcd | 3.5+ | Milvus 메타데이터 저장 | Milvus 필수 의존성 |
| **벡터 DB 스토리지** | MinIO | Latest | Milvus 데이터 영구 저장 | Milvus 필수 의존성, S3 호환 |
| **LLM** | OpenAI GPT-4o-mini | Latest API | 뉴스 영향도 예측, 전략 메시지 생성 | 비용 대비 성능 우수 ($0.01~0.02/건), 안정적 API, 한국어 지원 |
| **임베딩 모델** | OpenAI text-embedding-3-small | Latest API | 뉴스 텍스트 → 768차원 벡터 변환 | 비용 효율적 ($0.0001/건), 한국어 성능 우수, Milvus 호환 |
| **크롤링 라이브러리** | BeautifulSoup4 | 4.12+ | HTML 파싱, 뉴스 크롤링 | 간단하고 충분, 학습 곡선 낮음 |
| **주가 데이터** | FinanceDataReader | 0.9+ | 한국 증시 주가 수집 | 한국 시장 특화, 무료, KRX 데이터 지원 |
| **텔레그램 봇** | python-telegram-bot | 20.7+ | 텔레그램 봇 구현 및 알림 전송 | 텔레그램 봇 API 표준, 비동기 지원, 풍부한 문서 |
| **컨테이너화** | Docker | 24+ | 모든 서비스 컨테이너화 | 환경 일관성, 로컬/프로덕션 동일 실행 |
| **오케스트레이션** | Docker Compose | 2.20+ | 멀티 컨테이너 관리 (6개 서비스) | 단순 배포, docker-compose up으로 즉시 실행 |
| **백엔드 테스팅** | pytest | 7.4+ | Unit, Integration 테스트 | Python 표준, 픽스처 지원, 플러그인 풍부 |
| **비동기 테스팅** | pytest-asyncio | 0.21+ | FastAPI 비동기 함수 테스트 | pytest와 통합, 비동기 테스트 필수 |
| **코드 포맷터** | Black | 23.0+ | 일관된 코드 스타일 | Python 표준, 설정 불필요, CI 통합 용이 |
| **린터** | Flake8 | 6.0+ | 코드 품질 검사 | PEP8 준수, 정적 분석, Black과 호환 |
| **타입 체커** | mypy | 1.5+ | 타입 힌트 검증 | FastAPI 타입 안정성, 런타임 오류 사전 발견 |
| **버전 관리** | Git | 2.40+ | 소스 코드 관리 | 표준 버전 관리 시스템 |
| **원격 레포지토리** | GitHub | - | 코드 호스팅, 협업, CI/CD | 무료, Actions 통합, 풍부한 생태계 |
| **CI/CD** | GitHub Actions | - | 자동 테스트, 수동 배포 | 무료, GitHub 통합, 간단한 YAML 설정 |
| **클라우드 플랫폼** | AWS EC2 | t3.small | 서버 호스팅 | 비용 예측 가능 (~$15/월), 완전한 제어 |
| **백업 스토리지** | AWS S3 | - | PostgreSQL/Milvus 백업 보관 | 저렴한 스토리지 (~$5/월), 7일/4주 보관 |
| **모니터링** | Python logging | Built-in | 파일 로그 기록 | MVP는 간단한 로깅으로 충분, Phase 2 CloudWatch |
| **환경 변수 관리** | python-dotenv | 1.0+ | .env 파일 로드 | 민감 정보 분리, Git 커밋 방지 |

---

## 4. 데이터 모델

이 섹션은 프론트엔드(텔레그램 봇)와 백엔드 간 공유되는 핵심 비즈니스 엔티티를 정의합니다. Python 프로젝트이므로 **Pydantic 모델**을 사용하여 타입 안전성과 FastAPI 통합을 제공합니다.

### 4.1 News (뉴스)

**목적:** 크롤링한 증권 뉴스 원본 데이터 저장

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `title`: str - 뉴스 제목 (최대 500자)
- `content`: str - 뉴스 본문 전체 텍스트
- `published_at`: datetime - 뉴스 발표 시간 (KST)
- `source`: str - 언론사 (예: "네이버", "한국경제", "매일경제")
- `stock_code`: str - 관련 종목코드 (예: "005930" = 삼성전자)
- `created_at`: datetime - DB 저장 시간

**Pydantic 모델:**

```python
from datetime import datetime
from pydantic import BaseModel, Field

class News(BaseModel):
    id: int
    title: str = Field(..., max_length=500)
    content: str
    published_at: datetime
    source: str = Field(..., max_length=100)
    stock_code: str = Field(..., max_length=10)
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True  # SQLAlchemy ORM 호환
```

**관계:**
- `NewsStockMatch` (1:N): 하나의 뉴스는 여러 시점의 주가 변동률 매칭을 가질 수 있음
- `NewsEmbedding` (1:1): 각 뉴스는 하나의 벡터 임베딩을 가짐

### 4.2 StockPrice (주가)

**목적:** 1분 단위 주가 데이터 저장 (OHLCV)

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `stock_code`: str - 종목코드 (예: "005930")
- `date`: datetime - 주가 시점 (1분봉)
- `open`: float - 시가
- `high`: float - 고가
- `low`: float - 저가
- `close`: float - 종가
- `volume`: int - 거래량

**Pydantic 모델:**

```python
from datetime import datetime
from pydantic import BaseModel, Field

class StockPrice(BaseModel):
    id: int
    stock_code: str = Field(..., max_length=10)
    date: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)

    class Config:
        from_attributes = True
```

### 4.3 NewsStockMatch (뉴스-주가 매칭)

**목적:** 뉴스 발표 후 1일/3일/5일 주가 변동률 저장 (RAG 학습 데이터)

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `news_id`: int - 뉴스 ID (Foreign Key → News.id)
- `stock_code`: str - 종목코드
- `price_change_1d`: float - 1일 후 변동률 (%)
- `price_change_3d`: float - 3일 후 변동률 (%)
- `price_change_5d`: float - 5일 후 변동률 (%)
- `calculated_at`: datetime - 계산 완료 시간

**Pydantic 모델:**

```python
from datetime import datetime
from pydantic import BaseModel, Field

class NewsStockMatch(BaseModel):
    id: int
    news_id: int
    stock_code: str = Field(..., max_length=10)
    price_change_1d: float | None = None  # 1일 미경과 시 None
    price_change_3d: float | None = None
    price_change_5d: float | None = None
    calculated_at: datetime

    class Config:
        from_attributes = True
```

### 4.4 TelegramUser (텔레그램 사용자)

**목적:** 텔레그램 봇 구독자 관리

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `user_id`: int - 텔레그램 사용자 ID (Unique)
- `subscribed_at`: datetime - 구독 시작 시간
- `is_active`: bool - 활성 상태 (/stop 시 False)

**Pydantic 모델:**

```python
from datetime import datetime
from pydantic import BaseModel, Field

class TelegramUser(BaseModel):
    id: int
    user_id: int = Field(..., description="Telegram user ID")
    subscribed_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True
```

### 4.5 NewsEmbedding (뉴스 임베딩 - Milvus)

**목적:** Milvus 벡터 DB에 저장되는 뉴스 임베딩 (RAG 검색용)

**주요 속성:**
- `id`: int - Milvus 자동 생성 ID (Auto ID)
- `news_id`: int - PostgreSQL News.id 참조
- `embedding`: List[float] - 768차원 벡터 (OpenAI text-embedding-3-small)
- `stock_code`: str - 종목코드 (필터링용)
- `price_change_1d`: float - 1일 후 변동률 (메타데이터)
- `price_change_3d`: float - 3일 후 변동률
- `price_change_5d`: float - 5일 후 변동률

**Pydantic 모델:**

```python
from pydantic import BaseModel, Field

class NewsEmbedding(BaseModel):
    id: int | None = None  # Milvus 자동 생성
    news_id: int
    embedding: list[float] = Field(..., min_length=768, max_length=768)
    stock_code: str = Field(..., max_length=10)
    price_change_1d: float | None = None
    price_change_3d: float | None = None
    price_change_5d: float | None = None
```

### 4.6 Prediction (예측 결과 - 비즈니스 로직)

**목적:** LLM 예측 결과를 담는 DTO (Data Transfer Object, DB 저장 안 함)

**주요 속성:**
- `news_id`: int - 예측 대상 뉴스 ID
- `stock_code`: str - 종목코드
- `direction`: str - 방향 ("UP" | "DOWN" | "NEUTRAL")
- `probability`: float - 상승/하락 확률 (0~100)
- `impact_score`: float - 영향도 점수 (0~10)
- `expected_change`: float - 예상 변동폭 (%)
- `duration_days`: int - 영향 지속 기간 (일)
- `reasoning`: str - 예측 근거 (LLM 생성 텍스트)
- `similar_news`: List[int] - 유사 뉴스 ID 목록 (TOP 5)

**Pydantic 모델:**

```python
from pydantic import BaseModel, Field
from typing import Literal

class Prediction(BaseModel):
    news_id: int
    stock_code: str = Field(..., max_length=10)
    direction: Literal["UP", "DOWN", "NEUTRAL"]
    probability: float = Field(..., ge=0, le=100)
    impact_score: float = Field(..., ge=0, le=10)
    expected_change: float  # 예: +7.2 또는 -3.5
    duration_days: int = Field(..., ge=1, le=30)
    reasoning: str = Field(..., max_length=2000)
    similar_news: list[int] = Field(default_factory=list, max_length=5)
```

### 4.7 Prediction (예측 결과 저장 - PostgreSQL)

**목적:** LLM 예측 결과를 PostgreSQL에 영구 저장 (분석 이력, API 조회)

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `news_id`: int - 뉴스 ID (Foreign Key → News.id)
- `stock_code`: str - 종목코드 (인덱스)
- `direction`: str - 예측 방향 ("up", "down", "hold")
- `confidence`: float - 예측 신뢰도 (0.0 ~ 1.0)
- `reasoning`: str - 예측 근거 (Text)
- `current_price`: float - 예측 시점 현재가
- `target_period`: str - 예측 기간 (예: "1일", "1주일")
- `created_at`: datetime - 예측 생성 시간
- `short_term`: str - T+1일 예측 (Text)
- `medium_term`: str - T+3일 예측 (Text)
- `long_term`: str - T+5일 예측 (Text)
- `confidence_breakdown`: dict - 신뢰도 구성 요소 (JSON)
- `pattern_analysis`: dict - 패턴 분석 통계 (JSON)

**SQLAlchemy 모델:**

```python
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, JSON
from datetime import datetime
from backend.db.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    news_id = Column(Integer, ForeignKey("news_articles.id"), nullable=False)
    stock_code = Column(String(10), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # up, down, hold
    confidence = Column(Float, nullable=False)  # 0.0 ~ 1.0
    reasoning = Column(Text, nullable=True)
    current_price = Column(Float, nullable=True)
    target_period = Column(String(20), default="1일", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 기간별 예측
    short_term = Column(Text, nullable=True)
    medium_term = Column(Text, nullable=True)
    long_term = Column(Text, nullable=True)

    # 신뢰도 & 패턴 분석
    confidence_breakdown = Column(JSON, nullable=True)
    pattern_analysis = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_predictions_stock_code_created", "stock_code", "created_at"),
        Index("idx_predictions_news_id", "news_id"),
    )
```

**관계:**
- `News` (N:1): 하나의 뉴스는 여러 예측을 생성할 수 있음 (시점별)
- `API 조회`: `/api/predictions?stock_code=005930` 형태로 조회 가능

### 4.8 StockAnalysisSummary (종목 분석 요약 - PostgreSQL)

**목적:** 종목별 AI 투자 분석 리포트 캐시 (LLM 생성 콘텐츠 + 통계)

**주요 속성:**
- `id`: int - 고유 식별자 (Primary Key)
- `stock_code`: str - 종목코드 (Unique, 인덱스)
- `overall_summary`: str - 종합 의견 (Text)
- `short_term_scenario`: str - 단기 투자 시나리오 (Text)
- `medium_term_scenario`: str - 중기 투자 시나리오 (Text)
- `long_term_scenario`: str - 장기 투자 시나리오 (Text)
- `risk_factors`: list[str] - 리스크 요인 리스트 (JSON)
- `opportunity_factors`: list[str] - 기회 요인 리스트 (JSON)
- `recommendation`: str - 최종 추천 (Text)
- `total_predictions`: int - 총 예측 건수
- `up_count`: int - 상승 예측 건수
- `down_count`: int - 하락 예측 건수
- `hold_count`: int - 보합 예측 건수
- `avg_confidence`: float - 평균 신뢰도
- `last_updated`: datetime - 마지막 업데이트 시각
- `based_on_prediction_count`: int - 분석에 사용된 예측 건수

**SQLAlchemy 모델:**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from datetime import datetime
from backend.db.base import Base

class StockAnalysisSummary(Base):
    __tablename__ = "stock_analysis_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(10), unique=True, nullable=False, index=True)

    # LLM 생성 콘텐츠
    overall_summary = Column(Text, nullable=True)
    short_term_scenario = Column(Text, nullable=True)
    medium_term_scenario = Column(Text, nullable=True)
    long_term_scenario = Column(Text, nullable=True)
    risk_factors = Column(JSON, nullable=True)
    opportunity_factors = Column(JSON, nullable=True)
    recommendation = Column(Text, nullable=True)

    # 통계 데이터
    total_predictions = Column(Integer, default=0)
    up_count = Column(Integer, default=0)
    down_count = Column(Integer, default=0)
    hold_count = Column(Integer, default=0)
    avg_confidence = Column(Float, nullable=True)

    # 메타 정보
    last_updated = Column(DateTime, default=datetime.now, nullable=False)
    based_on_prediction_count = Column(Integer, default=0)
```

**관계:**
- `Prediction` (읽기 전용): 기존 예측 데이터를 기반으로 주기적 재생성
- `API 조회`: `/api/stocks/{stock_code}/analysis` 엔드포인트에서 반환
- **캐시 정책**: 24시간 TTL, 예측 10건 이상 변경 시 재생성

### 4.9 데이터 모델 관계도

```mermaid
erDiagram
    News ||--o{ NewsStockMatch : "has"
    News ||--|| NewsEmbedding : "has"
    StockPrice ||--o{ NewsStockMatch : "references"
    News ||--o{ Prediction : "generates"
    Prediction }o--|| StockAnalysisSummary : "aggregates_to"

    News {
        int id PK
        string title
        string content
        datetime published_at
        string source
        string stock_code
        datetime created_at
    }

    StockPrice {
        int id PK
        string stock_code
        datetime date
        float open
        float high
        float low
        float close
        int volume
    }

    NewsStockMatch {
        int id PK
        int news_id FK
        string stock_code
        float price_change_1d
        float price_change_3d
        float price_change_5d
        datetime calculated_at
    }

    TelegramUser {
        int id PK
        int user_id UK
        datetime subscribed_at
        bool is_active
    }

    NewsEmbedding {
        int id PK
        int news_id FK
        float[] embedding
        string stock_code
        float price_change_1d
        float price_change_3d
        float price_change_5d
    }

    Prediction {
        int id PK
        int news_id FK
        string stock_code
        string direction
        float confidence
        text reasoning
        float current_price
        string target_period
        datetime created_at
        text short_term
        text medium_term
        text long_term
        json confidence_breakdown
        json pattern_analysis
    }

    StockAnalysisSummary {
        int id PK
        string stock_code UK
        text overall_summary
        text short_term_scenario
        text medium_term_scenario
        text long_term_scenario
        json risk_factors
        json opportunity_factors
        text recommendation
        int total_predictions
        int up_count
        int down_count
        int hold_count
        float avg_confidence
        datetime last_updated
        int based_on_prediction_count
    }
```

---

## 5. API 명세

Craveny는 **Next.js 웹 대시보드와 텔레그램 봇 이중 인터페이스**를 제공합니다. REST API는 사용자 대시보드, 관리자 모니터링, 종목 분석 조회를 지원합니다.

### 5.1 REST API Specification (OpenAPI 3.0)

**Base URL:** `http://localhost:8000/api`

**주요 엔드포인트:**

#### GET /health

시스템 전체 상태를 확인합니다.

**응답 200 (정상):**
```json
{
  "status": "healthy",
  "postgres": true,
  "milvus": true,
  "redis": true,
  "news_count": 1247,
  "vector_count": 1247,
  "last_news_collected": "2025-10-31T14:35:22+09:00"
}
```

**응답 503 (비정상):**
```json
{
  "status": "unhealthy",
  "postgres": false,
  "milvus": true,
  "redis": true,
  "error": "PostgreSQL connection failed"
}
```

#### GET /metrics

시스템 메트릭을 조회합니다.

**응답 200:**
```json
{
  "last_prediction": "2025-10-31T14:30:15+09:00",
  "telegram_notifications_sent_24h": 37,
  "average_prediction_time": 3.24,
  "total_active_users": 18,
  "celery_queue_size": 2,
  "openai_api_cost_today": 1.47
}
```

#### GET /api/dashboard/stats

관리자 대시보드 통계를 조회합니다 (총 예측 수, 평균 신뢰도, 방향별 분포).

**응답 200:**
```json
{
  "total_predictions": 1247,
  "avg_confidence": 0.78,
  "direction_distribution": {
    "up": 587,
    "down": 423,
    "hold": 237
  },
  "recent_predictions": [
    {
      "id": 1250,
      "stock_code": "005930",
      "direction": "up",
      "confidence": 0.85,
      "created_at": "2025-11-02T10:30:15+09:00"
    }
  ]
}
```

#### GET /api/news

뉴스 목록을 조회합니다 (필터링, 페이징 지원).

**Query Parameters:**
- `notified`: bool - 알림 전송 여부 필터 (optional)
- `stock_code`: str - 종목코드 필터 (optional)
- `page`: int - 페이지 번호 (default: 1)
- `page_size`: int - 페이지 크기 (default: 20)

**응답 200:**
```json
{
  "items": [
    {
      "id": 1247,
      "title": "삼성전자, 3나노 공정 양산 돌입",
      "content": "...",
      "stock_code": "005930",
      "published_at": "2025-11-02T09:00:00+09:00",
      "notified_at": "2025-11-02T09:05:12+09:00",
      "prediction": {
        "direction": "up",
        "confidence": 0.87,
        "reasoning": "..."
      }
    }
  ],
  "total": 1247,
  "page": 1,
  "page_size": 20
}
```

#### GET /api/stocks/summary

HOT 종목 요약을 조회합니다 (뉴스 수, 알림 수 기준).

**응답 200:**
```json
{
  "hot_stocks": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "news_count": 127,
      "notification_count": 45,
      "avg_confidence": 0.82,
      "latest_direction": "up"
    }
  ]
}
```

#### GET /api/stocks/{stock_code}/analysis

종목별 AI 투자 분석 리포트를 조회합니다 (StockAnalysisSummary 캐시).

**Path Parameters:**
- `stock_code`: str - 종목코드 (예: "005930")

**응답 200:**
```json
{
  "stock_code": "005930",
  "overall_summary": "삼성전자는 최근 3나노 공정 양산 발표로...",
  "short_term_scenario": "단기적으로 5% 상승 가능성...",
  "medium_term_scenario": "중기적으로는...",
  "long_term_scenario": "장기적으로는...",
  "risk_factors": ["반도체 업황 둔화 가능성", "환율 변동성"],
  "opportunity_factors": ["AI 반도체 수요 증가", "삼성 파운드리 수주 확대"],
  "recommendation": "매수 의견 (목표가: 85,000원)",
  "statistics": {
    "total_predictions": 127,
    "up_count": 87,
    "down_count": 25,
    "hold_count": 15,
    "avg_confidence": 0.82
  },
  "last_updated": "2025-11-02T08:00:00+09:00"
}
```

**응답 404:**
```json
{
  "detail": "Analysis not found for stock code 005930"
}
```

#### GET /api/predictions

예측 이력을 조회합니다 (필터링, 페이징 지원).

**Query Parameters:**
- `stock_code`: str - 종목코드 필터 (optional)
- `direction`: str - 방향 필터 ("up", "down", "hold") (optional)
- `min_confidence`: float - 최소 신뢰도 필터 (0.0~1.0) (optional)
- `page`: int - 페이지 번호 (default: 1)
- `page_size`: int - 페이지 크기 (default: 20)

**응답 200:**
```json
{
  "items": [
    {
      "id": 1250,
      "news_id": 1247,
      "stock_code": "005930",
      "direction": "up",
      "confidence": 0.87,
      "reasoning": "3나노 공정 양산 발표로 기술 경쟁력 강화...",
      "short_term": "T+1일 예측: +3.2%",
      "medium_term": "T+3일 예측: +5.8%",
      "long_term": "T+5일 예측: +7.1%",
      "created_at": "2025-11-02T09:05:00+09:00"
    }
  ],
  "total": 1247,
  "page": 1,
  "page_size": 20
}
```

**자동 문서화:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 6. 컴포넌트

시스템을 논리적 컴포넌트로 분해하여 각 컴포넌트의 책임과 인터페이스를 명확히 정의합니다.

### 6.1 News Crawler (뉴스 크롤러)

**책임:** 네이버 뉴스, 한국경제, 매일경제에서 증권 뉴스 자동 크롤링

**주요 인터페이스:**
- `crawl_news(source: str) -> List[News]`
- `extract_stock_code(title: str, content: str) -> str | None`
- `is_duplicate(news: News) -> bool`
- `save_news(news: News) -> int`

**기술 상세:** `backend/crawlers/news_crawler.py`, APScheduler 10분 주기

### 6.2 Stock Price Collector (주가 수집기)

**책임:** FinanceDataReader로 한국 증시 주가 데이터 수집 (1분 주기)

**주요 인터페이스:**
- `collect_stock_prices(stock_codes: List[str]) -> List[StockPrice]`
- `is_market_open() -> bool`
- `save_prices(prices: List[StockPrice]) -> int`

**기술 상세:** `backend/crawlers/stock_crawler.py`, 장중 9:00~15:30만 실행

### 6.3 Embedding Service (임베딩 서비스)

**책임:** 뉴스 텍스트 → 768차원 벡터 변환 (OpenAI API)

**주요 인터페이스:**
- `embed_news(news: News) -> List[float]`
- `batch_embed(news_list: List[News]) -> List[NewsEmbedding]`
- `save_to_milvus(embeddings: List[NewsEmbedding]) -> int`

**기술 상세:** `backend/llm/embedder.py`, 매일 16:00 일괄 처리

### 6.4 RAG Search Service (벡터 유사도 검색)

**책임:** 새 뉴스의 유사 과거 뉴스 TOP 5 검색 (<100ms)

**주요 인터페이스:**
- `search_similar_news(news_text: str, top_k: int = 5) -> List[News]`
- `embed_query(text: str) -> List[float]`
- `fetch_news_details(news_ids: List[int]) -> List[News]`

**기술 상세:** `backend/llm/similarity_search.py`, Milvus L2 거리

### 6.5 LLM Prediction Engine (예측 엔진)

**책임:** 현재 뉴스 + 유사 과거 뉴스 + 현재 주가 → LLM 종합 분석 (2~5초)

**주요 인터페이스:**
- `predict(news: News, similar_news: List[News], current_price: float) -> Prediction`
- `build_prompt(news: News, similar_news: List[News]) -> str`
- `parse_llm_response(response: str) -> Prediction`

**기술 상세:** `backend/llm/predictor.py`, GPT-4o-mini API

### 6.6 Telegram Bot (텔레그램 봇)

**책임:** 사용자 명령어 처리 및 알림 메시지 전송

**주요 인터페이스:**
- `send_notification(user_id: int, message: str) -> bool`
- `handle_start(user_id: int) -> None`
- `handle_stop(user_id: int) -> None`

**기술 상세:** `backend/telegram/bot.py`, python-telegram-bot

### 6.7 Celery Task Orchestrator (비동기 작업 오케스트레이터)

**책임:** 새 뉴스 감지 → 예측 파이프라인 트리거 (순차 실행)

**주요 인터페이스:**
- `@celery.task process_new_news(news_id: int) -> None`
- `@celery.task retry_failed_task(task_id: str) -> None`

**기술 상세:** `backend/scheduler/celery_tasks.py`, Redis 브로커

### 6.8 컴포넌트 다이어그램

```mermaid
graph TB
    subgraph "External Services"
        NEWS_SITES[뉴스 웹사이트]
        FDR[FinanceDataReader]
        OPENAI[OpenAI API]
        TELEGRAM_API[Telegram API]
    end

    subgraph "Schedulers (APScheduler)"
        NEWS_CRON[News Crawler<br/>10분 주기]
        STOCK_CRON[Stock Collector<br/>1분 주기]
        MATCHER_CRON[News-Stock Matcher<br/>일일 15:40]
        EMBED_CRON[Embedding Service<br/>일일 16:00]
    end

    subgraph "Core Services"
        RAG[RAG Search Service]
        PREDICTOR[LLM Prediction Engine]
        TIME_CLASS[Time Classifier]
        MSG_BUILDER[Message Builder]
        FILTER[Notification Filter]
    end

    subgraph "Async Workers (Celery)"
        CELERY[Celery Task<br/>Orchestrator]
    end

    subgraph "User Interface"
        BOT[Telegram Bot]
    end

    subgraph "Data Layer"
        DB_LAYER[Database Layer<br/>Repository Pattern]
        PG[(PostgreSQL)]
        MILVUS[(Milvus)]
        REDIS[(Redis)]
    end

    NEWS_SITES --> NEWS_CRON
    FDR --> STOCK_CRON

    NEWS_CRON --> DB_LAYER
    STOCK_CRON --> DB_LAYER
    MATCHER_CRON --> DB_LAYER

    EMBED_CRON --> OPENAI
    EMBED_CRON --> DB_LAYER

    CELERY --> RAG
    RAG --> OPENAI
    RAG --> DB_LAYER

    RAG --> PREDICTOR
    PREDICTOR --> OPENAI
    PREDICTOR --> TIME_CLASS
    PREDICTOR --> MSG_BUILDER

    MSG_BUILDER --> FILTER
    FILTER --> BOT
    BOT --> TELEGRAM_API

    DB_LAYER --> PG
    DB_LAYER --> MILVUS
    FILTER --> REDIS
    CELERY --> REDIS
```

---

## 7. 데이터베이스 스키마

### 7.1 PostgreSQL 스키마

#### News (뉴스) 테이블

```sql
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(100) NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_news_stock_code ON news(stock_code);
CREATE INDEX idx_news_published_at ON news(published_at DESC);
CREATE INDEX idx_news_stock_published ON news(stock_code, published_at DESC);
```

#### StockPrice (주가) 테이블

```sql
CREATE TABLE stock_prices (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    open DECIMAL(10, 2) NOT NULL CHECK (open > 0),
    high DECIMAL(10, 2) NOT NULL CHECK (high > 0),
    low DECIMAL(10, 2) NOT NULL CHECK (low > 0),
    close DECIMAL(10, 2) NOT NULL CHECK (close > 0),
    volume BIGINT NOT NULL CHECK (volume >= 0),

    CONSTRAINT stock_prices_unique_key UNIQUE (stock_code, date)
);

CREATE INDEX idx_stock_prices_stock_date ON stock_prices(stock_code, date DESC);
```

#### NewsStockMatch (뉴스-주가 매칭) 테이블

```sql
CREATE TABLE news_stock_match (
    id SERIAL PRIMARY KEY,
    news_id INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    price_change_1d DECIMAL(6, 2),
    price_change_3d DECIMAL(6, 2),
    price_change_5d DECIMAL(6, 2),
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT news_stock_match_unique_key UNIQUE (news_id)
);

CREATE INDEX idx_news_stock_match_news_id ON news_stock_match(news_id);
```

#### TelegramUser (텔레그램 사용자) 테이블

```sql
CREATE TABLE telegram_users (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    subscribed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_telegram_users_is_active ON telegram_users(is_active)
    WHERE is_active = TRUE;
```

### 7.2 Milvus 벡터 DB 스키마

#### NewsEmbedding 컬렉션

```python
# Milvus 컬렉션 생성 (scripts/init_milvus.py)
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection

fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="news_id", dtype=DataType.INT64),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    FieldSchema(name="stock_code", dtype=DataType.VARCHAR, max_length=10),
    FieldSchema(name="price_change_1d", dtype=DataType.FLOAT),
    FieldSchema(name="price_change_3d", dtype=DataType.FLOAT),
    FieldSchema(name="price_change_5d", dtype=DataType.FLOAT),
]

schema = CollectionSchema(fields=fields, description="뉴스 임베딩 (RAG)")
collection = Collection(name="news_embeddings", schema=schema)

# 인덱스 생성 (IVF_FLAT - 정확도 우선)
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
collection.create_index(field_name="embedding", index_params=index_params)
```

---

## 8. 통합 프로젝트 구조

```plaintext
craveny/
├── .github/workflows/          # CI/CD
│   ├── ci.yml
│   └── deploy.yml
├── frontend/                   # Next.js 웹 대시보드
│   ├── app/                    # App Router
│   │   ├── page.tsx            # 사용자 대시보드 (/)
│   │   ├── layout.tsx          # Root Layout
│   │   ├── globals.css
│   │   ├── admin/
│   │   │   └── dashboard/page.tsx  # 관리자 대시보드 (/admin/dashboard)
│   │   ├── stocks/
│   │   │   ├── page.tsx        # 종목 목록 (/stocks)
│   │   │   └── [stockCode]/page.tsx  # 종목 상세 (/stocks/:code)
│   │   ├── predictions/page.tsx    # 예측 이력 (/predictions)
│   │   └── components/
│   │       └── Navigation.tsx  # 네비게이션
│   ├── public/
│   ├── next.config.ts          # API 프록시 설정
│   ├── tailwind.config.ts
│   ├── package.json
│   └── tsconfig.json
├── backend/                    # FastAPI 애플리케이션
│   ├── main.py                 # 진입점 (FastAPI 앱 초기화)
│   ├── config.py               # 환경 변수
│   ├── api/                    # REST API 라우터
│   │   ├── __init__.py
│   │   ├── dashboard.py        # GET /api/dashboard/stats
│   │   ├── news.py             # GET /api/news
│   │   ├── stocks.py           # GET /api/stocks/*
│   │   ├── prediction.py       # GET /api/predictions
│   │   └── statistics.py       # GET /api/statistics/summary
│   ├── crawlers/               # 데이터 수집
│   │   ├── base_crawler.py
│   │   ├── news_crawler.py
│   │   ├── stock_crawler.py
│   │   ├── news_saver.py
│   │   └── news_stock_matcher.py
│   ├── llm/                    # AI/ML & 예측
│   │   ├── embedder.py
│   │   ├── vector_search.py    # Milvus 유사도 검색
│   │   ├── predictor.py        # LLM 예측 생성 (GPT-4o)
│   │   ├── prediction_cache.py # Redis 캐싱
│   │   ├── investment_report.py # 투자 리포트 생성
│   │   └── prompts/
│   ├── notifications/          # 알림 시스템
│   │   ├── __init__.py
│   │   ├── telegram.py         # 텔레그램 메시지 전송
│   │   └── auto_notify.py      # 자동 알림 로직
│   ├── services/               # 비즈니스 로직
│   │   └── stock_analysis_service.py
│   ├── db/                     # 데이터베이스
│   │   ├── base.py
│   │   ├── session.py
│   │   ├── models/             # SQLAlchemy 모델
│   │   │   ├── __init__.py
│   │   │   ├── news.py
│   │   │   ├── stock_price.py
│   │   │   ├── prediction.py
│   │   │   └── stock_analysis.py
│   │   ├── milvus_client.py
│   │   └── repositories/
│   ├── scheduler/              # 스케줄링
│   │   ├── crawler_scheduler.py  # APScheduler (10분 주기 크롤링)
│   │   ├── celery_app.py
│   │   └── celery_tasks.py
│   ├── scripts/                # 유틸리티 스크립트
│   │   ├── fix_naver_news.py
│   │   ├── check_status.py
│   │   └── start_crawler.py
│   └── utils/
│       ├── stock_mapping.py
│       └── encoding_normalizer.py
├── data/                       # 데이터 및 로그
├── scripts/                    # 프로젝트 레벨 스크립트
│   ├── init_db.py
│   ├── init_milvus.py
│   ├── test_*.py               # 테스트 스크립트들
│   └── initial_data_collection.py
├── tests/                      # 테스트
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/                       # 문서
│   ├── prd/
│   │   ├── epic-1-data-infrastructure.md
│   │   └── epic-2-llm-prediction-notifications.md
│   ├── stories/
│   │   ├── 1.*.md              # Epic 1 스토리들
│   │   └── 2.*.md              # Epic 2 스토리들
│   ├── architecture.md
│   └── DASHBOARD_UX_DESIGN.md
├── infrastructure/             # 인프라
│   ├── docker-compose.yml
│   └── Dockerfile
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── RUN_GUIDE.md
└── README.md
```

---

## 9. 코딩 표준

### 9.1 필수 규칙

- **환경 변수 접근:** `backend/config.py`의 `settings` 객체만 사용
- **데이터베이스 접근:** Repository Pattern 필수
- **OpenAI API 호출:** `settings.OPENAI_MODEL` 사용
- **에러 처리:** 모든 외부 API 호출 try-except 래핑
- **로깅:** `print()` 금지, `logger` 사용
- **타입 힌트:** 모든 함수 시그니처 필수
- **비동기 함수:** FastAPI는 `async def`, Celery는 동기 함수

### 9.2 명명 규칙

| 요소 | 규칙 | 예시 |
|------|------|------|
| Python 모듈 | snake_case | `news_crawler.py` |
| Python 클래스 | PascalCase | `NewsRepository` |
| 함수/메서드 | snake_case | `get_news_by_id()` |
| 변수 | snake_case | `news_count` |
| 상수 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| 데이터베이스 테이블 | snake_case | `news`, `stock_prices` |
| API 엔드포인트 | kebab-case | `/health`, `/api/news` |

### 9.3 코드 포맷팅

```bash
# Black 포맷팅 (라인 길이 100)
black --line-length 100 backend/ tests/

# Flake8 린팅
flake8 backend/ tests/ --max-line-length 100

# mypy 타입 체크
mypy backend/ --ignore-missing-imports
```

---

## 10. 개발 워크플로우

### 10.1 로컬 개발 환경 설정

```bash
# 1. 레포지토리 클론
git clone https://github.com/your-org/craveny.git
cd craveny

# 2. Python 가상환경 (Backend)
python3.11 -m venv venv
source venv/bin/activate

# 3. Backend 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Frontend 의존성 설치
cd frontend
npm install
cd ..

# 5. 환경 변수
cp .env.example .env
# .env 편집 (OPENAI_API_KEY, TELEGRAM_BOT_TOKEN 등)

# 6. Docker 서비스 실행
cd infrastructure
docker-compose up -d

# 7. DB 초기화
python scripts/init_db.py
python scripts/init_milvus.py
```

### 10.2 개발 명령어

**Frontend (Next.js):**
```bash
# 개발 서버 (핫 리로드, http://localhost:3000)
cd frontend
npm run dev

# 프로덕션 빌드
npm run build

# 프로덕션 실행
npm run start

# 린트
npm run lint
```

**Backend (FastAPI):**
```bash
# FastAPI 서버 (핫 리로드, http://localhost:8000)
uvicorn backend.main:app --reload

# Celery Worker
celery -A backend.scheduler.celery_app worker --loglevel=info

# 크롤러 시작 (APScheduler)
python backend/scripts/start_crawler.py

# 텔레그램 봇
python -m backend.notifications.telegram

# 테스트
pytest tests/
pytest --cov=backend tests/

# 코드 품질
black backend/ tests/
flake8 backend/ tests/
mypy backend/
```

---

## 11. 배포 아키텍처

### 11.1 배포 전략

**백엔드 배포:**
- **플랫폼:** AWS EC2 t3.small (서울 리전)
- **방식:** Docker Compose
- **배포:**
  ```bash
  git pull origin main
  docker-compose down
  docker-compose up -d --build
  ```

### 11.2 CI/CD 파이프라인

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run Tests
        run: pytest tests/ --cov=backend
```

### 11.3 환경

| 환경 | 용도 | 배포 방식 |
|------|------|-----------|
| Development | 로컬 개발 | Docker Compose |
| Production | 실제 서비스 | AWS EC2 |

---

## 12. 보안 및 성능

### 12.1 보안

- **입력 검증:** Pydantic 자동 검증
- **토큰 저장:** 환경 변수 (.env)
- **API 인증:** MVP는 없음 (AWS Security Group IP 제한)

### 12.2 성능

- **응답 시간 목표:** <5초 (뉴스 → 알림)
- **캐싱:** Redis (중복 알림 방지)
- **DB 최적화:** 인덱스 최적화

---

## 13. 테스팅 전략

### 13.1 테스트 피라미드

```
     E2E (5%)
    /        \
Integration (25%)
/              \
Unit (70%)
```

**목표:** Unit 커버리지 70% 이상

### 13.2 테스트 예시

```python
# tests/unit/test_time_classifier.py
def test_classify_time_premarket():
    dt = datetime(2025, 10, 31, 7, 30)
    assert classify_time(dt) == "PRE_MARKET"

# tests/integration/test_milvus_search.py
def test_search_similar_news_returns_top5():
    results = search_similar_news("삼성전자", top_k=5)
    assert len(results) == 5
```

---

## 14. 에러 핸들링 전략

### 14.1 에러 응답 포맷

```python
# backend/api/health.py
@router.get("/health")
async def health_check():
    try:
        pg_ok = check_postgres()
        if not pg_ok:
            raise HTTPException(status_code=503)
        return {"status": "healthy"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503)
```

---

## 15. 모니터링 및 관찰성

### 15.1 모니터링 스택

- **백엔드:** Python logging (파일)
- **에러 추적:** Python logging
- **메트릭:** `/metrics` 엔드포인트

### 15.2 주요 메트릭

- 요청 비율 (requests/min)
- 에러 비율 (%)
- 응답 시간 (평균/p95)
- Celery 큐 크기

---

**문서 작성 완료:** 2025-10-31
**다음 단계:** 개발 시작, Architect Checklist 실행 (선택적)
