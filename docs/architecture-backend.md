# Backend Architecture (FastAPI Service)

## Executive Summary
FastAPI-based API and scheduler service delivering AI-driven stock insights, powered by PostgreSQL for relational data, Milvus for embeddings, Redis for caching/queues, and Celery/APScheduler for async workloads.

## Technology Stack
- Python 3.11, FastAPI, Uvicorn
- SQLAlchemy ORM, Alembic-style migrations (custom scripts)
- Celery + Redis, APScheduler
- OpenAI GPT-4o + text-embedding-3-small

## Architecture Pattern
Service-oriented API with background workers. Routers live in `backend/api`, share dependencies through `backend/config.py`, and dispatch to services/repositories. Scheduler triggers crawlers and prediction batch jobs.

## Data Architecture
- Relational entities documented in `docs/data-models-backend.md` (users, stocks, news, predictions, evaluations, AB tests).
- Vector embeddings stored via `backend/db/milvus_client.py` referencing Milvus + MinIO.
- Redis caches hot metrics + Celery task state.

## API Design
See `docs/api-contracts-backend.md` for router inventory. All endpoints live under `/api/*` with JWT protection except `/health`.

## Component Overview
- `api/`: REST routers per domain
- `auth/`: JWT + bcrypt utilities
- `crawlers/`: data ingestion
- `llm/`: GPT prompt builders
- `scheduler/`: APScheduler job registry
- `notifications/`: Telegram + alert fan-out

## Source Tree Snapshot
Summarized in `docs/source-tree-analysis.md` (backend section). Critical folders: `api`, `db`, `scheduler`, `services`, `utils`.

## Development Workflow
Refer to `docs/development-guide.md` for env setup, scripts, and quality gates. Key commands: `uvicorn backend.main:app`, `pytest`, `black`, `mypy`.

## Deployment Architecture
Runs alongside Compose data stack. Backend container definition lives in `infrastructure/docker-compose.yml` (currently commented). For production, package as Docker image and run behind nginx/ALB. See `docs/deployment-configuration.md`.

## Testing Strategy
- Pytest suites under `tests/`
- Coverage configured via `pyproject.toml`
- Linting + type checking enforced locally; add CI job per deployment doc.
