# Development Guide

## Prerequisites
- Python 3.11 (see `pyproject.toml` target + `requirements.txt`)
- Node.js >= 20 / npm >= 10 for Next.js frontend
- Docker 24+ / Compose 2.20+ for local data services (Postgres, Redis, Milvus stack)
- OpenAI API key + Telegram bot token for end-to-end flows

## Environment Setup
1. Copy `.env.example` → `.env` at repo root and populate OpenAI/Telegram/Postgres secrets.
2. Create Python venv:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. Install frontend deps:
   ```bash
   cd frontend
   npm install
   ```
4. Start infra services (Postgres, Redis, Milvus, etc.):
   ```bash
   cd infrastructure
   docker-compose up -d
   ```

## Running the Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
- Scheduler jobs live in `backend/scheduler/`; run `python backend/scheduler.py` if you need standalone workers.
- Celery workers can be launched via `celery -A backend.services.worker worker -l info` (module path inferred from structure).

## Running the Frontend
```bash
cd frontend
npm run dev   # http://localhost:3030
```
Set `NEXT_PUBLIC_API_BASE` (add to `.env.local`) if proxy differs from default `/api`.

## Database & Vector Stores
- Initialize Postgres tables: `python scripts/init_db.py`
- Initialize Milvus collections: `python scripts/init_milvus.py`
- Cached data written under `data/`

## Testing & Quality
```bash
pytest                          # backend tests
pytest --cov=backend            # coverage report
black backend/ tests/
isort backend/ tests/
flake8 backend/ tests/
mypy backend/
```
Frontend linting: `npm run lint`; add `npm run test` once component tests exist.

## Common Tasks
- Add API endpoint: create module in `backend/api/` + register router in `backend/main.py`.
- Add DB model: define SQLAlchemy class in `backend/db/models/` + migration script under `backend/db/migrations/`.
- Add dashboard page: create directory inside `frontend/app/` (App Router) and compose components.

Document any additional scripts in `scripts/` when adding automation so deployment runbooks stay current.
