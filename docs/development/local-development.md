# Local development and verification

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
   alembic check
   ```
   Apply the latest migration before starting updated backend code. Revision
   `0011_hybrid_dedup` backfills one occurrence per existing Job without merging
   historical Jobs or changing their count. Docker startup applies migrations
   automatically; native development requires this step explicitly.

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

## Testing & Quality Assurance

JobScope maintains an extensive test suite across both backend and frontend layers:

### Backend Testing (Pytest & Ruff)
Run from the repository root after configuring PostgreSQL and running `alembic upgrade head`. Database integration fixtures use the application's `DATABASE_URL`; use a dedicated development/test database. Fixtures use rollback or explicit cleanup. Without a reachable migrated database, some integration tests skip. Set `JOBSCOPE_REQUIRE_DATABASE=1` locally, as CI does, to fail rather than skip required database coverage.

```powershell
# Run the complete backend suite, requiring PostgreSQL
$env:JOBSCOPE_REQUIRE_DATABASE = "1"
pytest -v

# Run linter
ruff check .

# Check code formatting
ruff format --check .
```

### Frontend Testing (Vitest & Next Build)
```powershell
cd frontend

# Run automated component & flow tests
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
