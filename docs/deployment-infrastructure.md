# Deployment & Infrastructure Notes (Quick Scan)

## Docker Compose Stack (`infrastructure/docker-compose.yml`)
| Service | Purpose | Ports | Persistence |
| --- | --- | --- | --- |
| `postgres` | Primary relational DB | 5432 | `postgres_data` volume |
| `redis` | Cache + Celery broker | 6380→6379 | ephemeral |
| `etcd` | Milvus metadata | 2379 | `etcd_data` |
| `minio` | Object store for Milvus | 9000 | `minio_data` |
| `milvus` | Vector DB for embeddings | 19530/9091 | `milvus_data` |
| (`backend`) | FastAPI app (commented) | 8000 | bind-mounted source |

## Target Environment
- README specifies AWS EC2 `t3.small` + Docker Compose runtime.
- Ensure host has 8GB swap or upgrade instance when running Milvus + FastAPI concurrently.

## Secrets & Env
- `.env` at repo root feeds database + API keys. Compose uses `${POSTGRES_*}` with defaults; override in production SSM/Parameter Store.
- MinIO root creds currently default (`minioadmin`). Rotate before exposure.

## Operational Checklist
1. Provision security groups: allow 80/443 (proxy), restrict DB/Redis/Milvus to VPC.
2. Install Docker 24+ and Compose 2.20+.
3. `cd infrastructure && docker-compose up -d` to bootstrap data services.
4. Start backend via uvicorn (host) or uncomment `backend` service + provide production-ready Dockerfile.
5. Frontend can be containerized separately or built into static assets served by FastAPI/nginx.

## Monitoring Hooks
- Compose lacks health dashboards; add Prometheus/Grafana or at minimum enable CloudWatch agent on EC2.
- Healthchecks defined for Postgres/Redis/Milvus but not forwarded to ALB. Consider ECS or systemd for auto-restart.
