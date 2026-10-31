# JobScope

Personal job intelligence and evidence-based decision support. JobScope collects
public job postings into one workspace, extracts requirements, compares vacancies
with candidate profiles and tracks applications. Listings retain their original
source links and provenance so matching decisions can be inspected.

Built for local development and personal use. AI is optional; acquiring jobs,
deterministic matching and application tracking work without an AI provider.

## What you can do

- **Find jobs:** search and filter collected listings, read full descriptions and
  requirements, and inspect the sources where each job was observed.
- **Maintain your profile:** record skills, experience, education and projects;
  create separate Search Profiles for different roles and preferences.
- **Compare fit:** explicitly calculate deterministic scores with category
  breakdowns, evidence, missing information and blockers. Optionally request AI
  analysis after saving a deterministic match.
- **Track applications:** save a job, update its application status, keep notes
  and review status history. Tracking does not require a match or AI analysis.
- **Control ingestion:** select Sources or ATS providers, set country policies,
  preview decisions, persist accepted jobs and monitor or cancel runs.
- **Review duplicates:** retain multiple source occurrences under a logical job
  and review uncertain duplicate candidates at `/dedup`.
- **Research new sources:** use local discovery tools to identify candidate career
  boards and prepare review reports before updating the source catalog.

## Quick start: Docker

Requires Git and Docker Desktop running Linux containers with Docker Compose v2
(`up --wait` support is needed for the PowerShell wrapper). Host Python, Node.js
and PostgreSQL installations are not required for this option. Commands below use
PowerShell; on other shells use equivalent copy commands and direct Compose.

```powershell
git clone https://github.com/aharunu/jobscope.git
cd jobscope
Copy-Item .env.docker.example .env.docker
```

Edit `.env.docker` and replace `POSTGRES_PASSWORD=CHANGE_ME` with your own local
password before starting. If you already have this file, keep your existing
configuration rather than copying over it.

```powershell
.\start.ps1 -EnvFile .env.docker
```

The wrapper builds and starts the stack in the background, waits for readiness
and prints service addresses. The equivalent foreground command is:

```powershell
docker compose -f compose.yaml --env-file .env.docker up --build
```

