# Backend API Contracts (Quick Scan)

_Source: filename patterns under `backend/api/` – quick scan (no code execution)._  Each module maps to a FastAPI router registered under `/api`. Use this inventory to confirm which routes need authentication or monitoring before deployment.

| Module | Likely Path Prefix | Primary Responsibility | Notes |
| --- | --- | --- | --- |
| `health.py` | `/health` | Liveness/readiness checks for container and scheduler | Keep exposed for uptime monitors |
| `auth.py` | `/auth` | Login/token refresh & password reset flows | Depends on `backend/auth` and JWT helpers |
| `users.py` | `/users` | Admin CRUD for internal operators | Ensure RBAC middleware enabled |
| `stocks.py` | `/stocks` | Base stock metadata, supported tickers, reference data | Consumed by dashboard filters |
| `stock_management.py` | `/stocks/management` | Bulk upload & overrides for stock configs | Requires admin scope |
| `prediction.py` | `/predictions` | Latest AI prediction feed & historical lookups | Backed by Milvus + Postgres views |
| `evaluations.py` | `/evaluations` | Model evaluation snapshots & QA flags | Surfaces data for A/B dashboards |
| `statistics.py` | `/statistics` | Aggregated KPIs (win rate, Sharpe, etc.) | Feeds Recharts widgets |
| `dashboard.py` | `/dashboard` | Consolidated summary for landing dashboard | Typically batches multiple queries |
| `news.py` | `/news` | Crawled article listings & relevance tags | Clients pair with embeddings for RAG |
| `ab_test.py` | `/ab-test` | AB test config + decision endpoints | Works with `docs/ab_config` UI |
| `models.py` | `/models` | AI model registry metadata | Manage GPT prompts + weights |

**Integration Hooks**
- Routers share dependencies from `backend/config.py` (DB, Redis, OpenAI clients).
- Alerting endpoints publish events via Celery tasks (`backend/notifications`).
- To add new endpoints, scaffold a module in `backend/api/` and register a router in `backend/main.py`.

**Security Checklist**
- Confirm `auth.py` uses bcrypt + `python-jose` secrets from `.env`.
- Ensure `/health` is the only unauthenticated route exposed publicly.
