# Deployment Configuration

## Runtime Targets
- **Single-node**: AWS EC2 `t3.small` (per README). Runs Docker Compose stack + uvicorn + Next.js build.
- **Containers**: Compose services defined for Postgres, Redis, Milvus, MinIO, etcd. Backend container definition exists but commented—enable for immutable deployments.
- **Scaling Path**: Move Milvus to dedicated instance or managed vector DB if memory pressure >4GB.

## Build Artifacts
- Backend: build Docker image from `infrastructure/Dockerfile` (copy backend/, install reqs, run uvicorn).
- Frontend: `npm run build` → `.next` output. Serve via Next.js server (`next start`) or export static assets behind nginx / FastAPI StaticFiles.

## Environment Variables
| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | GPT-4o + embeddings |
| `OPENROUTER_API_KEY` | OpenRouter LLM 호출 시 사용 |
| `TELEGRAM_BOT_TOKEN` | Notification bot |
| `POSTGRES_*` | DB credentials |
| `REDIS_URL` | Celery broker/cache |
| `MILVUS_HOST/PORT` | Vector DB endpoint |
| `NEXT_PUBLIC_API_BASE` | Frontend fetch base URL |

Store secrets in AWS SSM or Secrets Manager; inject via `.env` on host or Compose `.env` file.

## CI/CD Recommendations
- Add GitHub Action:
  - Job 1: `pip install -r requirements-dev.txt && pytest && mypy`.
  - Job 2: `cd frontend && npm install && npm run lint && npm run build`.
  - Job 3: Build Docker images + push to ECR, trigger remote deployment (SSH or SSM RunCommand).

## Deployment Steps (Manual)
1. `git pull` latest main on EC2.
2. Update `.env` with production secrets.
3. `cd infrastructure && docker-compose pull && docker-compose up -d` (ensures data services up-to-date).
4. Build frontend: `cd frontend && npm install && npm run build`.
5. Start backend (systemd or `pm2`): `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4`.
6. Serve frontend via `next start -p 3000` or export static bundle to nginx.
7. Put nginx/Traefik in front to terminate TLS and route `/api` → backend, `/` → frontend.

## Observability & Ops
- Health endpoints: `/health` (backend), Compose healthchecks for DB/Redis/Milvus.
- Add monitoring: CloudWatch agent or Prometheus exporters. Track scheduler jobs via logs (`backend.log`, `backend_new.log`).
- Backups: snapshot Postgres volume (`postgres_data`) and MinIO buckets (Milvus) regularly.
