# Frontend View Models & State Surfaces (Quick Scan)

## Typed Models / DTOs
- `frontend/app/models/page.tsx` imports shared interfaces for investor personas + evaluation metrics.
- Context-specific hooks likely reside under `frontend/app/contexts/AuthContext.tsx` (provides `user`, `token`, `isAdmin`).

## React Query Cache Keys (inferred)
| Feature | Query Key Convention | Backend Dependency |
| --- | --- | --- |
| Predictions stream | `['predictions', symbol?]` | `/api/predictions` |
| Stock detail | `['stocks', symbol]` | `/api/stocks/{symbol}` |
| Evaluations | `['evaluations']` | `/api/evaluations` |
| AB testing | `['ab-test', variant]` | `/api/ab-test` |

## State Management
- `@tanstack/react-query` handles remote state; local auth state stored via `AuthContext` with `ProtectedRoute` gating.
- Component-level state (forms, filters) scoped inside page components (e.g., `ab-config`, `stocks`).

## Derived View Objects
- KPI cards combine `/api/statistics` payload with `PredictionStatusBanner` props.
- Charts under `components/evaluations/` expect normalized time-series arrays (timestamp, metric, label).

Add Zod/TypeScript interfaces per API contract before production to catch backend schema drift.
