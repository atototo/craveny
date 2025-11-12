# Frontend Architecture (Next.js Dashboard)

## Executive Summary
Next.js 15 App Router dashboard delivering investor insights, admin tooling, and AB-test configuration. Relies on FastAPI REST endpoints for data, React Query for caching, and Tailwind for UI system.

## Technology Stack
- Next.js 15.1.4, React 19, TypeScript 5
- Tailwind CSS, lucide-react icons, Recharts visualizations
- React Query for data fetching/state, AuthContext for session state

## Architecture Pattern
Hybrid SSR/CSR. Layout defined in `frontend/app/layout.tsx`, with page segments for predictions, stocks, admin, AB-test, login. ProtectedRoute wraps pages requiring authentication.

## Data Architecture
- Remote DTOs consumed from backend (see `docs/api-contracts-frontend.md`).
- View models tracked via React Query cache keys and local context (see `docs/data-models-frontend.md`).

## Component Overview
- Shared components catalogued in `docs/ui-components-frontend.md`.
- Feature directories under `app/` host page-specific components + loaders.
- `contexts/AuthContext.tsx` stores JWT + user metadata.

## Source Tree Snapshot
See `docs/source-tree-analysis.md` for annotated tree (frontend section). Critical folders: `app/components`, `app/contexts`, `app/(feature)` directories.

## Development Workflow
Refer to `docs/development-guide.md` for Node/npm requirements, `npm run dev`, `npm run build`, `npm run lint`.

## Deployment Architecture
- Build via `npm run build` -> `.next`. Serve with `next start -p 3000` behind reverse proxy or export static bundle.
- Environment variable `NEXT_PUBLIC_API_BASE` configures API origin when frontend deployed separately.
- Deployment guidance detailed in `docs/deployment-configuration.md`.

## Testing Strategy
- ESLint 9 currently enforced; add Jest/Playwright tests for components.
- Use React Testing Library for forms/charts once coverage is needed.
