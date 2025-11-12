# craveny - Epic Breakdown

**Author:** young
**Date:** 2025-11-11
**Project Level:** 3
**Target Scale:** 24/7 single-node deployment (t3.small)

---

## Overview

Craveny will be delivered through four cohesive epics: (1) Infra & Deployment Foundation, (2) Data/Model Pipeline Stabilization, (3) Dashboard & Model Comparison Experience, (4) Telegram & Ops Notifications. Each epic is scoped to a single value stream and sized so that its stories fit 200k-context dev agents.

---

## Epic 1: Infra & Deployment Foundation

Ensure the EC2 + Docker Compose stack, security, and monitoring baselines are in place so the rest of the product can run reliably.

### Story 1.1: Provision t3.small host & bring up Compose stack

단일 인스턴스를 구성하고 `infrastructure/docker-compose.yml` 를 실행해 Postgres/Redis/Milvus/MinIO/etcd 등 핵심 서비스를 기동한다.

**Status:** ✅ DONE (2025-01-12)

**Acceptance Criteria**
```
✅ Given AWS EC2 t3.small 인스턴스가 준비되어 있고 Docker 24/Compose 2.20이 설치돼 있을 때
✅ When docker-compose up -d 를 실행하면
✅ Then Postgres/Redis/Milvus/MinIO/etcd 컨테이너가 모두 healthy 상태여야 한다
✅ And `.env` 값이 적용되어 데이터 경로 볼륨이 생성되어야 한다
```

**Prerequisites:** 없음

**Technical Notes:** Ubuntu 22.04, Security Group 제한, 시스템 업데이트, compose logs 점검

**Completion Summary:**
- ✅ 모든 데이터 스택 서비스 healthy 상태 확인
- ✅ Docker 볼륨 생성 확인 (postgres_data, milvus_data, etcd_data, minio_data)
- ✅ .env 파일 검증 완료
- ✅ 포트 매핑 정상 작동 (Postgres:5432, Redis:6380, Milvus:19530/9091)

### Story 1.2: Backend/Frontend 런타임 서비스 기동

FastAPI 서버와 Next.js 빌드를 Compose 환경과 연동해 `uvicorn backend.main:app` + `next start -p 3000` 으로 운영한다.

**Current Status:** 🔄 In Progress
- ✅ Dockerfile 초안 작성 완료 (backend/Dockerfile, frontend/Dockerfile)
- ⚠️ Dockerfile 경로 수정 필요 (context 이슈)
- ⏳ 빌드/런 테스트 대기 중

**Acceptance Criteria**
```
Given docker-compose 가 데이터 스택을 실행 중일 때
When backend/ frontend 서비스를 빌드 및 실행하면
Then http://<host>:8000/health 와 http://<host>:3000 이 모두 200 응답을 제공한다
```

**Prerequisites:** Story 1.1

**Technical Notes:**
- nginx reverse proxy, JWT/환경변수 세팅, systemd unit(Optional)
- **⚠️ Dockerfile 수정 필요 사항:**
  - Backend: requirements.txt 경로 수정 필요 (프로젝트 루트에 위치)
  - Backend: COPY 경로가 docker-compose context(부모 디렉토리)와 맞지 않음
  - Frontend: package.json 경로 및 COPY 경로 조정 필요
  - Frontend: PORT 환경변수 3030으로 통일 (현재 Dockerfile은 3030, 설명은 3000)
  - 헬스체크 설정 추가 필요 (backend/frontend 서비스)

### Story 1.3: 보안/운영 구성 적용

HTTPS 종료, 비밀 변수 관리(OPENAI/OPENROUTER/Telegram/DB), CloudWatch 로그/헬스체크를 설정한다.

**Acceptance Criteria**
```
Given 배포 환경에서 secrets 가 SSM 또는 .env 로 주입되고
When HTTPS reverse proxy 및 CloudWatch agent 를 구성하면
Then 모든 API 호출이 HTTPS 로 노출되고 /health 실패 시 알림을 수신한다
```

**Prerequisites:** Story 1.1, 1.2

**Technical Notes:** nginx + certs(or ALB), CloudWatch 에이전트, Telegram 운영자 알림

---

## Epic 2: Data & Model Pipeline Stabilization

뉴스 크롤링, 예측 파이프라인, Redis/Milvus 연계를 Compose 환경에서 정상화한다.

### Story 2.1: 크롤러/스케줄러 작업 재구성

뉴스 크롤러와 APScheduler 작업을 Compose 환경에서 실행하며, 주기·로그·에러 핸들링을 확인한다.

**Acceptance Criteria**
```
Given docker-compose 와 backend 서비스가 실행 중일 때
When scheduler.py 를 실행하거나 systemd 로 등록하면
Then 모든 크롤러 작업이 데이터를 적재하고 실패 시 재시도 로그가 남는다
```

**Prerequisites:** Story 1.1, 1.2

**Technical Notes:** Redis 락/큐 사용, APScheduler job ID 관리, 로그 포맷 통일

### Story 2.2: 예측/임베딩 파이프라인 연결

