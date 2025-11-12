# Story 1.1: Provision t3.small host & bring up Compose stack

Status: ready-for-dev

## Story

As a solo infrastructure owner,
I want to provision the EC2 t3.small host and bring up the full Docker Compose data stack,
so that every backend, frontend, and automation service can attach to stable Postgres/Redis/Milvus foundations for 24/7 use anywhere.

## Acceptance Criteria

1. **Compose stack bootstraps successfully**  
   Given Ubuntu 22.04 on the t3.small host with Docker 24.x, Compose ≥2.20, and `.env` populated with production secrets, when `cd infrastructure && docker compose up -d` runs, then Postgres, Redis, Milvus, MinIO, and etcd containers all reach `healthy` status without manual retries and expose ports 5432/6380/19530/9091/9000.  
   _Source: docs/epics.md#epic-1-infra--deployment-foundation, docs/deployment-configuration.md#deployment-steps-manual_

2. **Idempotent bring-up with persistent volumes**  
   Given the stack is already running, when `docker compose down && docker compose up -d` or targeted restarts execute, then volumes (`postgres_data`, `milvus_data`, `minio_data`, `etcd_data`) remount cleanly and container healthchecks (`pg_isready`, `redis-cli ping`, Milvus `/healthz`) still pass without reconfiguration.  
   _Source: infrastructure/docker-compose.yml, docs/architecture-infrastructure.md#data--storage_

3. **Host prerequisites and access hardening verified**  
   Given the EC2 host has newly provisioned security groups and swap configuration, when diagnostics (`docker --version`, `docker compose version`, `.env` validation via `docker compose config | grep POSTGRES_`) and firewall checks run, then outputs confirm Docker/Compose versions, secrets sourced from `.env`/SSM (no defaults), and only 80/443 (plus restricted SSH) are exposed externally.  
   _Source: docs/deployment-infrastructure.md#target-environment, docs/architecture.md#deployment-architecture_

## Tasks / Subtasks

- [ ] **Prepare host prerequisites** (AC: #3)  
  - [ ] Apply OS updates, install Docker 24.x + Compose ≥2.20, configure ≥8 GB swap as recommended for t3.small + Milvus.  
  - [ ] Harden security groups/UFW so only 80/443 (and admin SSH) are reachable from the internet; keep Postgres/Redis/Milvus internal.  
  - [ ] Copy `.env.example` → `.env`, fill OPENAI/OPENROUTER/TELEGRAM/DB credentials from SSM or Parameter Store, then confirm with `docker compose config` that overrides take effect.
- [ ] **Bring up Compose data stack** (AC: #1)  
  - [ ] Run `docker compose pull` to fetch Postgres/Redis/Milvus/MinIO/etcd images.  
  - [ ] Execute `docker compose up -d` and watch `docker compose ps` until every container is `healthy`.  
  - [ ] Capture evidence (ports, container IDs, healthcheck output) for docs/runbook updates.
- [ ] **Validate persistence and idempotency** (AC: #2)  
  - [ ] Restart critical services (`docker compose restart postgres redis milvus`) and ensure health status returns to `healthy` within 2 minutes.  
  - [ ] Run smoke commands: `psql -h localhost -U $POSTGRES_USER -c '\l'`, `redis-cli -p 6380 ping`, `curl http://localhost:9091/healthz`.  
  - [ ] Document troubleshooting guidance (common failure logs, disk usage, volume paths) in deployment docs for reuse.

## Dev Notes

### Requirements Context Summary

- Epic 1 defines this story as the gating deliverable so later backend/frontend runtime work can reuse a stable Compose stack without bespoke setup. [Source: docs/epics.md#epic-1-infra--deployment-foundation]
- The PRD’s success criteria demand 24/7 availability on a single economical node, so provisioning plus deterministic container healthchecks determine whether investors can access the service anywhere. [Source: docs/PRD.md#success-criteria]
- Deployment configuration instructions emphasize Docker 24+/Compose 2.20 and `.env`-driven secrets, making host prerequisite verification part of the acceptance requirements. [Source: docs/deployment-configuration.md#deployment-steps-manual]

### Architecture & Constraints

- `infrastructure/docker-compose.yml` already enumerates Postgres, Redis, Milvus, MinIO, and etcd with healthchecks—modifications should stick to secrets/overrides via `.env` to avoid drift. [Source: infrastructure/docker-compose.yml]
- Architecture guidance fixes the hosting model at EC2 t3.small (Ubuntu 22.04) with Docker + Compose orchestrating data services before app runtimes attach, so any automation must preserve that layering. [Source: docs/architecture.md#deployment-architecture]
- Deployment infrastructure notes require restricted ingress (80/443 only), swap configuration, and health monitoring via `/health`, CloudWatch, or similar even for this foundational story. [Source: docs/deployment-infrastructure.md#target-environment]

### Project Structure Notes

- No predecessor story exists—this is the first implementation item recorded in sprint status—so there are no Dev Agent learnings yet. [Source: .bmad-ephemeral/sprint-status.yaml]
- Infrastructure work should remain within `infrastructure/`, `.env`, and docs, keeping `backend/` and `frontend/` untouched so future stories can focus on runtime enablement. [Source: README.md#📁-프로젝트-구조]
- Compose persistence relies on volumes `postgres_data`, `milvus_data`, `etcd_data`, and `minio_data`; ensure EC2 file permissions and disk allocation fit these mounts to prevent permission errors during restarts. [Source: infrastructure/docker-compose.yml]

### Testing & Validation

- Use `docker compose ps` plus container healthchecks (`pg_isready`, `redis-cli ping`, `curl http://localhost:9091/healthz`) to confirm each service transitions to healthy status. [Source: docs/deployment-configuration.md#deployment-steps-manual]
- After initial launch, run `docker compose restart` for key services and re-run smoke commands to prove idempotency and volume persistence. [Source: infrastructure/docker-compose.yml]
- Record verification steps and troubleshooting tips (logs under `docker compose logs -f`) in docs/runbook.md for reuse in later deployment automation stories. [Source: docs/deployment-configuration.md#observability--ops]

### Learnings from Previous Story

- First story in epic—no previous Dev Agent record exists; future stories should capture reusable interfaces and debt as they appear.

### References

- docs/epics.md#epic-1-infra--deployment-foundation  
- docs/PRD.md#success-criteria  
- docs/deployment-configuration.md#deployment-steps-manual  
- docs/deployment-infrastructure.md#target-environment  
- docs/architecture.md#deployment-architecture  
- README.md#📁-프로젝트-구조  
- infrastructure/docker-compose.yml  
- docs/deployment-configuration.md#observability--ops

## Dev Agent Record

### Context Reference

- .bmad-ephemeral/stories/1-1-provision-t3-small-host-bring-up-compose-stack.context.xml (generated 2025-11-12)

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

## Change Log

- 2025-11-11: Drafted story 1.1 based on Epic 1 infra objectives and deployment documentation.
