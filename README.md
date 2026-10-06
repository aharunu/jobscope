# JobScope

Personal job intelligence and evidence-based decision support. JobScope acquires
public job postings, preserves provider provenance, extracts requirements and
compares vacancies with candidate profiles using explainable deterministic matching.

## Implemented product

- **Jobs and Job Detail:** search, filters, pagination, requirements, saved matches
 and Source occurrences.
- **Profile and Search Profiles:** candidate editors and editable search personas.
 SearchProfile seniority is a single persisted selection.
- **Matching:** explicit deterministic calculation and optional explicit AI analysis
 through a hosted or local OpenAI-compatible provider.
- **Applications:** status transitions, notes, history and confirmed removal.
- **Ingestion:** Preview/Persist, country policies, Source/provider selection,
 progress, cancellation and frozen policy snapshots. Persisting a preview performs
 fresh acquisition; it does not replay an exact stored posting set.
- **Hybrid deduplication:** Logical Jobs, Source-owned occurrences, conservative
 deterministic decisions and confirmed review at `/dedup`.

Acquisition adapters: **Lever, Greenhouse, Ashby, Workday, SmartRecruiters,
Recruitee, Personio, Teamtailor, Workable, Hirex, BambooHR and Oracle**.
Kariyer.net and `custom` catalog entries have no acquisition adapter and are
excluded from ingestion. SmartRecruiters supports country query filtering;
Workday uses verified board-specific country facets when available. Other paths
retain local filtering. SearchProfiles never filter acquisition.

Preview does not create Jobs, occurrences, raw observations, requirements or dedup
candidates. PARTIAL or country-filtered acquisition cannot close absent occurrences.
A Logical Job remains ACTIVE while any occurrence is ACTIVE. Persist does not
reset the database, and safe merges preserve Applications and raw provenance.

Scheduler, CV import, manual job entry and verified production authentication are
planned work; see the [product backlog](docs/roadmap/post_mvp_product_backlog.md).

## Architecture

Python 3.11+ / FastAPI / PostgreSQL 16 / SQLAlchemy / Alembic; Next.js 15 /
React 19 / TypeScript / npm. The backend remains a modular monolith with
Clean/Hexagonal boundaries: pure domain, application services, infrastructure
adapters/repositories and FastAPI interfaces. Adapters acquire data; existing
ingestion owns persistence, requirements, deduplication and lifecycle.

`X-User-Id` supplies scoped user context, with a development fallback. It is not
verified authentication. See the [API and identity contract](docs/development/api.md).

## Quick start: Docker

From the repository root, copy the safe template and replace `CHANGE_ME` with a
local development password:

```powershell
Copy-Item .env.docker.example .env.docker
docker compose --env-file .env.docker up --build
```

Open [JobScope](http://localhost:3000), [backend API docs](http://localhost:8000/docs)
and [readiness](http://localhost:8000/health/ready). PostgreSQL is exposed on
`127.0.0.1:5433`; the backend connects to `db:5432`. Startup applies migrations
after database readiness. This stack uses its own Docker data volume.

The first build installs dependencies. Later starts reuse image layers and
dependency volumes; normal source edits use hot reload. `docker compose down`
retains the database volume. Full setup, start/stop wrappers, native development,
backup/restore and local LM Studio configuration are in the
[development runbook](docs/development/local-development.md).

## Native development

Use Python 3.11+, PostgreSQL 16 and Node.js 20 with npm (CI uses Node.js 20).
Create/activate a virtual environment, install `pip install -e ".[dev]"`, and copy
`.env.example` to `.env`. Set a consistent local `DATABASE_URL` and
`POSTGRES_PASSWORD`. The preserved `docker-compose.yml` is the PostgreSQL-only
helper on port 5432; `compose.yaml` is the full Docker stack.

Apply `python -m alembic upgrade head`, then start:

```powershell
python -m uvicorn backend.interfaces.api.main:app --reload --port 8000
```

In another terminal, from `frontend`:

```powershell
npm ci
npm run dev
```

Frontend `/api` requests proxy to `http://127.0.0.1:8000` by default. Root `.env`
is backend configuration; frontend overrides belong in `frontend/.env.local`.
See the runbook before changing ports, proxy targets or database environments.

## Validation

With the virtual environment active and a migrated development/test database:

```powershell
ruff check .
ruff format --check .
$env:JOBSCOPE_REQUIRE_DATABASE = '1'
pytest
python -m alembic check
git diff --check
```

From `frontend`:

```powershell
npx tsc --noEmit
npm test
npm run build
```

GitHub Actions runs backend lint/format/database tests and frontend type checking,
tests and production build on push/pull requests. Tests use fake provider
acquisition; live ATS boards and AI servers are not CI dependencies.

## Documentation

Start with the [documentation index](docs/development/README.md) for current
contracts and the distinction between design intent and historical evidence.

- [Local development and verification](docs/development/local-development.md)
- [API reference and user context](docs/development/api.md)
- [Profiles, matching and applications](docs/development/profiles-matching-applications.md)
- [Optional AI and local model configuration](docs/development/ai-matching.md)
- [Acquisition architecture and safety](docs/development/acquisition-architecture.md)
- [Ingestion control](docs/development/ingestion-control.md)
- [Provider country filtering](docs/development/provider-country-filtering.md)
- [Hybrid deduplication](docs/development/hybrid-deduplication.md)
- [Maintenance tools](docs/development/maintenance-tools.md)

Reusable scripts, source, migrations, tests and safe environment templates are
versioned. Real `.env*`, local backups, attachments, reports and generated evidence
remain ignored. Local `docs/agent-reports/` contains dated audit/acceptance evidence;
it is not required to launch the application.
