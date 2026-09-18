# JobScope

Personal Job Intelligence & Decision Support System.

JobScope converts the job search and matching process into a transparent, measurable, and evidence-based decision support system.

## Stack

- **Language:** Python >= 3.11
- **Framework:** FastAPI
- **Database:** PostgreSQL + SQLAlchemy 2.x
- **Migrations:** Alembic
- **Testing:** pytest + pytest-asyncio + httpx
- **Architecture:** Modular Monolith (Clean / Hexagonal boundaries)

## Getting Started

### 1. Environment Setup

```powershell
# Create virtual environment (if not present)
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install project and development dependencies
pip install -e ".[dev]"
```

### 2. Configuration

Copy the example environment file and configure settings as needed:

```powershell
cp .env.example .env
```

### 3. Run Development Server

```powershell
uvicorn backend.interfaces.api.main:app --reload --port 8000
```

Verify the health check endpoint:
```powershell
curl http://127.0.0.1:8000/health
```

### 4. Running Tests

```powershell
pytest
```

## Documentation

Detailed architecture and design specifications are located in the [docs/design/](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design) directory:

- [01_mvp_technical_design.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/01_mvp_technical_design.md): 45-point MVP technical design and architecture decisions.
- [02_database_and_api_design.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/02_database_and_api_design.md): Database schemas, constraints, and REST API specification.
- [03_data_model_and_architecture.md](file:///c:/Users/aharu/Documents/GitHub/jobscope/docs/design/03_data_model_and_architecture.md): ER relationships, SQLAlchemy models, and Clean Architecture abstractions.

Agent-generated implementation plans and execution walkthroughs are stored under `docs/agent-reports/` (local and git-ignored).

