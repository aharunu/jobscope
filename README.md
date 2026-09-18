# JobScope

Personal Job Intelligence & Decision Support System.

JobScope converts the job search and matching process into a transparent, measurable, and evidence-based decision support system.

## Stack

- **Language:** Python >= 3.11
- **Framework:** FastAPI
- **Database:** PostgreSQL 16 + SQLAlchemy 2.x
- **Migrations:** Alembic
- **Testing:** pytest + pytest-asyncio + httpx
- **Code Quality:** Ruff (linting & formatting)
- **Architecture:** Modular Monolith (Clean / Hexagonal boundaries)

---

## Local Development Setup

Follow these steps to set up and run the project locally:

### 1. Create Virtual Environment

```powershell
# Create a virtual environment using Python 3.11+
python -m venv venv

# Activate the virtual environment
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```powershell
# Install JobScope in editable mode with development & test dependencies
pip install -e ".[dev]"
```

### 3. Configure Environment Variables

```powershell
# Copy the safe example configuration template
cp .env.example .env
```

Review `.env` and adjust database credentials or ports if necessary. Note that `.env` is excluded from Git to prevent secret leaks.

### 4. Start Local PostgreSQL Database

```powershell
# Start local PostgreSQL container via Docker Compose
docker compose up -d

# Verify container status
docker compose ps
```

### 5. Run Database Migrations (Optional / when revisions exist)

```powershell
alembic upgrade head
```

### 6. Run the Application

```powershell
# Start the development server with auto-reload
uvicorn backend.interfaces.api.main:app --reload --port 8000
```

Verify service status:
- **Process Liveness:** `curl http://127.0.0.1:8000/health` (HTTP 200)
- **Database Readiness:** `curl http://127.0.0.1:8000/health/ready` (HTTP 200 if connected, HTTP 503 if disconnected)

### 7. Run Tests and Quality Checks

```powershell
# Run the automated test suite
pytest -v

# Run Ruff linter checks
ruff check .

# Check code formatting
ruff format --check .
```

---

## Developer Automation CLI (`scripts/dev.py`)

A lightweight, zero-dependency developer task runner is included:

```powershell
# Run all checks (format check, lint, and tests)
python scripts/dev.py check

# Run tests
python scripts/dev.py test

# Run linter (with optional auto-fix)
python scripts/dev.py lint
python scripts/dev.py lint --fix

# Run code formatter
python scripts/dev.py format

# Start local dev server
python scripts/dev.py run --port 8000

# Run database migrations
python scripts/dev.py migrate
```

---

## Documentation

Detailed architecture and design specifications are located in the [docs/design/](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design) directory:

- [01_mvp_technical_design.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/01_mvp_technical_design.md): 45-point MVP technical design and architecture decisions.
- [02_database_and_api_design.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/02_database_and_api_design.md): Database schemas, constraints, and REST API specification.
- [03_data_model_and_architecture.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/03_data_model_and_architecture.md): ER relationships, SQLAlchemy models, and Clean Architecture abstractions.

Agent-generated implementation plans and execution walkthroughs are stored under `docs/agent-reports/` (local and git-ignored).
