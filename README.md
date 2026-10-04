# JobScope

Personal Job Intelligence & Evidence-Based Decision Support System.

JobScope transforms the job search and evaluation process into a transparent, measurable, and evidence-based decision support system. It ingests job listings across multiple ATS providers, normalizes requirements, and computes deterministic match scores against structured candidate profiles with explainable evidence and blocker detection.

---

## Architecture & Technology Stack

JobScope is built as a **Modular Monolith** adhering to Clean / Hexagonal Architecture principles, paired with a modern Next.js frontend.

### Backend
- **Language:** Python >= 3.11
- **Framework:** FastAPI (RESTful API & OpenAPI docs)
- **Database:** PostgreSQL 16 + SQLAlchemy 2.x (async engine, mapped domain models)
- **Migrations:** Alembic
- **Testing:** pytest, pytest-asyncio, httpx (800+ automated tests)
- **Code Quality:** Ruff (linting & formatting)
- **Logging:** Structured logging supporting console and JSON formats with automatic secret & credential masking
- **Architecture Layers:**
  - `backend/domain/`: Core business entities, deterministic evaluator rules, value objects, and repository interfaces.
  - `backend/application/`: Application services, use-case orchestration, and domain exceptions inheriting from `JobScopeError`.
  - `backend/infrastructure/`: PostgreSQL repositories, twelve ATS acquisition adapters, safe HTTP clients, and configuration.
  - `backend/interfaces/`: FastAPI app, dependency injection, route handlers, and Pydantic schemas.

### Frontend
- **Framework:** Next.js 15 (App Router) + React 19
- **Language:** TypeScript 5.7 (strict typing)
- **Styling:** Custom Vanilla CSS Design System (dark-themed, CSS variables/tokens, glassmorphism, responsive micro-animations)
- **API Communication:** Same-origin Next.js rewrites (`/api/:path*` -> FastAPI backend)
- **Testing:** Vitest 3 + React Testing Library (130+ automated tests)

---

## Core System Features

1. **Source Registry & Multi-ATS Crawlers:**
   - Acquisition adapters for **Lever, Greenhouse, Ashby, Workday, SmartRecruiters, Recruitee, Personio, Teamtailor, Workable, Hirex, BambooHR and Oracle**. Hosted/widget providers with unverified coverage return PARTIAL and cannot close absent jobs. See [A3 acquisition guide](docs/development/acquisition_a3.md).
   - Crawl orchestration, content hashing, deduplication, and crawl run history auditing.

2. **Deterministic Match Engine:**
   - 100% deterministic, explainable scoring algorithm across 6 evaluation categories:
     - **Skills** (required vs. optional keyword matching & evidence)
     - **Experience** (years of experience, seniority alignment)
     - **Education** (degree requirements & field matching)
     - **Role / Title** (title similarity & domain fit)
     - **Location** (workplace mode, remote eligibility, country/city restrictions)
     - **Other Criteria** (salary expectations, custom constraints)
   - Strict blocker detection (deal-breakers immediately nullify or penalize eligibility).
   - Rich score breakdown with explainable evidence trails.
   - Optional, explicit AI analysis supplements the deterministic result with verified source references and a backend-bounded score adjustment.

3. **Profile & Search Profile Management:**
   - **BaseProfile:** Canonical candidate data (name, summary, skills, work experiences, education history, projects), managed manually at `/profile`. Contact fields and CV import are not implemented.
   - **SearchProfiles:** Contextual search personas (e.g., "Senior Backend Engineer", "Lead Architect") with tailored weights, target roles, salary bounds, and preferred locations.
   - User ownership enforcement and scoped queries.

4. **Interactive Discovery & Match UI:**
   - `/jobs`: Searchable job board with live filtering (keyword, location, remote mode, ATS source), pagination, and URL query synchronization.
   - `/jobs/[id]`: Comprehensive job detail view with interactive deterministic Match Panel, radial score gauges, blocker alerts, category breakdowns, and real-time SearchProfile switcher.
   - `/search-profiles`: Dedicated management interface for creating, viewing, and configuring search profiles.
   - `/profile`: Candidate summary and repeatable skills, experience, education and project editors using the existing BaseProfile API.
   - MatchPanel reads the saved result for the selected Job + SearchProfile on opening or switching profiles. Calculation and re-evaluation require an explicit button click.