| Service | Default address |
| --- | --- |
| Application | [localhost:3000](http://localhost:3000) |
| Backend API documentation | [localhost:8000/docs](http://localhost:8000/docs) |
| Backend/database readiness | [localhost:8000/health/ready](http://localhost:8000/health/ready) |
| PostgreSQL | `127.0.0.1:5433` on the host; `db:5432` inside Docker |

Startup applies database migrations automatically. The Docker stack uses its own
`jobscope_docker_postgres_data` volume; it does not import your native database.
The first build needs network access to download images and dependencies. Later
starts reuse image layers; backend and frontend source edits support hot reload.

Stop the stack while retaining database data:

```powershell
.\stop.ps1 -EnvFile .env.docker
```

`docker compose down -v` deletes the database volume; use the normal stop command
for everyday shutdown. See the [development runbook](docs/development/local-development.md)
for backups, port overrides, rebuilding dependencies and importing existing data.

## First use

A fresh database has no registered sources or collected jobs. Starting the app
does not automatically import the catalog or crawl career boards.

1. **Register sources.** With the backend running, synchronize the curated
   `data/turkish-job-sources.md` catalog through `POST /api/sources/sync`, either
   from [the API docs](http://localhost:8000/docs) or PowerShell:

   ```powershell
   Invoke-RestMethod -Method Post -Uri 'http://localhost:8000/api/sources/sync'
   ```

   This updates the Source registry; it does not fetch job postings. Repeated
   synchronization preserves existing Source IDs, manual active state and
   operational overrides. Review returned counts and catalog warnings.
2. **Preview one source.** Open [Ingestion](http://localhost:3000/ingestion),
   choose a supported Source and review the country policy. Start with Preview
   and inspect accepted/rejected decisions and coverage warnings.
3. **Persist suitable results.** Use **Persist this preview** on an eligible
   completed preview. Persist performs fresh acquisition, so live listings and
   counts may differ from the preview. Open [Jobs](http://localhost:3000/jobs)
   to browse the saved results.
4. **Set up matching.** Fill in [Profile](http://localhost:3000/profile), create
   a [Search Profile](http://localhost:3000/search-profiles), then open a job and
   explicitly calculate a match. Profile edits do not automatically recalculate
   saved matches.
5. **Track a job.** Use **Track Application** from job detail and manage its status,
   notes and history at [Applications](http://localhost:3000/applications).
   Tracking is independent of the selected Search Profile.

Preview makes real network requests and saves ingestion audit records, but does
not create Jobs, occurrences, raw observations, requirements or dedup candidates.
PARTIAL or country-filtered acquisition cannot close absent occurrences. A logical
job remains ACTIVE while any occurrence is ACTIVE; closing a job preserves its
application record and history. See [ingestion behavior](docs/development/ingestion-control.md)
and [deduplication](docs/development/hybrid-deduplication.md) for the full contracts.

## Supported job sources

Acquisition adapters: **Lever, Greenhouse, Ashby, Workday, SmartRecruiters,
Recruitee, Personio, Teamtailor, Workable, Hirex, HRPeak, BambooHR and Oracle**.

Support applies to the public board URL formats implemented by each adapter;
recognizing a platform does not guarantee every company's board is readable.
HRPeak public HTML acquisition is always PARTIAL. Provider coverage, accepted URL
formats and configuration are documented in the
[provider contracts](docs/development/acquisition_a3.md) and
[Lever/Greenhouse guide](docs/development/acquisition_a1.md).

Kariyer.net and `custom` catalog entries have no acquisition adapter and are
excluded from ingestion. SmartRecruiters supports country query filtering;
Workday uses verified board-specific country facets when available. Other paths
retain local filtering. Search Profiles affect matching, not acquisition scope.

For new boards, the [discovery workflow](docs/development/source-discovery.md)
prepares local provider modules and phased research from the canonical catalog.
Discovery does not automatically register sources, activate them or ingest jobs.
`data/source-discovery/`, local `data/discovery*.md` inputs and generated reports
remain ignored by Git. Run these developer tools from a native Python environment;
they are not included in the app's Docker runtime. Optional agent research uses
an existing Codex CLI sign-in and is separate from the app's AI matching settings.

## Native development

Requires Python 3.11+, Node.js 20 with npm, and PostgreSQL 16. From the repository
root, create a virtual environment and copy the backend configuration template:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `DATABASE_URL` and `POSTGRES_PASSWORD` in `.env` to consistent local values;
URL-encode special characters in the password used in `DATABASE_URL`. Keep an
existing `.env` instead of overwriting it. Use an existing PostgreSQL instance
with the configured database/user, or start the PostgreSQL-only helper:

```powershell
docker compose -f docker-compose.yml up -d --wait postgres
python -m alembic upgrade head
python -m uvicorn backend.interfaces.api.main:app --reload --port 8000
```

In a second terminal, start the frontend:

```powershell
cd frontend
npm ci
npm run dev
```

The two Compose files serve different workflows:

| File | Purpose | Default database host port |
| --- | --- | --- |
| `compose.yaml` | Full Docker stack: frontend, backend and database | 5433 |
| `docker-compose.yml` | PostgreSQL-only helper for a native backend/frontend | 5432 |

Frontend `/api` requests proxy to `http://127.0.0.1:8000` by default. Root `.env`
configures the backend; frontend overrides belong in `frontend/.env.local`.
Stop native servers using ports 3000/8000 before running the full Docker stack.
For Linux/macOS activation, database setup and environment details, see the
[development runbook](docs/development/local-development.md).

## Optional AI analysis

AI is disabled by default. Deterministic matching remains usable if AI is
unconfigured or unavailable. Explicit AI analysis sends the selected job,
candidate evidence, search preferences and saved matching evidence to the
configured provider; use a provider appropriate for that data.

Native development uses `AI_*` / `OPENAI_API_KEY` settings in `.env`; the full
Docker stack uses separate `DOCKER_AI_*` / `DOCKER_OPENAI_API_KEY` overrides in
`.env.docker`. Hosted and OpenAI-compatible local servers are supported, subject
to the required structured-output schema. Follow the
[AI configuration and privacy guide](docs/development/ai-matching.md) and
[Docker/LM Studio setup](docs/development/local-development.md#lm-studio-on-the-windows-host)
for model IDs, timeouts and host networking.

## Current limitations

- **Local development identity:** `X-User-Id` supplies scoped user context with a
  development fallback; it is not verified authentication. The current setup is
  not a production deployment. See [identity behavior](docs/development/api.md).
- **Matching interpretation:** scores and confidence summarize the implemented
  rules and available evidence, not the probability of getting an offer. Some
  rules currently include search preferences alongside candidate skills; see the
  [matching limitations](docs/development/requirements-and-deterministic-matching.md).
- **Provider coverage:** public boards can reject requests, require unsupported
  URLs or provide incomplete data. PARTIAL results and an empty response do not
  establish that all vacancies were observed or closed.
- **Planned work:** scheduling, CV import and manual job entry are not implemented.
  The [product backlog](docs/roadmap/post_mvp_product_backlog.md) records planned
  improvements separately from implemented behavior.

## Architecture and repository layout

Python / FastAPI / PostgreSQL / SQLAlchemy / Alembic; Next.js / React / TypeScript.
The backend is a modular monolith with Clean/Hexagonal boundaries. Adapters acquire
data; application use cases and persistence adapters own ingestion and lifecycle.

```text
backend/          Domain, application use cases, infrastructure and HTTP interfaces
frontend/src/     Next.js routes, shared components, API client and frontend tests
tests/            Backend unit and PostgreSQL integration tests
data/             Canonical source catalog and ignored local discovery workspace
scripts/          Developer, discovery, profiling and maintenance tools
docs/development/ Current contracts and operational runbooks
docs/design/      Original architecture and design intent
docs/roadmap/     Planned product work
docs/archive/     Selected historical audits
```

## Validation

Use a development/test database, not a database containing data you need to keep.
With the virtual environment active and that database configured and migrated:

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

GitHub Actions runs backend lint/format/PostgreSQL tests and frontend type checking,
tests and production build on push/pull requests. Automated tests use fake provider
responses; live ATS boards, agent research and AI servers are not CI dependencies.

## Documentation

Start with the [documentation index](docs/development/README.md). Development guides
record current behavior; design documents describe intent, and historical audits
may include findings that have since been resolved.

- [Local development, backups and verification](docs/development/local-development.md)
- [API reference and user context](docs/development/api.md)
- [Source registry and catalog synchronization](docs/development/source-registry.md)
- [Source discovery and local research tools](docs/development/source-discovery.md)
- [Profiles, matching and applications](docs/development/profiles-matching-applications.md)
- [Optional AI and local model configuration](docs/development/ai-matching.md)
- [Acquisition architecture and safety](docs/development/acquisition-architecture.md)
- [Ingestion control](docs/development/ingestion-control.md)
- [Provider country filtering](docs/development/provider-country-filtering.md)
- [Hybrid deduplication](docs/development/hybrid-deduplication.md)
- [Maintenance tools](docs/development/maintenance-tools.md)
- [Historical audits (2026-10-01)](docs/archive/2026-10-01/README.md)

Reusable scripts, source, migrations, tests and safe environment templates are
versioned. Real `.env*`, local backups, attachments and generated reports/evidence
remain ignored. Selected historical audits are versioned under `docs/archive/`;
local `docs/agent-reports/` evidence is not required to launch the application.

## License

[MIT](LICENSE).
