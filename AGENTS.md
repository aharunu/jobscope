# Repository Guidelines

## Project Structure & Module Organization

- `backend/`: FastAPI modular monolith: pure entities in `domain/`, use cases/ports in `application/`, adapters/repositories in `infrastructure/`, HTTP wiring in `interfaces/`.
- `backend/infrastructure/database/migrations/versions/`: Alembic revisions.
- `tests/`: backend unit and PostgreSQL integration tests.
- `frontend/src/`: Next.js routes in `app/`, shared UI in `components/`, API helpers in `lib/`, styles in `styles/`, and Vitest tests in `tests/` and `__tests__/`. The application icon lives in `app/icon.svg`.
- `data/`: source catalogs; `scripts/`: maintenance tools; `docs/development/`: current contracts/runbooks. Design documents express intent; historical audits may be outdated.

## Build, Test, and Development Commands

Use Python 3.11+, Node.js 20, npm, and PostgreSQL 16.

- Docker: copy `.env.docker.example` to `.env.docker`, replace placeholders, then run `./start.ps1 -EnvFile .env.docker`. `./stop.ps1 -EnvFile .env.docker` stops services while retaining data.
- Native backend: `pip install -e ".[dev]"`, configure `.env`, run `python -m alembic upgrade head`, then `python -m uvicorn backend.interfaces.api.main:app --reload --port 8000`.
- From `frontend/`: `npm ci` installs locked dependencies; `npm run dev` serves port 3000; `npm run build` checks the production build.
- Backend checks: `ruff check .`, `ruff format --check .`, `pytest`, and `python -m alembic check`.
- Frontend checks: `npx tsc --noEmit` and `npm test`.
- Repository check: `git diff --check`.

## Coding Style & Naming Conventions

Python uses four-space indentation, snake_case functions/modules, PascalCase classes, and Ruff formatting with double quotes and an 88-character limit. TypeScript uses strict checking; follow surrounding indentation and quotes. Use PascalCase component filenames and camelCase helpers. Preserve Clean/Hexagonal boundaries; ATS adapters acquire data without owning persistence.

## Testing Guidelines

Use pytest/pytest-asyncio (`test_*.py`) and Vitest/React Testing Library (`*.test.ts[x]`). Add regression coverage for changed behavior; no fixed coverage percentage is configured. Database tests require a migrated development/test database. Set `$env:JOBSCOPE_REQUIRE_DATABASE = '1'` before `pytest` in PowerShell to reject skipped tests. Keep CI deterministic with fake provider/AI responses; live boards are optional manual checks.

## Commit & Pull Request Guidelines

History mixes plain summaries and `feat:` subjects; no uniform convention exists. Prefer scoped, imperative subjects such as `fix: preserve application history`. PRs should explain behavior, link relevant issues, report exact checks, and include screenshots for visible UI changes. Document migration/configuration effects and update affected development guides.

## Security & Data Safety

Never commit real `.env*`, credentials, backups, or generated evidence. Keep safe templates versioned. Preserve non-mutating Preview, filtered/PARTIAL absence-closure suppression, occurrence-aware lifecycle, and application/provenance preservation during merges. Do not start another roadmap phase implicitly.