5. **Application Tracking & Core Workflow:**
   - Track a job from Job Detail, then manage it at `/applications` and `/applications/[id]`.
   - Six status badges, server status filters, pagination, private notes, persisted chronological history and confirmed removal.
   - Matching and AI are optional. Low scores, blockers and closed jobs never prevent tracking or application management.

---

## Authentication & Authorization Model

JobScope implements a scoped user identity pattern:
- **Authentication Header:** Client requests supply the candidate ID via the `X-User-Id` HTTP header (UUID format).
- **Development Environment (`ENVIRONMENT=development`):** If `X-User-Id` is omitted, the backend falls back to a deterministic development candidate (`00000000-0000-0000-0000-000000000001`) and ensures its User record exists.
- **Production configuration (`ENVIRONMENT=production`, `DEBUG=false`):** `X-User-Id` is required and must identify an existing user. Missing or unknown users receive `401`; malformed UUIDs receive `400`. Debug mode also enables the development fallback.

This header supplies user context; it is not verified authentication. JWT/OAuth and a trusted identity boundary remain future work. `GET /api/profile` auto-provisions the blank BaseProfile when needed.

Match retrieval GET routes resolve this identity without provisioning a User or BaseProfile. In development an unknown identity receives an empty match collection; production still requires an existing user.

---

## Repository Structure

```text
jobscope/
├── backend/
│   ├── application/          # Use cases (matching, profile management, crawl, discovery)
│   ├── domain/               # Pure domain entities, evaluators, repository contracts
│   ├── infrastructure/       # Database models, SQLAlchemy repositories, ATS crawlers
│   └── interfaces/           # FastAPI application, route handlers, Pydantic schemas
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js pages (/, /jobs, /jobs/[id], /profile, /search-profiles)
│   │   ├── components/       # UI components (jobs, matching, profile, search_profile, ui)
│   │   ├── lib/              # API client, contracts, formatters, constants
│   │   ├── styles/           # Design system tokens and globals.css
│   │   └── tests/            # Vitest unit, component, and user flow tests
│   ├── next.config.mjs       # Next.js config with backend API proxy rewrites
│   └── vitest.config.ts      # Vitest test configuration
├── tests/                    # Backend pytest suite (700+ tests)
├── scripts/
│   └── dev.py                # Zero-dependency Python developer CLI runner
├── docs/
│   └── design/               # Architecture decision records and specifications
├── .github/
│   └── workflows/ci.yml      # Automated GitHub Actions CI workflow
├── compose.yaml              # Full local Docker development stack
├── docker-compose.yml        # Preserved native PostgreSQL-only helper
├── .env.example              # Environment variables template
└── pyproject.toml            # Python dependencies and tool configs
```

---

## Local Development

### Option A — Docker Compose

Requires Docker Desktop running Linux containers and a current Compose v2 with
`up --wait` support. The canonical full-stack file is `compose.yaml`; the existing
`docker-compose.yml` remains an explicitly selected PostgreSQL-only native helper.

If root `.env` already has your local `POSTGRES_PASSWORD`, simply run:

```powershell
docker compose up --build
# Or build, detach, and wait for all healthchecks:
.\start.ps1
```

For a fresh checkout, or to keep Docker credentials separate from native settings:

```powershell
Copy-Item .env.docker.example .env.docker
# Edit .env.docker: replace CHANGE_ME with your own local password.
docker compose --env-file .env.docker up --build
# Equivalent convenience wrapper:
.\start.ps1 -EnvFile .env.docker
```

Only safe templates are committed. `.env` and `.env.docker` remain ignored.
Compose requires a nonempty `POSTGRES_PASSWORD`; replace template placeholders
before starting. Credentials are injected at runtime, never copied into images.

| Service | Browser / host address | Container address |
| --- | --- | --- |
| Frontend | http://localhost:3000 | `frontend:3000` |
| Backend | http://localhost:8000 | `backend:8000` |
| API docs | http://localhost:8000/docs | — |
| PostgreSQL | `localhost:5433` by default | `db:5432` |

The backend constructs its container-only `DATABASE_URL` from `POSTGRES_USER`,
`POSTGRES_PASSWORD` and `POSTGRES_DB`, URL-encoding credentials and always using
`db:5432`. Native `DATABASE_URL` is never passed into this container. PostgreSQL
health gates migrations; `alembic upgrade head` must succeed before Uvicorn starts.
The backend readiness check verifies DB connectivity; frontend health checks the
same readiness endpoint through its existing `/api` rewrite to `http://backend:8000`.
The browser continues to use same-origin `/api/*`; no new proxy or CORS setup.

