# Project Overview – Craveny

## Purpose
AI 기반 증권 뉴스 분석 및 단기 주가 방향성 예측 플랫폼. 뉴스 크롤링 → GPT-4o 추론 → Next.js 대시보드/텔레그램으로 배포하는 E2E 파이프라인.

## Architecture Level
- **Field Type:** Brownfield (existing FastAPI + Next.js codebase)
- **Track:** BMad Method
- **Structure:** Multi-part repo (backend, frontend, infrastructure)

## Tech Stack Snapshot
| Layer | Stack |
| --- | --- |
| Frontend | Next.js 15 / React 19 / Tailwind / React Query |
| Backend | FastAPI, Celery, APScheduler, SQLAlchemy |
| Data | PostgreSQL, Redis, Milvus, MinIO |
| AI | OpenAI GPT-4o, text-embedding-3-small |
| Infra | Docker Compose on AWS EC2 |

## Key Documents
- API contracts: `docs/api-contracts-backend.md`, `docs/api-contracts-frontend.md`
- Data models: `docs/data-models-backend.md`, `docs/data-models-frontend.md`
- Architecture (per part): `docs/architecture-*.md`
- Integration overview: `docs/integration-architecture.md`
- Development & deployment: `docs/development-guide.md`, `docs/deployment-configuration.md`

## Current Status
- Legacy planning docs archived (see `docs/archive/planning-pre-*`).
- Fresh workflow tracking stored in `docs/bmm-workflow-status.yaml` – next workflow after documentation: `prd` (PM agent).

## Next Actions
1. Review newly generated documentation (links above) to brief upcoming PRD/architecture workflows.
2. Execute `*prd` workflow referencing `docs/index.md` once generated (post-document-project completion).
3. Prepare deployment target (EC2 + Docker Compose) following `docs/deployment-configuration.md`.
