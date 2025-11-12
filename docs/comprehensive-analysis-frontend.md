# Frontend Quick Scan Summary

## Build & Tooling
- `package.json` pins Next.js 15.1.4 + React 19, Node >=20.
- Scripts: `npm run dev` (port 3030), `npm run build`, `npm run start`, `npm run lint`.
- TypeScript + ESLint 9 + Tailwind pipeline defined (postcss/autoprefixer).

## Routing Layout
- App Router root `frontend/app/layout.tsx` wraps `Navigation`, `ProtectedRoute`, and global styles.
- Segments: `predictions`, `stocks`, `models`, `admin`, `ab-config`, `ab-test`, `login`.

## Auth Flow
- `contexts/AuthContext.tsx` manages tokens client-side; `ProtectedRoute` reads context to gate pages.
- Login route likely posts to `/api/auth` (see contract map) and stores token in context/local storage.

## Data Access Layer
- React Query ensures caching/refetch policies per feature.
- Use `fetch` or Axios wrapper? (none detected). Standardize a shared client to centralize base URL + headers before deployment.

## Deployment Notes
- Next.js 15 supports hybrid rendering; ensure server runtime set to `nodejs` when deploying behind Docker/EC2.
- Production build should serve via `next start` behind reverse proxy (nginx or same FastAPI container via `proxy_pass`).

## Observed Gaps
- No `.env.local.example` for frontend—document required NEXT_PUBLIC vars (API base URL, telemetry toggles).
- Add Lighthouse/perf budget before public launch.