LLM 호출(OpenAI/OpenRouter), Milvus 임베딩, Postgres 저장 흐름을 테스트한다.

**Acceptance Criteria**
```
Given OPENAI/OPENROUTER 키가 설정되어 있을 때
When 예측 작업을 수행하면
Then Milvus 에 임베딩이 저장되고 Postgres 의 prediction 테이블이 업데이트된다
And 예측 결과가 대시보드/알림에 전달될 데이터 구조로 기록된다
```

**Prerequisites:** Story 2.1

**Technical Notes:** `backend/db/milvus_client.py` 확인, 비용 모니터링

### Story 2.3: 데이터 품질 및 캐싱 검증

React Query/Redis 캐시와 Postgres 데이터를 비교해 누락·지연을 점검하고 TTL 전략을 조정한다.

**Acceptance Criteria**
```
Given 대시보드에서 모델별 데이터를 조회할 때
When Redis 캐시를 활성화하고 TTL 을 설정하면
Then 동일한 요청이 캐시에서 빠르게 응답되고 데이터 불일치가 발생하지 않는다
```

**Prerequisites:** Story 2.2

**Technical Notes:** React Query staleTime 설정, Redis key naming

---

## Epic 3: Dashboard & Model Comparison Experience

Next.js 대시보드에서 모델별 비교 경험을 안정화하고 성능을 보장한다.

### Story 3.1: 모델 비교 화면 연동 및 UI 검증

`app/predictions`, `app/stocks` 페이지에서 API 응답을 연결하고 모델별 카드/표가 정상 표시되도록 한다.

**Acceptance Criteria**
```
Given backend API 가 /api/predictions 와 /api/stocks 를 제공할 때
When 프론트엔드 페이지를 로드하면
Then 각 모델별 분석 카드와 비교표가 로딩 스피너 후 3초 이내에 렌더링된다
```

**Prerequisites:** Story 2.3

**Technical Notes:** React Query hooks, 로딩/에러 상태 처리, Tailwind 스타일

### Story 3.2: 실사용 시나리오 테스트

로그인 → 종목 선택 → 모델 비교 → 알림 구독의 엔드투엔드 시나리오를 점검한다.

**Acceptance Criteria**
```
Given 테스트 계정으로 로그인했을 때
When 종목을 선택하고 모델 비교 화면을 확인하면
Then 예측 결과와 설명이 정상적으로 표시되고 오류 로그가 없어야 한다
```

**Prerequisites:** Story 3.1

**Technical Notes:** 수동/자동 테스트, 로그 분석

### Story 3.3: 성능/접근성 점검

Lighthouse 등으로 주요 페이지 성능과 접근성을 확인하고 필요한 튜닝을 한다.

**Acceptance Criteria**
```
Given Next.js 앱이 빌드된 상태일 때
When Lighthouse 체크를 수행하면
Then Performance 80+, Accessibility 70+ 를 달성한다
```

**Prerequisites:** Story 3.1

**Technical Notes:** 이미지 최적화, Lazy loading, Tailwind 접근성 가이드

---

## Epic 4: Telegram & Ops Notifications

투자자 알림과 운영자 모니터링 경보를 정비한다.

### Story 4.1: 텔레그램 알림 채널 재연결

`python-telegram-bot` 을 이용해 새로운 배포 환경에서 알림 메시지를 보낼 수 있도록 설정한다.

**Acceptance Criteria**
```
Given TELEGRAM_BOT_TOKEN 이 설정되어 있을 때
When 알림 테스트 명령을 실행하면
Then 지정된 채널/사용자가 메시지를 수신한다
```

**Prerequisites:** Story 2.2

**Technical Notes:** Bot 토큰/챗 ID, 실패 시 fallback 로그

### Story 4.2: 운영 경보/헬스체크 알림 구성

CloudWatch 또는 cron 기반으로 `/health` 실패나 주요 작업 실패 시 운영자에게 Telegram/이메일 알림을 보낸다.

**Acceptance Criteria**
```
Given CloudWatch 경보 또는 커스텀 헬스체크 스크립트가 설정되어 있을 때
When backend/Compose 서비스가 실패하면
Then 운영자 알림이 5분 이내에 도착한다
```

**Prerequisites:** Story 4.1, Story 1.3

**Technical Notes:** CloudWatch Alarm → SNS → Telegram Webhook, 또는 cron 스크립트

### Story 4.3: 운영/배포 체크리스트 문서화

배포 전/후 점검표 및 롤백 지침을 작성해 향후 스프린트에서 재사용할 수 있도록 한다.

**Acceptance Criteria**
```
Given docs/ 디렉터리에 운영 문서를 작성할 때
When 체크리스트에 따라 배포를 수행하면
Then 모든 주요 단계(Compose 업, backend/프론트 확인, 알림 테스트)가 통과됨을 기록한다
```

**Prerequisites:** Story 1.1~4.2 완료 후 문서화

**Technical Notes:** docs/runbook.md 등으로 작성, rollback 절차 포함

---

_This epic breakdown enables the next workflows (architecture refinements / sprint planning) to proceed with clear, bite-sized stories._
