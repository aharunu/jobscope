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
- **Testing:** pytest, pytest-asyncio, httpx (700+ automated tests)
- **Code Quality:** Ruff (linting & formatting)
- **Logging:** Structured logging supporting console and JSON formats with automatic secret & credential masking
- **Architecture Layers:**
  - `backend/domain/`: Core business entities, deterministic evaluator rules, value objects, and repository interfaces.
  - `backend/application/`: Application services, use-case orchestration, and domain exceptions inheriting from `JobScopeError`.
  - `backend/infrastructure/`: PostgreSQL repositories, ATS crawlers (Greenhouse, Lever implemented; Ashby, Workday planned), HTTP clients, and configuration.
  - `backend/interfaces/`: FastAPI app, dependency injection, route handlers, and Pydantic schemas.

### Frontend
- **Framework:** Next.js 15 (App Router) + React 19
- **Language:** TypeScript 5.7 (strict typing)
- **Styling:** Custom Vanilla CSS Design System (dark-themed, CSS variables/tokens, glassmorphism, responsive micro-animations)
- **API Communication:** Same-origin Next.js rewrites (`/api/:path*` -> FastAPI backend)
- **Testing:** Vitest 3 + React Testing Library (80+ automated tests)

---

## Core System Features

1. **Source Registry & Multi-ATS Crawlers:**
   - Pluggable crawler engine supporting **Greenhouse** and **Lever** (with **Ashby** and **Workday** planned for future phases).
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

3. **Profile & Search Profile Management:**
   - **BaseProfile:** Canonical candidate CV data (contact, summary, skills, work experiences, education history, projects).
   - **SearchProfiles:** Contextual search personas (e.g., "Senior Backend Engineer", "Lead Architect") with tailored weights, target roles, salary bounds, and preferred locations.
   - User ownership enforcement and scoped queries.

4. **Interactive Discovery & Match UI:**
   - `/jobs`: Searchable job board with live filtering (keyword, location, remote mode, ATS source), pagination, and URL query synchronization.
   - `/jobs/[id]`: Comprehensive job detail view with interactive deterministic Match Panel, radial score gauges, blocker alerts, category breakdowns, and real-time SearchProfile switcher.
   - `/search-profiles`: Dedicated management interface for creating, viewing, and configuring search profiles.

---

## Authentication & Authorization Model

JobScope implements a scoped user identity pattern:
- **Authentication Header:** Client requests supply the candidate ID via the `X-User-Id` HTTP header (UUID format).
- **Development Environment (`ENVIRONMENT=development`):** If `X-User-Id` is omitted, the backend falls back to a deterministic development candidate (`00000000-0000-0000-0000-000000000001`) and ensures its User record exists.
- **Production configuration (`ENVIRONMENT=production`, `DEBUG=false`):** `X-User-Id` is required and must identify an existing user. Missing or unknown users receive `401`; malformed UUIDs receive `400`. Debug mode also enables the development fallback.

This header supplies user context; it is not verified authentication. JWT/OAuth and a trusted identity boundary remain future work. `GET /api/profile` auto-provisions the blank BaseProfile when needed.

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
│   │   ├── app/              # Next.js App Router pages (/, /jobs, /jobs/[id], /search-profiles)
│   │   ├── components/       # UI components (jobs, matching, search_profile, ui)
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
├── docker-compose.yml        # PostgreSQL 16 container setup
├── .env.example              # Environment variables template
└── pyproject.toml            # Python dependencies and tool configs
```

---

## Getting Started

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
   docker compose up -d
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
| **Applications** | `/api/applications` | GET, POST | List or create tracked applications (backend already implemented) |
| **Applications** | `/api/applications/{id}` | GET, DELETE | Retrieve or delete an application |
| **Applications** | `/api/applications/{id}/status` | PATCH | Transition status and append history |
| **Applications** | `/api/applications/{id}/notes` | PATCH | Update application notes |
| **Applications** | `/api/applications/{id}/history` | GET | Retrieve status history |

### Application Tracking Backend — COMPLETE

The backend supports tracking an existing job, listing/filtering/paginating the current user's applications, retrieving details, updating status or notes, and deleting a tracking record. Application Tracking frontend is **not implemented yet (FAZ 4)**.

- Creation defaults to `INTERESTED`; any valid explicit ApplicationStatus is accepted. Initial creation has no history entry because there is no previous application status.
- One application per `(job_id, user_id)` is enforced by PostgreSQL and the service. Duplicate tracking returns `409 APPLICATION_ALREADY_EXISTS`, including insert races.
- Every actual allowed status change writes history in the same request transaction. A failure rolls back status and history together. Concurrent status/notes edits lock and refresh the owned application before mutation.
- Same-status requests return `422 INVALID_STATUS_TRANSITION` and create no history. Existing transition policy is preserved:

  | Current status | Allowed next statuses |
  |---|---|
  | INTERESTED | APPLYING, APPLIED, REJECTED |
  | APPLYING | INTERESTED, APPLIED, REJECTED |
  | APPLIED | INTERVIEW, OFFER, REJECTED |
  | INTERVIEW | OFFER, REJECTED |
  | OFFER | REJECTED |
  | REJECTED | INTERESTED, APPLYING, APPLIED, INTERVIEW |

- Missing or another user's application returns `404 APPLICATION_NOT_FOUND` for detail, status, notes, deletion and history. Payload `user_id` is rejected; ownership comes from request context.
- Notes are optional, limited to 5,000 characters, and trimmed; null/blank notes clear the value. Notes edits create no status history.
- Detail embeds chronological history; `/history` exposes the same ordering by `changed_at`, then ID. Lists use status filtering and `limit` (1–100) / `offset` (non-negative), returning `items`, `total`, `limit`, `offset`.
- Job and Application statuses are independent: closing a job preserves an application in `INTERVIEW`. Explicitly deleting the application deletes its history; closing the job does neither.

### Planned Endpoints (Future Phases)
The following capabilities are specified in design documentation and scheduled for subsequent implementation phases:
- **Application Tracking frontend**: Backend routes already exist; the tracking UI and end-to-end workflow remain planned. No tracking functionality was added in Phase 0.
- **Profile frontend and match retrieval**: BaseProfile backend exists; a dedicated Profile UI and persisted match retrieval API remain planned.
- **AI Matching Analysis (`/api/matches/{id}/ai`)**: Deep qualitative LLM match evaluation and evidence extraction.
- **CV Import & Parse (`/api/cv/upload`, `/api/cv/{id}/approve`)**: PDF/DOCX resume parsing.
- **Manual Job Entry (`/api/jobs/manual`)**: User-submitted job URLs.
- **Scheduler, Ashby and Workday adapters**: Planned; only Greenhouse and Lever crawlers are implemented.

---

## Documentation

Detailed architecture specifications and design records are available in `docs/`:
- [MVP Technical Design](docs/design/01_mvp_technical_design.md): Architectural decisions and foundational choices.
- [Database & API Design](docs/design/02_database_and_api_design.md): Schemas, relational integrity, and API specs.
- [Data Model & Architecture](docs/design/03_data_model_and_architecture.md): Entity relationships and Clean Architecture boundaries.
