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
- **Development Environment (`ENVIRONMENT=development`):** If `X-User-Id` is omitted, the backend automatically falls back to a deterministic development candidate (`00000000-0000-0000-0000-000000000001`) and auto-provisions a blank `BaseProfile`.
- **Production Environment (`ENVIRONMENT=production`):** `X-User-Id` is strictly required. Unauthenticated or invalid requests receive a `401 Unauthorized` response.

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
   *(Verify PostgreSQL connection strings and ports in `.env`)*

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
   npm install
   ```

3. **Start the Next.js development server:**
   ```powershell
   npm run dev
   ```
   - **Web UI:** `http://localhost:3000`
   - **Job Discovery Board:** `http://localhost:3000/jobs`

> **Note on API Communication:** Next.js proxies all `/api/*` requests to the FastAPI backend (`http://127.0.0.1:8000/api/*`) via server rewrites defined in `next.config.mjs`. You do not need to configure CORS for local development.

---

## Testing & Quality Assurance

JobScope maintains an extensive test suite across both backend and frontend layers:

### Backend Testing (Pytest & Ruff)
```powershell
# Run all backend tests (700+ tests)
pytest -v

# Run linter
ruff check backend tests

# Check code formatting
ruff format --check backend tests
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
| **Sources** | `/api/sources/summary` | GET | Sources breakdown and health summary |
| **Sources** | `/api/sources/sync` | POST | Sync sources from canonical Markdown catalog into DB |
| **Sources** | `/api/sources/probe-all` | POST | Execute health probes across all active sources |
| **Sources** | `/api/sources/{id}/probe` | POST | Probe specific source health |
| **Crawl** | `/api/crawl/run` | POST | Trigger ingestion run for a source or all sources |
| **Crawl** | `/api/crawl/runs` | GET | List historical crawl runs |
| **Crawl** | `/api/crawl/runs/{id}` | GET | Get specific crawl run details |
| **Crawl** | `/api/crawl/runs/{id}/jobs` | GET | Discovered job audit records for a crawl run |
| **Crawl** | `/api/crawl/history` | GET | Crawl run history for a source |
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
| **Search Profiles** | `/api/search-profiles/{id}` | GET, PUT, DELETE | Retrieve, update, or remove a search profile |
| **Matching** | `/api/matches` | POST | Evaluate job against SearchProfile; returns deterministic score & evidence |

### Planned Endpoints (Future Phases)
The following capabilities are specified in design documentation and scheduled for subsequent implementation phases:
- **Application Tracking (`/api/applications`)**: KanBan/funnel tracking for job application stages.
- **AI Matching Analysis (`/api/matches/{id}/ai`)**: Deep qualitative LLM match evaluation and evidence extraction.
- **CV Import & Parse (`/api/cv/upload`, `/api/cv/{id}/approve`)**: PDF/DOCX resume parsing.
- **Manual Job Entry (`/api/jobs/manual`)**: User-submitted job URLs.

---

## Documentation

Detailed architecture specifications and design records are available in `docs/`:
- [MVP Technical Design](docs/design/01_mvp_technical_design.md): Architectural decisions and foundational choices.
- [Database & API Design](docs/design/02_database_and_api_design.md): Schemas, relational integrity, and API specs.
- [Data Model & Architecture](docs/design/03_data_model_and_architecture.md): Entity relationships and Clean Architecture boundaries.