Ports are published on host loopback only. Stop any native frontend/backend using
3000/8000 before starting this stack, or set `DOCKER_FRONTEND_PORT` /
`DOCKER_BACKEND_PORT` to unused host ports. `DOCKER_POSTGRES_PORT` can change the Docker
database host port without affecting the internal URL; existing `POSTGRES_PORT`
continues to configure only the legacy PostgreSQL helper. Native PostgreSQL on
5432 can remain running. This is **local development, not production deployment**;
the existing development identity limitation remains unchanged.

#### Everyday Docker commands

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose restart backend
docker compose up -d --build backend frontend
docker compose down
.\stop.ps1
```

When using `.env.docker`, include `--env-file .env.docker` on Compose commands and
`-EnvFile .env.docker` on both wrappers. The wrappers use their own repository path,
fail visibly on Docker/startup errors, and never open a browser automatically.
`start.ps1` uses Compose health waiting (default timeout 240s after build); inspect
logs if it fails. No arbitrary sleep loops. For slow machines use `-WaitTimeout 600`.
Restart alone does not apply changed environment variables: use `up -d` to recreate.

#### Hot reload and rebuilds

Backend code (`backend/`) and the source catalog (`data/`) are read-only bind
mounts; Python reload uses polling for Docker Desktop compatibility. Frontend
`src/` is a read-only bind mount and Next.js watches via polling. Container users
are non-root; generated `.next` and npm dependencies stay inside the image/container,
separate from Windows `node_modules` and native build artifacts. Source edits reload
without rebuilding. Changes to dependencies, Dockerfiles, startup helper or frontend
config require `docker compose up -d --build`. Next.js in Docker uses the dev server;
`npm run build` remains the independent native production-build validation.
Docker runtime dependencies use `backend/requirements.lock` constraints captured
from the smoke-tested Linux image; direct dependencies remain in `pyproject.toml`.
Refresh constraints deliberately when upgrading. Frontend installs with `npm ci`
and the existing lockfile. Official base images track Python 3.11 / Node 20 patches;
first builds require registry access and may be slow, later source-only builds
reuse dependency layers.

#### Database persistence and protecting existing data

The Docker stack starts with a **separate, fresh database** in the named volume
`jobscope_docker_postgres_data`. It never copies, overwrites or automatically migrates
the existing native database or the old `postgres_data` volume. `docker compose down`
and `stop.ps1` preserve database data. **`docker compose down -v` is destructive**:
it deletes this stack's database volume. Do not use it for normal shutdown or to
change passwords. Existing volumes retain role passwords even if environment
values change; rotate the role in place and align local configuration.

Optional import is manual. First make a separate full backup using a `pg_dump`
version compatible with the source server. The Docker server is PostgreSQL 16;
do not assume a PostgreSQL 17/18 database can be downgraded into it. Verify server
versions and schema revisions first, and keep the original database untouched.

For a PostgreSQL 16 source at the same Alembic head, the following uses PostgreSQL
16 client tools, password prompts (no password in command arguments), and a data-only
archive. Run this only with an **empty, migrated Docker target**, before browsing
pages that provision profile/user records or inserting test data. Full backups
should be stored outside Git/build contexts and may contain personal information.

```powershell
# Full source backup; SOURCE_DB and user/port are examples to replace.
pg_dump -h localhost -p 5432 -U jobscope -d SOURCE_DB -W -Fc -f C:\Backups\jobscope-full.dump
# Separate import archive: keep target's current Alembic revision.
pg_dump -h localhost -p 5432 -U jobscope -d SOURCE_DB -W -Fc --data-only --exclude-table=public.alembic_version -f C:\Backups\jobscope-data.dump
pg_restore --list C:\Backups\jobscope-data.dump
# No --clean, drop, truncate or automatic import. Failure rolls back this restore.
pg_restore -h localhost -p 5433 -U jobscope -d jobscope -W --data-only --no-owner --no-privileges --single-transaction --exit-on-error C:\Backups\jobscope-data.dump
```

Adapt the target port/user/database to Docker settings. Do not restore into a
nonempty target; inspect conflicts and schema compatibility rather than deleting
records to force an import. This procedure is guidance, not automatically executed
by any script. The original database remains the recovery source.

#### LM Studio on the Windows host

AI is disabled by default and is never required for startup. Compose uses separate
`DOCKER_AI_*` settings so native `AI_BASE_URL=http://127.0.0.1:1234/v1` remains valid
for a backend running directly on Windows. Set these in the Compose environment
file to opt in (or set them in root `.env` if using plain Compose):

