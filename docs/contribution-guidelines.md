# Contribution Guidelines (Quick Scan)

## Branch & PR Flow
1. Create feature branch from `main`: `git checkout -b feature/<slug>`.
2. Run formatters + tests locally (see `docs/development-guide.md`).
3. Use conventional commit-style messages (e.g., `feat: add realtime alert api`).
4. Open PR with: summary, screenshots (for frontend), deployment checklist.

## Code Quality
- Python: `black`, `isort`, `flake8`, `mypy`, `pytest`.
- Frontend: `npm run lint`, add unit tests when available.
- Keep functions under 100 lines; break service logic into `backend/services/*` helpers.

## Documentation
- Update `docs/` artifacts when adding new APIs, data models, or infra changes.
- Record schema changes by adding a migration file under `backend/db/migrations/`.

## Reviews
- Require at least one reviewer before merge (self if solo project—use checklist in PR template).
- Verify deployment plan (Compose vs manual) before merging infra-impacting changes.
