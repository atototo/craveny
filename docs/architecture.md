# Architecture

## Executive Summary

Craveny is deployed as a cost-efficient single-node SaaS stack: Docker Compose on an EC2 t3.small instance orchestrates Postgres, Redis, Milvus (with etcd + MinIO), while FastAPI and Next.js power the API/notification layer and investor dashboard. The architecture emphasizes 24/7 uptime, deterministic model-comparison experiences, and easy rehydration from source via scripted setup.

## Project Initialization

First implementation story should ensure the host is provisioned and services started:

```bash
cd infrastructure && docker-compose up -d && \
  cd .. && uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

This establishes the core services (Postgres/Redis/Milvus) and exposes the FastAPI app used by the Next.js frontend and Telegram worker.

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| Hosting | EC2 t3.small, Ubuntu 22.04, Docker 24 + Compose 2.20 | 24.0.5 / 2.20 | All | Single-node keeps cost minimal while supporting stack |
| Backend Runtime | FastAPI + Uvicorn + Celery + APScheduler | Python 3.11 / FastAPI 0.104 | Data ingestion, predictions, alerts | Matches existing codebase, async friendly |
| Frontend | Next.js 15 App Router, React 19, React Query | 15.1.4 / 19.0.0 | Dashboard/Model comparison | Enables SSR/CSR mix and caching |
| Data Layer | Postgres 13, Redis 7, Milvus 2.3 + MinIO/etcd | 13.12 / 7.0 / 2.3.0 | Storage, embeddings, caching | Aligns with current dependencies and Compose stack |
| Notifications | Telegram bot via `python-telegram-bot` | v20.7 | Alerting epic | Already proven for investors, avoids new channel |
| Security | JWT auth + HTTPS via nginx/ALB, secrets in SSM/.env | n/a | All | Keeps private APIs protected without extra VPN |
| Observability | CloudWatch agent + `/health` endpoint | n/a | Ops | Gives simple uptime check and log centralization |

## Project Structure

```
craveny/
├── backend/                      # FastAPI application, services, schedulers, crawlers
│   ├── api/                      # Domain routers (auth, stocks, prediction, etc.)
│   ├── services/                 # Business logic
│   ├── db/                       # SQLAlchemy models, migrations, Milvus client
│   ├── llm/, notifications/, scheduler/, crawlers/
│   └── main.py                   # Uvicorn entrypoint
├── frontend/                     # Next.js 15 App Router dashboard
│   ├── app/ (predictions, stocks, admin, ab-test, login)
│   └── components/, contexts/
├── infrastructure/               # docker-compose.yml, Dockerfiles
├── docs/                         # PRD, architecture, deployment guides, status tracking
├── scripts/                      # init_db.py, init_milvus.py, helper scripts
├── data/                         # local data/embeddings cache
└── tests/                        # pytest suites
```

## Epic to Architecture Mapping

| Epic / Capability | Architectural Elements |
| --- | --- |
| Investor Dashboard / Model Comparison | frontend `app/predictions`, `app/stocks` + backend `/api/predictions`, `/api/stocks`; React Query caches + Postgres views + Milvus lookup |
| Telegram Alerts | backend `notifications/` workers, APScheduler jobs, Redis broker, Telegram bot token |
| Data Ingestion & Scheduling | backend `crawlers/`, `scheduler/`, Compose-managed Milvus/Postgres volumes |
| Admin Controls (AB test, models) | frontend `app/ab-test`, `app/models`; backend `/api/ab-test`, `/api/models`; DB tables `ab_test_config`, `model` |

## Technology Stack Details

### Core Technologies

- **Frontend:** Next.js 15.1.4, React 19, TypeScript 5, Tailwind 3.x, React Query 5, Recharts, lucide-react
- **Backend:** Python 3.11, FastAPI 0.104+, SQLAlchemy 2, Pydantic v2, Uvicorn, Celery 5.3, APScheduler 3.10
- **Data & Infra:** Postgres 13-alpine, Redis 7-alpine, Milvus 2.3 (with etcd & MinIO), Docker Compose v3.8
- **AI Providers:** OpenAI GPT-4o + text-embedding-3-small via OpenAI/OpenRouter APIs

### Integration Points

1. **Frontend ↔ Backend:** HTTPS REST requests to `/api/*` with JWT auth header; React Query handles caching/invalidations.
2. **Backend ↔ Postgres:** SQLAlchemy session factory from `backend/db/session.py` used across repositories.
3. **Backend ↔ Redis:** Celery broker + short-lived caches (market snapshots, throttling) via `redis://` env var.
4. **Backend ↔ Milvus/MinIO:** `backend/db/milvus_client.py` persists and queries embeddings for news/predictions.
5. **Backend ↔ Telegram:** `python-telegram-bot` client posts alerts using bot token from secrets.
6. **Schedulers ↔ Services:** APScheduler + Celery tasks run crawlers and evaluation jobs at configured intervals.

## Novel Pattern Designs

_No novel patterns required for this release; standard service/router layering suffices._

## Implementation Patterns

- **Router-Service-Repository:** Keep API modules thin, delegate to service classes that orchestrate repositories/LLM calls.
- **Job Idempotency:** Scheduler jobs ensure duplicate prevention via Redis locks or timestamp guards.
- **React Query Hooks:** Each feature defines hooks (e.g., `usePredictions`, `useStockDetail`) centralizing fetch/transform logic.
- **Environment Separation:** `.env` powers local Compose; production loads the same keys from AWS SSM or EC2 user-data without code changes.

## Consistency Rules

### Naming Conventions

- Python modules/functions snake_case; classes PascalCase.
- React components PascalCase; hooks start with `use`. DB tables singular lowercase.
- API routes prefixed with `/api/{domain}`; Telegram commands kebab-case.

### Code Organization

- New backend domains create parallel folders in `api/`, `services/`, `db/models/`.
- Shared utilities live under `backend/utils/` to avoid duplication.
- Frontend feature folders inside `app/` keep components colocated with route logic.

### Error Handling

- FastAPI routers raise `HTTPException` with meaningful status codes.
- Scheduler jobs wrap critical sections with try/except and log structured errors.

### Logging Strategy

- Python `logging` module outputs JSON-like lines with correlation IDs (request ID, job name).
- Compose logs aggregated by journald/CloudWatch agent; alerts triggered when `/health` fails.

## Data Architecture

- **Postgres Tables:** `user`, `stock`, `news`, `prediction`, `model`, `evaluation_history`, `daily_performance`, `ab_test_config`, `match`.
- **Relationships:** `prediction` FK → `stock`, `model`; `match` links `news` ↔ `stock`; evaluation tables reference `model` for trend tracking.
- **Milvus Collections:** `news_embeddings` and `prediction_embeddings` keyed by corresponding Postgres IDs, metadata mirrored in SQL tables.

## API Contracts

- `/api/auth`: POST login w/ email/password → JWT; refresh endpoint for token renewal.
- `/api/predictions`: GET list with `symbol`, `model`, `direction`, `confidence`, `reasoning`.
- `/api/stocks`: GET metadata; `/api/stocks/management` (admin) for overrides.
- `/api/evaluations`: GET metrics for charts (win rate, Sharpe, etc.).
- `/api/ab-test`: CRUD experiment variants + allocations.
- `/api/models`: Manage registered AI model configs/prompts.

## Security Architecture

- JWT tokens stored client-side via `AuthContext`; backend verifies roles per route.
- HTTPS termination via nginx/ALB; backend listens on localhost, Compose network private.
- Secrets (`OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, DB creds) injected via `.env` locally or AWS SSM in prod.
- DB/Redis/Milvus ports firewalled to host; only reverse proxy exposed publicly.

## Performance Considerations

- React Query caching reduces redundant fetches; stale-while-revalidate approach for dashboards.
- Redis caches frequently requested metrics; TTL tuned to avoid stale data.
- APScheduler staggers heavy jobs (crawl, embedding) to prevent CPU spikes on t3.small.
- Healthchecks detect degraded services; Compose restart policies keep containers running.

## Deployment Architecture

- `infrastructure/docker-compose.yml` manages Postgres/Redis/Milvus/MinIO/etcd.
- Backend served via uvicorn (optionally Compose-managed) behind nginx reverse proxy.
- Frontend built with `npm run build` and served via `next start -p 3000`; same reverse proxy routes `/` vs `/api`.
- Monitoring: CloudWatch agent + alarms on `/health` failure, Telegram admin alerts for critical jobs.

## Development Environment

### Prerequisites

- Python 3.11, Node.js >= 20, Docker 24, Compose 2.20
- Access to OpenAI/OpenRouter + Telegram tokens, Postgres credentials

### Setup Commands

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -r requirements-dev.txt
cd frontend && npm install
cd infrastructure && docker-compose up -d
```

## Architecture Decision Records (ADRs)

1. **Single-node deployment:** chosen for launch to minimize cost; scaling path is to move Milvus/Postgres to managed services if load increases.
2. **Compose orchestrator:** faster iteration than ECS/Kubernetes, matches developer workflow.
3. **Milvus embeddings:** reuse existing data flow; no re-architecture needed pre-launch.
4. **Telegram alerts retained:** avoids new notification channels until service proves value.

---
_Generated 2025-11-11 for young_
