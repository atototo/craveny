## Project Documentation Index

### Project Overview
- **Type:** Multi-part repository with 3 parts (backend, frontend, infrastructure)
- **Primary Languages:** Python 3.11 + TypeScript/React
- **Architecture:** FastAPI service + Next.js dashboard + Docker Compose data stack

### Quick Reference by Part
#### Backend API (backend)
- **Tech Stack:** FastAPI, SQLAlchemy, Celery, APScheduler
- **Entry Point:** `backend/main.py`
- **Pattern:** API + async workers

#### Web Dashboard (frontend)
- **Tech Stack:** Next.js 15, React 19, Tailwind, React Query
- **Root:** `frontend/`
- **Pattern:** App Router (hybrid SSR/CSR) with protected routes

#### Infrastructure Stack (infrastructure)
- **Tech Stack:** Docker Compose 3.8 (Postgres, Redis, Milvus, MinIO, etcd)
- **Root:** `infrastructure/`
- **Pattern:** Data-services-first stack for EC2 deployment

### Generated Documentation
- [Project Overview](./project-overview.md)
- [Architecture – Backend](./architecture-backend.md)
- [Architecture – Frontend](./architecture-frontend.md)
- [Architecture – Infrastructure](./architecture-infrastructure.md)
- [API Contracts – Backend](./api-contracts-backend.md)
- [API Contracts – Frontend](./api-contracts-frontend.md)
- [Data Models – Backend](./data-models-backend.md)
- [Data Models – Frontend](./data-models-frontend.md)
- [UI Components – Frontend](./ui-components-frontend.md)
- [Component Inventory (Cross-Part)](./component-inventory.md)
- [Source Tree Analysis](./source-tree-analysis.md)
- [Integration Architecture](./integration-architecture.md)
- [Development Guide](./development-guide.md)
- [Deployment Configuration](./deployment-configuration.md)
- [Contribution Guidelines](./contribution-guidelines.md)
- [Infrastructure Notes](./deployment-infrastructure.md)
- [Project Parts Metadata](./project-parts.json)

### Existing Documentation (Legacy / Reference)
- [API_MIGRATION_EPIC3.md](./API_MIGRATION_EPIC3.md) – earlier epic write-up
- [CRAWLING_STRATEGY.md](./CRAWLING_STRATEGY.md) – crawler design notes
- [DASHBOARD_UX_DESIGN.md](./DASHBOARD_UX_DESIGN.md) – historical UX study
- [MULTI_MODEL_DESIGN.md](./MULTI_MODEL_DESIGN.md) – multi-model concept doc
- [MULTI_MODEL_IMPLEMENTATION.md](./MULTI_MODEL_IMPLEMENTATION.md) – implementation notes
- [pm-checklist-results.md](./pm-checklist-results.md) – PM validation log
- [REDDIT_DESIGN_COMPARISON.md](./REDDIT_DESIGN_COMPARISON.md)
- [REDDIT_INTEGRATION_DESIGN.md](./REDDIT_INTEGRATION_DESIGN.md)
- [REDDIT_INTEGRATION_SUMMARY.md](./REDDIT_INTEGRATION_SUMMARY.md)
- [sprint-change-proposal-2025-11-02.md](./sprint-change-proposal-2025-11-02.md)
- [STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md](./STOCK_ANALYSIS_REPORT_UPDATE_SYSTEM_ANALYSIS.md)
- [TOKEN_ARCHITECTURE.md](./TOKEN_ARCHITECTURE.md)

### Getting Started
1. Review [Development Guide](./development-guide.md) to install dependencies, start Docker Compose services, and run backend/frontend locally.
2. Use [Deployment Configuration](./deployment-configuration.md) + [deployment-infrastructure.md](./deployment-infrastructure.md) to provision the EC2/Compose stack.
3. Follow [Integration Architecture](./integration-architecture.md) to wire frontend → backend → data services and configure env vars.
4. Ready for planning? Run the next workflow (`prd`) with these docs as context per `docs/bmm-workflow-status.yaml`.
