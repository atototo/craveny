# Component Inventory (Cross-Part)

## Backend Components
| Component | Location | Notes |
| --- | --- | --- |
| API Routers | `backend/api/*.py` | Auth, stocks, predictions, evaluations, AB test, dashboard, news |
| Auth Services | `backend/auth/` | JWT issuance, password hashing, role checks |
| Crawlers | `backend/crawlers/` | Naver/KIS/KRX ingest jobs |
| Scheduler Jobs | `backend/scheduler/` | APScheduler job definitions |
| Notification Workers | `backend/notifications/` | Telegram + other alert channels |
| Data Access Layer | `backend/db/models`, `backend/db/repositories` | SQLAlchemy models & repos |

## Frontend Components
| Component | Location | Notes |
| --- | --- | --- |
| LayoutWrapper | `frontend/app/components/LayoutWrapper.tsx` | Shell for navigation + auth |
| Navigation | `frontend/app/components/Navigation.tsx` | Menu rendering (admin vs default) |
| ProtectedRoute | `frontend/app/components/ProtectedRoute.tsx` | Auth guard for routes |
| PredictionStatusBanner | `frontend/app/components/PredictionStatusBanner.tsx` | KPI indicator |
| NewsImpact | `frontend/app/components/NewsImpact.tsx` | Highlights AI insights per stock |
| MetricBreakdownChart | `frontend/app/components/evaluations/MetricBreakdownChart.tsx` | Renders chart via Recharts |
| StockPerformanceTable | `frontend/app/components/evaluations/StockPerformanceTable.tsx` | Tabular analytics |

## Infrastructure Components
| Component | Location | Notes |
| --- | --- | --- |
| PostgreSQL Service | `infrastructure/docker-compose.yml` | Primary DB; persists to `postgres_data` |
| Redis Service | same | Broker/cache for Celery + scheduler |
| Milvus Stack | milvus + etcd + MinIO | Handles embeddings + metadata |
| Backend Container (optional) | commented service | Mounts backend code for uvicorn |

Refer to `docs/ui-components-frontend.md` and `docs/api-contracts-backend.md` for deeper per-component notes.