```dotenv
DOCKER_AI_ENABLED=true
DOCKER_AI_BASE_URL=http://host.docker.internal:1234/v1
DOCKER_OPENAI_API_KEY=lm-studio
DOCKER_AI_MODEL=EXACT_MODEL_ID_FROM_GET_V1_MODELS
DOCKER_AI_TIMEOUT_SECONDS=120
```

These map to existing backend `AI_ENABLED`, `AI_BASE_URL`, `OPENAI_API_KEY`,
`AI_MODEL`, `AI_TIMEOUT_SECONDS`. Blank base URL retains hosted OpenAI support; use
the real hosted key only in ignored local configuration. The harmless `lm-studio`
placeholder applies only to a local server with authentication disabled.
LM Studio stays native; the application contains no Docker hostname/model hardcode.

[Docker Desktop documents `host.docker.internal`](https://docs.docker.com/desktop/features/networking/networking-how-tos/)
for reaching host services. If a loopback-only LM Studio server is unreachable
from Docker, its [Serve on Local Network setting](https://lmstudio.ai/docs/developer/core/server/serve-on-network)
may be needed. Limit access with your Windows firewall/authentication settings;
the setup does not change them automatically. Select/load the exact model returned
by `/v1/models` and keep strict structured-output/evidence validation enabled.

```powershell
# Optional connectivity probe; prints only HTTP status, not model/profile content.
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:1234/v1/models', timeout=5).status)"
```

For authenticated servers use a credential-aware probe without printing keys.
Run AI analysis explicitly from the UI only after opting in; deterministic matching
continues to work when the provider is unavailable.

### Option B — Native Development

### Prerequisites
- **Python** >= 3.11
- **Node.js** >= 18.18 (Node 20+ recommended) & **npm**
- **Docker** & **Docker Compose** (for PostgreSQL)

---

### Backend Setup

1. **Create and activate a virtual environment:**
   ```powershell
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies:**
   ```powershell
   pip install -e ".[dev]"
   ```

3. **Configure environment variables:**
   ```powershell
   cp .env.example .env
   ```
   Replace `CHANGE_ME` with the same new local password in `DATABASE_URL` and `POSTGRES_PASSWORD`. For the default setup both use user/database `jobscope`, host `localhost`, and port `5432`. URL-encode special characters in the URL password, or use an alphanumeric password. Never commit `.env`.

   Compose reads root `.env`; backend settings and Alembic also read it when run from the repository root. Existing Docker volumes retain their database credentials: changing `.env` does not rotate an existing role password. Align that role in place; do not delete the volume to change credentials.

4. **Start PostgreSQL with Docker Compose:**
   ```powershell
   docker compose -f docker-compose.yml up -d postgres
   ```

5. **Run database migrations:**
   ```powershell
   alembic upgrade head
   ```

6. **Start the FastAPI backend server:**
   ```powershell
   uvicorn backend.interfaces.api.main:app --reload --port 8000
   ```
   - **API Base:** `http://127.0.0.1:8000`
   - **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`
   - **Liveness Health Check:** `http://127.0.0.1:8000/health`
   - **Readiness Health Check:** `http://127.0.0.1:8000/health/ready`

---

### Frontend Setup

1. **Navigate to the frontend directory:**
   ```powershell
   cd frontend
   ```

2. **Install dependencies:**
   ```powershell
   npm ci
   ```

3. **Start the Next.js development server:**
   ```powershell
   npm run dev
   ```
   - **Web UI:** `http://localhost:3000`
   - **Job Discovery Board:** `http://localhost:3000/jobs`

> **Note on API Communication:** Next.js proxies all `/api/*` requests to the FastAPI backend (`http://127.0.0.1:8000/api/*`) via server rewrites defined in `next.config.mjs`. You do not need to configure CORS for local development.

Optional frontend overrides belong in `frontend/.env.local`: `BACKEND_API_URL=http://127.0.0.1:8000` (no `/api` suffix) and `NEXT_PUBLIC_USER_ID` (UUID). Next.js does not load the repository root `.env`. The defaults use backend port 8000 and frontend port 3000; changing `PORT` in backend settings alone does not change the explicit Uvicorn CLI port or frontend proxy.

---

## Testing & Quality Assurance

JobScope maintains an extensive test suite across both backend and frontend layers:

### Backend Testing (Pytest & Ruff)
Run from the repository root after configuring PostgreSQL and running `alembic upgrade head`. Database integration fixtures use the application's `DATABASE_URL` and roll back test transactions; use a dedicated development/test database. Without a reachable migrated database, some integration tests skip. CI sets `JOBSCOPE_REQUIRE_DATABASE=1` so any skip fails the quality gate.

```powershell
# Run all backend tests (700+ tests)
pytest -v

# Run linter
ruff check .

# Check code formatting
ruff format --check .
```

### Frontend Testing (Vitest & Next Build)
```powershell
cd frontend

# Run automated component & flow tests (80+ tests)
npm test

# Check TypeScript types
npx tsc --noEmit

# Verify production build compilation
npm run build
```

### Developer Task Runner (`scripts/dev.py`)
A cross-platform CLI task runner is provided for common backend tasks:
```powershell
# Run format check, lint, and tests sequentially
python scripts/dev.py check

# Run tests
python scripts/dev.py test

# Start dev server
python scripts/dev.py run --port 8000

# Run database migrations
python scripts/dev.py migrate
```

---

## REST API Endpoints

All application routes are served under `/api` (or at root for health checks):

| Category | Endpoint | Method | Description |
|---|---|---|---|
| **Health** | `/health` | GET | System liveness probe |
| **Health** | `/health/ready` | GET | Database connectivity readiness probe |
| **Jobs** | `/api/jobs` | GET | Paginated canonical job list with search & filter params (`company`, `location`, `work_mode`, `employment_type`, `status`) |
| **Jobs** | `/api/jobs/{id}` | GET | Canonical job details including structured requirements |
| **Sources** | `/api/sources` | GET | List registered ATS and career sources |
| **Sources** | `/api/sources/stats` | GET | Sources breakdown and health summary |
| **Sources** | `/api/sources/sync` | POST | Sync sources from canonical Markdown catalog into DB |
| **Sources** | `/api/sources/probe` | POST | Execute batch source health probes |
| **Sources** | `/api/sources/{id}` | GET, PATCH | Retrieve or update a source |
| **Sources** | `/api/sources/{id}/status` | PATCH | Update source active status |
| **Sources** | `/api/sources/{id}/probe` | POST | Probe specific source health |
| **Crawl** | `/api/crawl/run` | POST | Trigger ingestion run for a source or all sources |
| **Crawl** | `/api/crawl/runs` | GET | List historical crawl runs |
| **Crawl** | `/api/crawl/runs/{id}` | GET | Get specific crawl run details |
| **Crawl** | `/api/crawl/runs/{id}/jobs` | GET | Discovered job audit records for a crawl run |
| **Profile** | `/api/profile` | GET | Get candidate BaseProfile (auto-provisions if missing) |
| **Profile** | `/api/profile` | PATCH | Update BaseProfile metadata (name, summary) |
| **Profile** | `/api/profile/skills` | GET, POST | List or add profile skills |
| **Profile** | `/api/profile/skill-suggestions?q={query}&limit=20` | GET | Read bounded suggestions from the existing technical-skill taxonomy; custom skills remain allowed |
| **Profile** | `/api/profile/skills/{id}` | PATCH, DELETE | Update or remove profile skill |
| **Profile** | `/api/profile/experiences` | GET, POST | List or add profile work experiences |
| **Profile** | `/api/profile/experiences/{id}` | PATCH, DELETE | Update or remove profile experience |
| **Profile** | `/api/profile/educations` | GET, POST | List or add profile education records |
| **Profile** | `/api/profile/educations/{id}` | PATCH, DELETE | Update or remove profile education |
| **Profile** | `/api/profile/projects` | GET, POST | List or add profile projects |
| **Profile** | `/api/profile/projects/{id}` | PATCH, DELETE | Update or remove profile project |
| **Search Profiles** | `/api/search-profiles` | GET, POST | List or create contextual search personas |
| **Search Profiles** | `/api/search-profiles/{id}` | GET, PATCH, DELETE | Retrieve, update, or remove a search profile |
| **Matching** | `/api/matches` | POST | Evaluate job against SearchProfile; returns deterministic score & evidence |
| **Matching** | `/api/matches/job/{job_id}?search_profile_id={id}` | GET | Retrieve the current user's saved match for this Job + SearchProfile |
| **Matching** | `/api/matches` | GET | Current user's saved matches; optional `job_id`, `search_profile_id`, `limit`, `offset` |
| **AI Matching** | `/api/matches/{match_result_id}/ai?force=false` | POST | Explicit owned AI analysis; reuse matching fingerprint or force re-analysis |
| **Applications** | `/api/applications` | GET, POST | List or create tracked applications (backend already implemented) |
| **Applications** | `/api/applications/{id}` | GET, DELETE | Retrieve or delete an application |
| **Applications** | `/api/applications/{id}/status` | PATCH | Transition status and append history |
| **Applications** | `/api/applications/{id}/notes` | PATCH | Update application notes |
| **Applications** | `/api/applications/{id}/history` | GET | Retrieve status history |

### Application Tracking Backend — COMPLETE

The backend supports tracking an existing job, listing/filtering/paginating the current user's applications, retrieving details, updating status or notes, and deleting a tracking record. The frontend and core workflow are also **complete (FAZ 4)**.

- Creation defaults to `INTERESTED`; any valid explicit ApplicationStatus is accepted. Initial creation has no history entry because there is no previous application status.
- One application per `(job_id, user_id)` is enforced by PostgreSQL and the service. Duplicate tracking returns `409 APPLICATION_ALREADY_EXISTS`, including insert races.
- Every actual allowed status change writes history in the same request transaction. A failure rolls back status and history together. Concurrent status/notes edits lock and refresh the owned application before mutation.
- Same-status requests return `422 INVALID_STATUS_TRANSITION` and create no history. Existing transition policy is preserved:

  | Current status | Allowed next statuses |
  |---|---|
  | INTERESTED | APPLYING, APPLIED, REJECTED |
  | APPLYING | INTERESTED, APPLIED, REJECTED |
  | APPLIED | INTERVIEW, OFFER, REJECTED |
  | INTERVIEW | APPLIED, OFFER, REJECTED |
  | OFFER | REJECTED |
  | REJECTED | INTERESTED, APPLYING, APPLIED, INTERVIEW |

- Missing or another user's application returns `404 APPLICATION_NOT_FOUND` for detail, status, notes, deletion and history. Payload `user_id` is rejected; ownership comes from request context.
- Notes are optional, limited to 5,000 characters, and trimmed; null/blank notes clear the value. Notes edits create no status history.
- Detail embeds chronological history; `/history` exposes the same ordering by `changed_at`, then ID. Lists use status filtering and `limit` (1–100) / `offset` (non-negative), returning `items`, `total`, `limit`, `offset`.
- Optional `job_id` UUID filtering uses the existing owned unique lookup. It returns zero or one matching application without downloading the full list; status and pagination constraints still apply.
- Job and Application statuses are independent: closing a job preserves an application in `INTERVIEW`. Explicitly deleting the application deletes its history; closing the job does neither.

### Application Tracking Frontend & Core Workflow — COMPLETE

Configure `/profile`, manage search personas at `/search-profiles`, browse `/jobs` and open a job. The MatchPanel retrieves saved deterministic results and optionally runs explicit calculation or AI analysis. **Track Application** creates an `INTERESTED` record even without a match or AI. An existing record shows its current status and **Manage application**; duplicate creation races recover through the owned job lookup.

`/applications` shows job summaries, application/job status, notes previews and timestamps in responsive cards, with server status filtering and 20-item pagination. `/applications/{id}` survives refresh/direct navigation and provides **View job**, allowed next-status choices, notes editing/clearing (5,000 characters), real persisted history and separate **Remove application → Confirm removal** controls. Removal deletes tracking/history, preserves the job and allows tracking again on a later visit.

Status, notes and removal requests share a synchronous mutation guard; authoritative PATCH responses update the record without optimistic status changes. Notes drafts survive failures and status saves. Requests are aborted on navigation, and stale responses cannot update a different application or job. Application identity is User + Job and remains independent of SearchProfile/AI selection.

| Core capability | Status |
|---|---|
| BaseProfile backend/frontend | COMPLETE |
| SearchProfile backend/frontend | COMPLETE |
| Job Discovery | COMPLETE |
| Deterministic Matching / Persistence / Retrieval | COMPLETE |
| Optional AI Matching | COMPLETE |
| Application Tracking backend/frontend | COMPLETE |
| Core JobScope workflow | COMPLETE |

Validation combines real PostgreSQL/API workflow tests and frontend behavioral tests, with targeted desktop/tablet/mobile browser smoke checks. This is not a full automated browser E2E suite or production authentication/deployment certification.

### Candidate Profile UI and Match Retrieval — COMPLETE

Open `/profile` from navigation, create/edit the candidate name and summary, then manage skills, experience, education and projects. The existing backend initializes a blank `Candidate Profile` on GET; the UI's Create Profile action saves its metadata through PATCH. SearchProfiles remain separate search personas configured at `/search-profiles`.

Skill names offer optional suggestions from the existing extraction taxonomy. Custom names remain valid. The editor offers Beginner, Intermediate, Advanced, Expert or Not specified; historical free-text levels and category metadata are preserved when editing other fields. Category is omitted from the editor because matching does not consume it. Optional experience years accept 0–50 in half-year steps in the UI; the API rejects non-finite or out-of-range numbers.

Experience company, role title and start date are required. Native date controls remain empty until a date is entered, accept dates from 1900-01-01 through today, and require end date to be on or after start date. Current role immediately clears/disables end date, and the backend persists it as null. Historical invalid dates are flagged for manual correction rather than replaced with an invented date. Field errors preserve the draft, and save requests use the existing duplicate-request guard.

`GET /api/matches/job/{job_id}?search_profile_id={id}` is the canonical detail lookup. It returns the same persisted representation as POST, including scores, category breakdowns, requirement evidence, blockers and explanation. Missing saved results return `404 MATCH_RESULT_NOT_FOUND`; missing jobs or inaccessible SearchProfiles return their resource 404s. GET never calls the match engine or writes results. Collection GET returns `items`, `total`, `limit`, `offset`, ordered by `updated_at` descending then ID descending; `limit` is 1–100 and `offset` is non-negative.

Each `(job_id, base_profile_id, search_profile_id)` stores one latest snapshot. Explicit POST re-evaluation overwrites that snapshot, retaining its ID and creation timestamp. Profile/job edits do not automatically invalidate or recalculate it; MatchPanel displays its saved timestamp and offers explicit re-evaluation.

Run `alembic upgrade head` before using retrieval. Migration `0008_match_snapshot` persists category scores and explanation that previously existed only in the POST response. Legacy rows retain their stored scalar scores and requirement evidence with `{}` category scores and a null explanation. GET does not invent or backfill missing evidence; explicitly re-evaluate to obtain a complete current snapshot.

### Optional AI Matching — COMPLETE

AI runs only from **AI ile Detaylı Analiz Et** after a persisted deterministic match exists. Opening a job, retrieving matches, switching SearchProfiles, calculating deterministic matching, editing profiles and crawling never call AI. Missing configuration or provider errors leave the deterministic result usable.

Configure the root ignored `.env`, then restart the backend:

```dotenv
AI_ENABLED=true
OPENAI_API_KEY=YOUR_API_KEY
AI_MODEL=gpt-4.1-mini-2025-04-14
AI_TIMEOUT_SECONDS=30
AI_BASE_URL=
```

Leave `AI_BASE_URL` blank for hosted OpenAI. For an OpenAI-compatible local server such as LM Studio, start the server, read its exact chat-model ID from `GET http://127.0.0.1:1234/v1/models`, and configure the ignored root `.env`:

```dotenv
AI_ENABLED=true
AI_BASE_URL=http://127.0.0.1:1234/v1
OPENAI_API_KEY=lm-studio
AI_MODEL=EXACT_CHAT_MODEL_ID_FROM_V1_MODELS
AI_TIMEOUT_SECONDS=120
```

Restart the backend after changing settings. `lm-studio` is a harmless explicit placeholder only for a server with authentication disabled; use the server's actual key when authentication is enabled. No hosted credential is needed for local inference. The base URL must include its API prefix (normally `/v1`) and must not contain credentials, query parameters or fragments. The server must support the existing strict `response_format=json_schema` request and return the complete AI output schema; [LM Studio documents this format](https://lmstudio.ai/docs/developer/openai-compat/structured-output). Invalid/truncated output remains an error, with the deterministic result preserved. Changing endpoints invalidates AI cache even when model IDs are equal. No model/server-specific fallback or relaxed validation is used.

The Next.js API rewrite proxy allows 150 seconds so it can relay the backend's bounded 120-second AI request and transaction overhead. Restart the frontend after updating `next.config.mjs` (rebuild before production start); its former 30-second default could return a proxy 500 while a local model's successful analysis continued in the backend. Provider text containing NUL characters is rejected as `AI_INVALID_OUTPUT` / 502 before persistence; it is never stripped or repaired.

The safe template defaults to disabled AI with an empty key. One OpenAI HTTP adapter uses existing `httpx`; the application depends on a provider Protocol, and automated tests use an offline fake or mock HTTP. The pinned model supports [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) according to its [official model documentation](https://developers.openai.com/api/docs/models/gpt-4.1-mini). Requests have a bounded timeout, no automatic retries, no redirects, no tools, a strict JSON schema and `store=false`.

`POST /api/matches/{id}/ai` accepts no trusted client content; an optional empty JSON object is permitted, other body fields are rejected. The backend loads owned Job, BaseProfile, SearchProfile and the saved deterministic evidence. Successful responses use MatchResultResponse with `ai_score`, `ai_adjustment` and nested `ai_analysis` (assessment, summary, strengths, gaps, risks, evidence, provider/model, created timestamp, `cached`). Detail and collection GET return the same saved analysis without provider calls or writes.

Cache fingerprints use canonical JSON/SHA-256 over semantic job/profile/search/deterministic inputs, provider/model, prompt version and schema version, excluding unrelated IDs/timestamps. One latest AIAnalysis per MatchResult is retained. An identical explicit request returns it with `cached=true`; **Re-analyze AI** sends `force=true`. Profile/job/search changes cause a cache miss on the next explicit request, while GET remains read-only. Deterministic re-evaluation clears the old AI projection/cache transactionally. Simultaneous normal AI requests serialize on the MatchResult row and reuse the committed result; the provider timeout bounds each external call while this lock is held.

The backend uses Decimal arithmetic and two-decimal `ROUND_HALF_UP` rounding:

```text
raw adjustment = clamp((AI score - deterministic score) × 0.25, -8, +8)
final score = clamp(deterministic score + accepted adjustment, 0, 100)
```

Alpha 0.25 is an initial calibration constant. Example: deterministic 86, AI 94 → +2 → final 88. Provider output cannot set final score, adjustment or confidence. Any unsupported evidence (or no evidence) disables the entire aggregate AI adjustment, because its contribution cannot be attributed safely. Unmet deterministic blockers prevent a positive adjustment; deterministic requirements/blockers are never rewritten.

Evidence references must match `profile.skills[i]`, `profile.experiences[i]`, `profile.educations[i]` or `profile.projects[i]` in the canonical prompt order, agree with evidence type, and include an exact source quote of at least three characters. Invalid references/type/quotes become `NONE / INSUFFICIENT_EVIDENCE`. This verifies source existence and quotation, not the semantic truth of every inference. Model narrative remains advisory. Confidence is calculated as `baseline + (100 - baseline) × verified_evidence_fraction × 0.25`, clamped to 0–100; the baseline is saved to prevent repeated re-analysis inflation. Missing-data uncertainty is inherited from deterministic confidence. Score disagreement alone does not reduce confidence.

Migration `0009_ai_details` saves previously unsupported strengths/gaps/risks, baseline confidence and source quotes in existing AI tables. Run `alembic upgrade head` before using AI. Both migration directions are tested transactionally.

**Privacy:** An explicit AI request sends the current job's description/responsibilities/requirements and fit metadata, candidate summary/skills/experience/education/projects, search preferences and deterministic scores/evidence to the configured provider (hosted OpenAI by default, or the configured OpenAI-compatible server). Candidate root name/IDs, project URLs, internal settings, keys, headers, application notes and unrelated users are omitted. Prompts/responses are not logged; SQL debug parameters are hidden. Job/profile text is delimited as untrusted JSON data with instructions against prompt injection and invented evidence; this is defensive separation, not perfect injection immunity. Provider costs, terms and account/model availability apply. No real-provider call is part of normal tests.

### Planned Endpoints (Future Phases)
The following capabilities are specified in design documentation and scheduled for subsequent implementation phases:
- **CV Import & Parse (`/api/cv/upload`, `/api/cv/{id}/approve`)**: PDF/DOCX resume parsing.
- **Manual Job Entry (`/api/jobs/manual`)**: User-submitted job URLs.
- **Scheduler**: Planned. Twelve acquisition adapters are implemented; PARTIAL providers suppress absence closure.

---

## Documentation

Detailed architecture specifications and design records are available in `docs/`:
- [MVP Technical Design](docs/design/01_mvp_technical_design.md): Architectural decisions and foundational choices.
- [Database & API Design](docs/design/02_database_and_api_design.md): Schemas, relational integrity, and API specs.
- [Data Model & Architecture](docs/design/03_data_model_and_architecture.md): Entity relationships and Clean Architecture boundaries.
