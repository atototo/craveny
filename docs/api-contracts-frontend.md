# Frontend → Backend Contract Map (Quick Scan)

_Quick inference from route folders under `frontend/app/` and shared hooks (no source parsing)._  Use this to align API responses with dashboard expectations before deployment.

| UI Surface | Expected Backend Route | Data Needed |
| --- | --- | --- |
| `/` (dashboard `page.tsx`) | `/api/dashboard`, `/api/statistics` | Summary KPIs, model win rate, alert counts |
| `/predictions` | `/api/predictions`, `/api/news` | Latest AI predictions + supporting articles |
| `/stocks/[symbol]` | `/api/stocks`, `/api/stock_management` | Stock metadata, overrides, realtime price snapshots |
| `/admin` | `/api/users`, `/api/models`, `/api/ab-test` | User provisioning, model registry, experiment knobs |
| `/ab-test` & `/ab-config` | `/api/ab-test`, `/api/evaluations` | Variant definitions + evaluation stats |
| `/login` | `/api/auth` | Token issuance, refresh |
| `/models` | `/api/models`, `/api/evaluations` | Prompt templates, evaluation history |

**HTTP Client Layer**
- React Query hooks expected under `frontend/app/contexts` & `app/components` (e.g., `PredictionStatusBanner`).
- Ensure each hook handles 401 → redirect via `ProtectedRoute`.

**Payload Expectations**
- `predictions` list: `symbol`, `direction`, `confidence`, `reasoning` (align with `backend/api/prediction.py`).
- `statistics` summary: win-rate %, coverage %, active alerts.
- `ab-test` config: variant key, allocation %, prompt diff summary.

Before production deploy, verify backend OpenAPI spec or manual docs match the above contracts to avoid runtime 500s.
