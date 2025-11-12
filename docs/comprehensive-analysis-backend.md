# Backend Quick Scan Summary

## Entry Points & Process Model
- `backend/main.py` registers FastAPI app and routers under `/api`.
- `backend/scheduler.py` + `backend/scheduler/` hold APScheduler jobs (news crawling, evaluation refresh).
- CLI entry defined in `pyproject.toml` (`craveny = backend.main:main`).

## Configuration Surfaces
- `.env` template at repo root feeds `backend/config.py` via `pydantic-settings`.
- Secrets for OpenAI, Telegram, Postgres, Redis, Milvus referenced in `requirements.txt` modules.

## Authentication & Security
- `backend/auth/` contains JWT helpers, bcrypt password hashing, role enforcement decorators.
- API modules import shared dependencies from `backend/auth/dependencies.py` (implicit from filenames).

## Shared Libraries
- `backend/utils/` + `backend/services/` contain cross-cutting helpers (logging, caching, feature flags).
- `backend/notifications/` integrates Telegram + future webhook support.

## Async & Eventing
- Celery worker modules under `backend/services` publish long-running jobs (news ingestion, evaluation batch).
- Redis declared in `requirements.txt` and Compose for broker/cache.

## Testing & Quality Gates
- `tests/` + `backend/tests/` (unit + integration) with pytest + coverage (configured in `pyproject.toml`).
- CI hooks implied by `.github/workflows`? (not present yet) → add GitHub Actions for lint/test before deployment.

## Deployment Considerations
- Designed to run on Docker (compose file exposes Postgres/Milvus/Redis). Backend container block already defined but commented.
- Production target per README: single EC2 (t3.small) with Docker Compose and background scheduler.

## Outstanding Risks
- Need health/metrics endpoint for scheduler jobs.
- Ensure OpenAI + Telegram secrets injected in ECS/Compose before scaling.
- Evaluate Milvus resource usage on t3.small; may require separate instance or managed vector DB for production load.
