# Infrastructure Architecture (Docker Compose Stack)

## Executive Summary
Single-node container stack bootstrapped via `infrastructure/docker-compose.yml`, provisioning PostgreSQL, Redis, Milvus (with MinIO + etcd dependencies), and optional backend container. Designed for cost-efficient EC2 deployment.

## Technology Stack
- Docker 24+, Compose v3.8
- Official images: postgres:13-alpine, redis:7-alpine, milvusdb/milvus:v2.3.0, minio/minio, quay.io/coreos/etcd
- Optional backend Dockerfile for FastAPI app

## Architecture Pattern
Data-services-first: Compose file lifts persistent dependencies; backend/frontend run as separate processes or containers pointing to same bridge network.

## Data & Storage
- Volumes: `postgres_data`, `milvus_data`, `etcd_data`, `minio_data`
- Secrets via environment variables (defaulted; replace in production)

## Networking
- Exposed ports: 5432 (Postgres), 6380→6379 (Redis), 19530/9091 (Milvus), 9000 (MinIO)
- Recommend security groups restricting direct exposure; route traffic through reverse proxy/SSH tunnel.

## Deployment Workflow
1. Provision EC2 + security groups.
2. Copy repo, populate `.env` with secure values.
3. `cd infrastructure && docker-compose up -d`.
4. Start backend container (uncomment service) or run uvicorn on host.
5. Build/start frontend; optionally containerize and attach to same Docker network.

## Observability / Ops
- Built-in healthchecks for Postgres, Redis, Milvus.
- Add CloudWatch/Prometheus exporters for CPU/memory.
- Snapshot volumes regularly; store MinIO data in S3 for DR.

## Integration Touchpoints
- Backend container depends_on Postgres/Redis/Milvus.
- Celery + APScheduler rely on Redis uptime.
- Telegram + OpenAI secrets injected via `.env` shared between host processes and Compose stack.
