# Integration Architecture

| From | To | Type | Details |
| --- | --- | --- | --- |
| Frontend (Next.js) | Backend (FastAPI) | REST over HTTPS | Routes from `frontend/app/*` call `/api/dashboard`, `/api/predictions`, `/api/stocks`, `/api/ab-test`, `/api/models`, `/api/auth`. Auth via JWT stored in `AuthContext`. |
| Backend (FastAPI) | PostgreSQL | SQLAlchemy ORM | Models under `backend/db/models/*.py`. Connection params drawn from `.env`. |
| Backend (FastAPI) | Redis | Cache + Celery broker | Configured in `requirements.txt`; used for APScheduler locks + Celery queues. |
| Backend (FastAPI) | Milvus + MinIO + etcd | Vector storage | `backend/db/milvus_client.py` persists embeddings referenced by news/prediction entities. |
| Backend (Schedulers/Crawlers) | External news/APIs | HTTP clients | Modules under `backend/crawlers/` call Naver/KRX/KIS endpoints before storing data. |
| Backend (Notifications) | Telegram Bot API | HTTPS | `backend/notifications/` pushes alerts using `python-telegram-bot`. |
| Infrastructure Compose | All services | Container networking | `docker-compose.yml` wires Postgres, Redis, Milvus, MinIO, etcd; backend container (optional) binds to same bridge network. |

**Auth Flow**
1. Frontend login posts to `/api/auth` → FastAPI issues JWT.
2. Token stored in context → appended to Authorization header for subsequent REST calls.
3. Backend enforces scopes via `backend/auth` dependencies; sensitive routes (`users`, `stock_management`, `ab-test`) require admin role.

**Data Flow**
- Crawlers ingest news → stored in Postgres (`news` table) + embeddings in Milvus.
- Scheduler triggers `prediction` jobs; results saved to Postgres (`prediction`, `daily_performance`).
- API layer exposes aggregated stats consumed by frontend charts.
- Notifications service publishes high-signal predictions to Telegram.

**Operational Notes**
- Compose healthchecks keep data services alive; backend health endpoint (`/health`) should be wired to external monitoring.
- For production, frontends and API should sit behind reverse proxy (nginx/ALB) with TLS termination.
