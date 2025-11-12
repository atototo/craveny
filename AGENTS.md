# Repository Guidelines

## Project Structure & Module Organization
`backend/` hosts the FastAPI service, split into `api`, `services`, `models`, and scheduler jobs; reusable utilities sit under `backend/core`. `frontend/` is a Next.js 15 dashboard (App Router) with shared UI in `frontend/src/components` and data hooks under `frontend/src/lib`. Long‑running infrastructure pieces (PostgreSQL, Redis, Milvus, MinIO) live in `infrastructure/` with Docker Compose manifests, while `scripts/` provides setup helpers such as `init_db.py` and `init_milvus.py`. Architecture notes reside in `docs/`, and automated checks belong in `tests/`, which is divided into `unit`, `integration`, and `e2e`.

## Build, Test, and Development Commands
- `cd infrastructure && docker-compose up -d` — boots all backing services for local work.
- `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload` — launches the API plus APScheduler jobs.
- `pytest` / `pytest --cov=backend --cov-report=html` — runs the backend test suite with optional coverage artifacts in `htmlcov/`.
- `cd frontend && npm install && npm run dev` — starts the dashboard on http://localhost:3030; use `npm run build` before deploying and `npm run lint` to mirror CI checks.

## Coding Style & Naming Conventions
Python code uses 4-space indentation, type hints, and docstrings for service boundaries; format with `black backend tests`, sync imports via `isort`, and keep `flake8` + `mypy` clean before opening a PR. Modules, packages, and environment variables follow `snake_case`/`UPPER_SNAKE_CASE`, while FastAPI routes expose kebab-case paths for consistency with the frontend. React components and files use `PascalCase.jsx/tsx`, hooks use `useSomething`, and maintain Tailwind utility order via `tailwind-merge`. Do not commit secret `.env` values; reference defaults from `.env.example`.

## Testing Guidelines
Prefer deterministic fixtures in `tests/conftest.py` and name Python tests `test_<unit>.py`. Unit tests belong in `tests/unit`, integration suites should stand up lightweight DB fakes, and end-to-end coverage should mock external LLM calls. Target ≥80 % coverage on critical packages (crawlers, prediction pipelines) and regenerate HTML reports before large refactors. For the frontend, add Vitest/Playwright suites under `frontend/tests` (mirroring route paths) and gate merges on `npm run lint` until UI tests mature.

## Commit & Pull Request Guidelines
Adopt the existing Conventional-Commit shorthand observed in history (`feat:`, `fix:`, `chore:`, `docs:`) followed by a concise, imperative clause (e.g., `feat: add telegram alert retries`). Each PR should include: a summary of scope and risk, linked issue or task ID, screenshots/CLI snippets for UI or ops changes, and a checklist confirming tests, lint, and infra migrations. Keep diffs narrowly scoped; open follow-up issues for deferred work rather than mixing concerns.

## Security & Configuration Tips
Store OpenAI, Telegram, and database credentials only in `.env` or your secret manager, never in tracked files. When touching Milvus or Redis configs, update the matching service definitions under `infrastructure/docker-compose.yml` and document any port changes in `docs/architecture.md` so other agents can reproduce them.
