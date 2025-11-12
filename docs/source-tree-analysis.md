# Source Tree Analysis (Quick Scan)

```
craveny/
├── backend/                      # FastAPI service + schedulers (Part: backend)
│   ├── api/                      # Router modules (auth, stocks, prediction, etc.)
│   ├── auth/                     # JWT helpers, bcrypt hashing, dependency injection
│   ├── crawlers/                 # News collectors / ETL jobs
│   ├── db/                       # SQLAlchemy models, migrations, Milvus client
│   ├── llm/                      # GPT-4o integration + prompt logic
│   ├── notifications/            # Telegram + alert publishing
│   ├── scheduler/                # APScheduler job registry
│   ├── services/, utils/         # Business logic + shared helpers
│   └── main.py                   # FastAPI app entry, router registration
│
├── frontend/                     # Next.js 15 dashboard (Part: frontend)
│   ├── app/
│   │   ├── components/           # Shared UI widgets (layout, charts, banners)
│   │   ├── contexts/             # Auth context for ProtectedRoute
│   │   ├── predictions/, stocks/ # Feature routes; fetch backend data via React Query
│   │   ├── admin/, ab-test/      # Operator tooling + experimentation UIs
│   │   └── login/                # Auth entrypoint
│   ├── next.config.ts            # Build/runtime config (image domains, rewrites)
│   └── package.json              # Scripts + dependency manifest
│
├── infrastructure/               # Deployment definitions (Part: infrastructure)
│   ├── docker-compose.yml        # Postgres, Redis, Milvus, MinIO, etcd stack
│   └── Dockerfile(s)             # Backend container build context (commented service)
│
├── docs/                         # Planning + generated documentation output
│   ├── archive/                  # Historical PRD/architecture artifacts
│   └── *.md                      # Current quick-scan deliverables (API, data, infra)
│
├── scripts/                      # DB/Milvus init helpers, operational scripts
├── data/                         # Local storage for crawled datasets & embeddings
├── tests/                        # Pytest suites targeting backend modules
├── requirements*.txt, pyproject  # Python dependencies & tooling config
└── README.md, RUN_GUIDE.md       # High-level overview + manual run instructions
```

**Integration Touchpoints**
- Frontend routes call FastAPI endpoints under `backend/api/*` (see `docs/api-contracts-frontend.md`).
- Backend relies on data services started via `infrastructure/docker-compose.yml` (Postgres, Redis, Milvus).
- Shared `.env` at repo root configures both backend and infrastructure stack.

Critical folders tracked: backend/api, backend/db, backend/scheduler, frontend/app/components, frontend/app/contexts, infrastructure/docker-compose.yml, docs/archive/*.
