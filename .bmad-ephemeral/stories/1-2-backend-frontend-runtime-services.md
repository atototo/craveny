# Story 1.2: Backend/Frontend 런타임 서비스 기동

Status: drafted

## Story

As a **system operator**,
I want **FastAPI backend and Next.js frontend services to run in Docker Compose environment**,
so that **the application runtime stack is fully operational alongside the data infrastructure**.

## Acceptance Criteria

```
Given docker-compose 가 데이터 스택을 실행 중일 때
When backend/ frontend 서비스를 빌드 및 실행하면
Then http://<host>:8000/health 와 http://<host>:3030 이 모두 200 응답을 제공한다
```

### Functional Requirements

1. Backend service builds successfully and starts with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2. Frontend service builds successfully and starts with `npm run start` on port 3030
3. Both services respond with 200 status on their health/root endpoints
4. Services integrate properly with existing data stack (postgres, redis, milvus)

### Integration Requirements

5. Backend connects to Postgres, Redis, and Milvus using environment variables
6. Frontend connects to backend API using NEXT_PUBLIC_API_URL
7. Docker Compose orchestrates all services with proper dependency order
8. All existing data stack services remain healthy and operational

### Quality Requirements

9. Both Dockerfiles follow multi-stage build patterns for optimization
10. Services include proper healthcheck configurations
11. Environment variables are properly sourced from .env file
12. Services restart automatically on failure (restart: unless-stopped)

## Tasks / Subtasks

- [ ] Task 1: Fix Backend Dockerfile context and paths (AC: 1, 4, 5)
  - [ ] Update requirements.txt COPY path to work with parent context
  - [ ] Verify COPY paths for backend/ and scripts/ directories
  - [ ] Add healthcheck configuration for /health endpoint
  - [ ] Test backend build: `docker-compose build backend`

- [ ] Task 2: Fix Frontend Dockerfile context and paths (AC: 2, 6)
  - [ ] Update package.json/package-lock.json COPY paths for parent context
  - [ ] Verify all frontend/ COPY operations
  - [ ] Confirm PORT environment variable is 3030 throughout
  - [ ] Add healthcheck configuration for root endpoint
  - [ ] Test frontend build: `docker-compose build frontend`

- [ ] Task 3: Verify docker-compose.yml integration (AC: 3, 7, 8)
  - [ ] Confirm backend service configuration (ports, env_file, depends_on)
  - [ ] Confirm frontend service configuration (ports, env, depends_on)
  - [ ] Verify .env file exists with required variables
  - [ ] Test full stack: `docker-compose up -d`

- [ ] Task 4: Validate service health and integration (AC: 3, 5, 6, 8)
  - [ ] Test backend health: `curl http://localhost:8000/health`
  - [ ] Test frontend access: `curl http://localhost:3030`
  - [ ] Verify backend can connect to Postgres/Redis/Milvus
  - [ ] Verify frontend can call backend API
  - [ ] Check all service logs for errors
  - [ ] Confirm all containers are healthy: `docker-compose ps`

## Dev Notes

### Architecture Patterns

- **Multi-stage Docker builds**: Optimization pattern used in both Dockerfiles
- **Docker Compose orchestration**: Service dependency management with depends_on
- **Environment variable injection**: .env file shared across services via env_file
- **Health checking**: Container health validation for orchestration reliability

### Source Tree Components to Touch

**Primary Files:**
- `backend/Dockerfile` - Backend container build configuration
- `frontend/Dockerfile` - Frontend container build configuration
- `infrastructure/docker-compose.yml` - Service orchestration (already configured)
- `.env` - Environment variables (verify exists)

**Dependencies:**
- `requirements.txt` - Backend Python dependencies (project root)
- `backend/main.py` - FastAPI application entry point with /health endpoint
- `frontend/package.json` - Frontend npm configuration
- `frontend/next.config.js` - Next.js configuration

### Testing Standards Summary

1. **Build Testing**: Both services must build without errors
2. **Runtime Testing**: Services must start and respond to health checks
3. **Integration Testing**: Services must connect to data stack and each other
4. **Regression Testing**: Existing data stack services must remain healthy

### Project Structure Notes

**Current Context (from docker-compose.yml):**
```yaml
backend:
  build:
    context: ..          # Parent directory (project root)
    dockerfile: backend/Dockerfile

frontend:
  build:
    context: ..          # Parent directory (project root)
    dockerfile: frontend/Dockerfile
```

**File Locations:**
- `requirements.txt` is at project root (not backend/)
- `backend/` directory contains backend code
- `frontend/` directory contains frontend code
- `scripts/` directory at project root (used by backend)

**Known Issues from Epic:**
1. Backend Dockerfile COPY paths assume backend/ context but compose uses parent context
2. Frontend Dockerfile COPY paths assume frontend/ context but compose uses parent context
3. Healthcheck configurations missing from both Dockerfiles
4. Need to verify .env file exists with all required variables

### References

- [Source: docs/epics.md#Story 1.2: Backend/Frontend 런타임 서비스 기동]
- [Source: infrastructure/docker-compose.yml#backend service (lines 90-103)]
- [Source: infrastructure/docker-compose.yml#frontend service (lines 105-120)]
- [Source: backend/Dockerfile (lines 1-25)]
- [Source: frontend/Dockerfile (lines 1-27)]

## Dev Agent Record

### Context Reference

<!-- Path(s) to story context XML will be added here by context workflow -->

### Agent Model Used

claude-sonnet-4-5-20250929

### Debug Log References

### Completion Notes List

### File List

### Change Log
