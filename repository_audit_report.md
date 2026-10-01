# Repository Audit Report — JobScope

**Date:** 2026-10-01  
**Auditor:** Senior Architecture Review  
**Repository:** `c:\Users\aharu\Documents\GitHub\jobscope`

---

## 1. Executive Summary

**JobScope** is a personal job intelligence and evidence-based decision support system. It ingests job listings from multiple ATS providers (Greenhouse, Lever), normalizes requirements, and computes deterministic match scores against structured candidate profiles.

### What Is Already Implemented
- Clean/Hexagonal Architecture backend with well-separated domain, application, infrastructure, and interface layers
- PostgreSQL persistence with 6 Alembic migrations, 11+ ORM models, and bidirectional domain⟷ORM mapping
- Multi-ATS crawl engine with Greenhouse and Lever adapters, safe HTTP client with SSRF protection and retry logic
- Deterministic match engine with 6 category evaluators (Role, Skills, Experience, Education, Location, Other)
- Full profile management (BaseProfile, SearchProfile) with child entities (Skills, Experiences, Education, Projects)
- Source registry, health probing, Markdown catalog parser, and crawl history auditing
- Job lifecycle management with safe absence-based closure and completeness evaluation
- Next.js 15 frontend with job discovery board, job detail + match panel, and search profile management
- **648 backend tests** and **55 frontend tests**

### Most Important Problems
1. **`.env` file committed to Git** with real database password (`147147`)
2. **No `.env.example`** file — setup instructions in README reference a missing file
3. **No CI/CD pipeline** — no GitHub Actions, no automated quality gate
4. **Application Tracking** domain is fully modeled (domain entities, ORM models, migrations) but has zero application services, zero API endpoints, and zero tests
5. **LLM integration** and **CV parsing** infrastructure are empty scaffolds with no implementation
6. **Ashby and Workday** ATS adapters are empty `__init__.py` stubs despite being listed in README

### What Is Missing
- Application tracking API and services (domain fully modeled but zero business logic)
- AI/LLM analysis layer (entities + ORM models exist, no implementation)
- CV upload and parsing functionality (entity + model + migration exist, no service/API)
- Ashby and Workday crawl adapters (empty packages)
- Authentication system (X-User-Id header only, no actual auth)
- `.env.example` template

### Technical Debt
- 2 empty application packages (`application_tracking`, `job_matching`) creating organizational confusion
- Docker Compose only provisions PostgreSQL — no backend/frontend containerization
- No structured logging (JSON) for production observability
- Matching exceptions don't extend `JobScopeError`, creating inconsistent error handling

### What Should Be Done Next
1. Immediately remove `.env` from version control and create `.env.example`
2. Add CI/CD pipeline (GitHub Actions)
3. Implement Application Tracking services and API endpoints
4. Add Ashby/Workday adapters or remove from documentation

### Blockers
- No critical code blockers preventing continued development
- The committed `.env` with password is a security hygiene issue but does not block functionality

---

## 2. Repository Overview

### Structure

```text
jobscope/
├── backend/                        # Python backend (FastAPI + SQLAlchemy)
│   ├── domain/                     # 9 domain submodules
│   │   ├── application/            # Application tracking entities + enums
│   │   ├── crawl/                  # CrawlRun entities + enums + repository contracts
│   │   ├── cv/                     # CV entity + enums (no repository)
│   │   ├── job/                    # Job, RawJob, JobRequirement + repositories
│   │   ├── matching/               # MatchResult, evaluators, engine
│   │   ├── profile/                # BaseProfile + child entities + repositories
│   │   ├── search_profile/         # SearchProfile entity + repository
│   │   ├── source/                 # Source entity + repository
│   │   └── user/                   # User entity (minimal)
│   ├── application/                # 8 application service modules
│   │   ├── application_tracking/   # EMPTY — docstring only
│   │   ├── common/                 # Base exceptions
│   │   ├── job_discovery/          # Crawler orchestrator, adapter registry, ports
│   │   ├── job_matching/           # EMPTY — docstring only
│   │   ├── job_processing/         # Ingestion, normalization, lifecycle, extraction
│   │   ├── matching/               # MatchingService, exceptions
│   │   ├── profile_management/     # BaseProfile, child, search profile services
│   │   └── system/                 # Health service
│   ├── infrastructure/             # 8 infrastructure modules
│   │   ├── ats/                    # Greenhouse + Lever adapters, Ashby/Workday stubs
│   │   ├── config/                 # Pydantic Settings
│   │   ├── database/               # Engine, session, base, models, repos, migrations
│   │   ├── extraction/             # Deterministic requirement extractor + taxonomy
│   │   ├── http/                   # SafeHttpClient + SSRF protection
│   │   ├── llm/                    # EMPTY — docstring only
│   │   ├── logging/                # Logger setup with secret masking
│   │   └── parsers/                # Markdown source catalog parser
│   └── interfaces/
│       └── api/                    # FastAPI app, routes, schemas, dependencies
├── frontend/                       # Next.js 15 + React 19 + TypeScript
│   └── src/
│       ├── app/                    # Pages: /, /jobs, /jobs/[id], /search-profiles
│       ├── components/             # UI components (jobs, matching, search_profile, ui)
│       ├── lib/                    # API client, types, formatters
│       ├── styles/                 # globals.css design system
│       └── tests/                  # Vitest test suite
├── tests/                          # Backend pytest suite (68 test files)
├── scripts/                        # dev.py CLI runner
├── docs/
│   ├── design/                     # 3 design documents
│   └── agent-reports/              # 49 implementation walkthroughs
├── data/                           # turkish-job-sources.md catalog (451KB)
├── docker-compose.yml              # PostgreSQL 16
├── pyproject.toml                  # Python project + dependencies
└── alembic.ini                     # Migration config
```

### Key Metrics

| Metric | Count |
|--------|-------|
| Backend Python source files | ~80+ |
| Frontend TypeScript/TSX files | ~30+ |
| Backend test files | 68 |
| Frontend test files | 12 |
| Backend tests (claimed) | 648 |
| Frontend tests (claimed) | 55 |
| Alembic migrations | 6 |
| ORM models | 11+ |
| Domain entities | 14+ |
| API route modules | 7 |
| ATS adapters (implemented) | 2 (Greenhouse, Lever) |
| ATS adapters (stub) | 2 (Ashby, Workday) |
| Design documents | 3 |
| Agent implementation reports | 49 |

---

## 3. Architecture Overview

JobScope follows a **Modular Monolith** with **Clean/Hexagonal Architecture** principles. The layering is well-implemented:

```text
                    ┌────────────────────────────┐
                    │     Next.js Frontend       │
                    │  (React 19, App Router)    │
                    └─────────┬──────────────────┘
                              │ /api/* rewrite proxy
                              ▼
                    ┌────────────────────────────┐
                    │   FastAPI API Layer         │
                    │  (routes, schemas, DI)      │
                    │  interfaces/api/            │
                    └─────────┬──────────────────┘
                              │ Depends()
                              ▼
                    ┌────────────────────────────┐
                    │  Application Services       │
                    │  (orchestration, use cases) │
                    │  application/               │
                    └────┬─────────────┬─────────┘
                         │             │
              ┌──────────▼──┐    ┌─────▼──────────┐
              │ Domain Layer│    │ Infrastructure  │
              │ (entities,  │    │ (SQLAlchemy,    │
              │  evaluators,│    │  ATS crawlers,  │
              │  repository │    │  HTTP client,   │
              │  protocols) │    │  config)        │
              │ domain/     │    │ infrastructure/ │
              └─────────────┘    └────────┬───────┘
                                          │
                                          ▼
                                 ┌────────────────┐
                                 │  PostgreSQL 16  │
                                 │  (Docker)       │
                                 └────────────────┘
```

### Architectural Patterns Used
- **Repository Pattern** (Protocol-based interfaces in domain, SQLAlchemy implementations in infrastructure)
- **Dependency Injection** via FastAPI `Depends()` with typed annotated aliases
- **Application Factory** (`create_app()`)
- **Adapter Pattern** for ATS crawlers (ATSAdapter Protocol → Greenhouse/Lever implementations)
- **DTO Pattern** for cross-layer data transfer
- **Domain→ORM Mapping** via `to_domain()` / `from_domain()` methods on ORM models
- **Lifespan Management** for engine, HTTP client, adapter registry

---

## 4. Actual System/Data Flow

### Crawl & Ingestion Flow
```text
API POST /api/crawl/run
  ↓
CrawlerOrchestrator
  ↓  ← resolves Source from SourceRepository
ATSAdapter (Greenhouse/Lever)
  ↓  ← SafeHttpClient (SSRF validation + retries)
DiscoveredJobDTO[]
  ↓
CrawlPersistenceManager (transaction boundaries)
  ↓
JobIngestionService
  ├→ JobNormalizer.normalize()
  ├→ Deduplication (source_id + external_job_id or canonical_url)
  ├→ JobRepository.save()
  ├→ RawJobRepository.save()
  ├→ RequirementExtractionService.extract_and_persist()
  ├→ CrawlRunRepository.record_job_action()
  └→ JobLifecycleService.close_absent_jobs() [if eligible]
  ↓
JobIngestionResultDTO → CrawlRunResponse
```

### Match Evaluation Flow
```text
API POST /api/matches
  ↓ (job_id, search_profile_id, user_id)
MatchingService
  ├→ JobRepository.get_job_detail()  [with requirements]
  ├→ BaseProfileRepository.get_by_user_id()  [ownership check]
  ├→ SearchProfileRepository.get_by_id_and_base_profile_id()  [ownership chain]
  └→ DeterministicMatchEngine.evaluate()
       ├→ RoleEvaluator
       ├→ SkillEvaluator
       ├→ ExperienceEvaluator
       ├→ LocationEvaluator
       ├→ EducationEvaluator
       └→ OtherRequirementEvaluator
  ↓
MatchResult (weighted scores, blockers, explanations)
  ↓
MatchResultRepository.save()  [idempotent upsert]
  ↓
MatchResultResponse → Frontend MatchPanel
```

### Job Discovery UI Flow
```text
Frontend GET /api/jobs?q=...&company=...&work_mode=...
  ↓ (Next.js rewrite proxy)
Backend GET /api/jobs
  ↓
JobQueryService.list_jobs(JobFilterDTO)
  ↓
JobRepository.list_jobs() + count_jobs()
  ↓
JobListResponse → JobList → JobCard[]

Frontend GET /api/jobs/{id}
  ↓
JobQueryService.get_job()
  ↓
JobDetailResponse → JobDetailClient
                   ├→ JobDetailHeader
                   ├→ JobDetailBody
                   └→ MatchPanel
                      ├→ ScoreGauge
                      ├→ BlockerAlert
                      ├→ CategoryScoresBreakdown
                      ├→ SkillsEvidenceList
                      └→ RequirementMatchesList
```

---

## 5. Implementation Status

| Subsystem | Status | Evidence |
|-----------|--------|----------|
| **Source Registry & Management** | COMPLETE | Full CRUD, probe, sync, Markdown parser, 8+ test files |
| **Greenhouse ATS Adapter** | COMPLETE | 13.7KB adapter, 29KB test file, integration tests |
| **Lever ATS Adapter** | COMPLETE | 11.9KB adapter, 14.8KB test file |
| **Ashby ATS Adapter** | MISSING | Empty `__init__.py` (33 bytes, docstring only) |
| **Workday ATS Adapter** | MISSING | Empty `__init__.py` (35 bytes, docstring only) |
| **Job Ingestion & Normalization** | COMPLETE | JobIngestionService, JobNormalizer, content cleaning, lifecycle |
| **Requirement Extraction** | COMPLETE | DeterministicRequirementExtractor + taxonomy |
| **Job Query & Discovery** | COMPLETE | JobQueryService, list/detail with filters + pagination |
| **Deterministic Match Engine** | COMPLETE | 6 evaluators, weighted scoring, blocker detection, explanations |
| **Match Persistence & API** | COMPLETE | Save, calculate, retrieve endpoints |
| **BaseProfile Management** | COMPLETE | Full CRUD for profile + skills + experiences + education + projects |
| **SearchProfile Management** | COMPLETE | Full CRUD + ownership enforcement |
| **User Ownership / Auth** | MOSTLY COMPLETE | X-User-Id header, dev fallback, user seeding; no real auth |
| **Application Tracking** | SKELETAL | Domain entities + enums + ORM model + migration exist; zero services, zero API, zero tests |
| **CV Upload & Parsing** | SKELETAL | Domain entity + enums + ORM model + migration exist; no service, no API, no parsing logic |
| **LLM/AI Analysis** | SKELETAL | Domain entities (AIAnalysis, AIEvidence) + ORM models exist; infrastructure/llm/ is empty |
| **Crawl History & Observability** | COMPLETE | List/detail/job-actions endpoints with filtering + pagination |
| **Job Lifecycle Closure** | COMPLETE | Safe absence-based closure with 5 invariant checks |
| **Frontend Job Board** | COMPLETE | /jobs page with search, filters, pagination, URL sync |
| **Frontend Job Detail + Match** | COMPLETE | /jobs/[id] with MatchPanel, gauges, breakdowns |
| **Frontend Search Profiles** | COMPLETE | /search-profiles list + /new creation form |
| **Frontend Profile Page** | MISSING | No /profile page; backend API exists but no UI |
| **Health Checks** | COMPLETE | Liveness + readiness probes |
| **Database Migrations** | COMPLETE | 6 migrations covering all current tables |

---

## 6. Architecture Review

### Strengths
The architecture is genuinely well-implemented for a project of this scale. The Clean Architecture boundaries are consistently maintained:

- **Domain layer** contains only pure Python dataclasses and Protocol interfaces — no SQLAlchemy, no FastAPI imports
- **Application services** orchestrate domain logic without infrastructure dependencies
- **Infrastructure** implements domain protocols without leaking into upper layers
- **Dependency direction** consistently flows inward: interfaces → application → domain ← infrastructure

### Architectural Violations

**Violation 1: Matching exceptions bypass `JobScopeError` hierarchy**

| Aspect | Detail |
|--------|--------|
| **Location** | [`backend/application/matching/exceptions.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/matching/exceptions.py) |
| **Problem** | `MatchingError`, `JobNotFoundError`, `SearchProfileNotFoundError`, `BaseProfileNotFoundError` extend plain `Exception`, not `JobScopeError` |
| **Principle** | Liskov Substitution / consistency |
| **Consequence** | These exceptions are caught manually with `HTTPException` in [`routes/matching.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/interfaces/api/routes/matching.py#L49-L63) instead of being handled by the centralized `jobscope_error_handler` |
| **Fix** | Extend `JobScopeError` with appropriate `status_code` and `code` attributes |

**Violation 2: Empty application packages create false organization**

| Aspect | Detail |
|--------|--------|
| **Location** | `application/application_tracking/__init__.py` (46 bytes), `application/job_matching/__init__.py` (40 bytes) |
| **Problem** | Empty packages suggest functionality that doesn't exist |
| **Consequence** | Developer confusion about where matching and tracking logic lives |
| **Fix** | Either implement services or remove packages until needed |

**Violation 3: CrawlPersistenceManager creates infrastructure objects in infrastructure layer**

| Aspect | Detail |
|--------|--------|
| **Location** | [`crawl_persistence.py:110-123`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/crawl_persistence.py#L110-L123) |
| **Problem** | `execute_ingestion()` directly instantiates `JobNormalizer()`, `DeterministicRequirementExtractor()`, and all repositories — acting as a mini composition root |
| **Consequence** | Hard to override dependencies for testing; tight coupling |
| **Fix** | Accept pre-configured `JobIngestionService` or use factory injection |

---

## 7. Domain Model Review

### Entities Assessment

The domain model is well-structured with pure Python dataclasses using `slots=True`:

| Entity | Quality | Notes |
|--------|---------|-------|
| `Job` | Good | Rich attributes, proper status tracking |
| `RawJob` | Good | Immutable audit trail for raw content |
| `JobRequirement` | Good | Type, level, importance, criticality, evidence |
| `Source` | Good | Comprehensive config fields (adapter, pagination, rate limit, endpoint) |
| `CrawlRun` | Good | Full audit counters |
| `CrawlRunJob` | Good | Action-level audit linking |
| `BaseProfile` | Good | Proper aggregate root with child collections |
| `ProfileSkill/Experience/Education/Project` | Good | Proper child entities |
| `SearchProfile` | Good | Clean separation from BaseProfile |
| `MatchResult` | Good | Detailed scoring with category breakdowns |
| `Application` | Good design, no implementation | Entity exists, no services use it |
| `User` | Minimal | Only `id` + timestamps; no profile data |
| `CV` | Skeletal | Entity exists, no processing logic |

### Business Logic Placement
Business logic is correctly concentrated in:
- **Domain evaluators** (matching scoring logic)
- **Application services** (orchestration, ownership enforcement, lifecycle rules)
- **Domain normalization** (URL normalization, source normalization)

> [!NOTE]
> No business logic leakage detected into controllers, ORM models, or infrastructure.

### Missing Domain Concepts
- **Application** domain has entities but no business rules or state machine logic
- **CV** domain has entity but no parsing, validation, or import rules
- **User** entity is extremely thin — no name, email, or preferences

---

## 8. Code Quality Review

### Structure — **Strong**
- Clear module boundaries with consistent naming
- Each domain submodule has `entities.py`, `enums.py`, and `repositories.py` (when applicable)
- Infrastructure repositories follow `SQLAlchemy{Entity}Repository` naming
- Application services follow `{Entity}Service` naming

### Maintainability — **Strong**
- Functions are well-scoped and reasonably sized
- Docstrings present on all public classes and methods
- Type annotations throughout (Python 3.11+ syntax: `str | None`, `list[X]`)
- Consistent use of `from __future__ import annotations`

### Correctness — **Adequate**
- Proper async/await throughout
- Transaction management with commit/rollback/close
- Content hash-based change detection for jobs
- Deduplication logic with proper precedence (external_id > canonical_url)

### Potential Issues

1. **Engine singleton with global mutable state** ([`engine.py:7`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/engine.py#L7)): `_engine` and `_session_factory` are module-level globals. Thread-safe for async but fragile for testing.

2. **Silent exception swallowing** in [`normalizer.py:184`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/normalizer.py#L184) and [`content_cleaning.py:100`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/content_cleaning.py#L100): `pass` in exception handlers — errors during date parsing and content cleaning are silently ignored without logging.

3. **Double engine disposal** in lifespan ([`main.py:53-56`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/interfaces/api/main.py#L53-L56)): `engine.dispose()` and `dispose_engine()` are both called, the second call accesses the global singleton which may already be None.

### Error Handling — **Mostly Good**
- Centralized `JobScopeError` hierarchy with structured error responses
- Global unhandled exception handler that doesn't leak internals
- Per-job error handling in crawl ingestion (individual failures don't crash batch)
- **Gap**: Matching exceptions don't participate in centralized handling

### Logging — **Adequate**
- `SecretMaskingFilter` redacts passwords and tokens from logs
- Important operations are logged (match completion, job closure, crawl results)
- **Gap**: No structured logging (JSON format) for production log aggregation
- **Gap**: Logging config uses `logging.basicConfig` which is not production-grade

---

## 9. Database & Persistence Review

### Schema Quality — **Strong**
- 6 well-structured migrations creating all tables
- Proper UUID primary keys with `gen_random_uuid()` server defaults
- `created_at` / `updated_at` timestamps with timezone awareness
- Foreign keys with appropriate `ON DELETE` actions (CASCADE for owned children, RESTRICT for sources)

### Indexes
- Source, company, title, status columns properly indexed on `jobs`
- FK columns have indexes for join performance
- `first_seen_at` indexed for chronological queries

### Constraints
- `uq_source_external_job_id` uniqueness on jobs
- `canonical_url` unique constraint
- `uq_match_results_job_base_search` composite uniqueness
- `uq_applications_job_user` uniqueness

### Potential Issues

1. **`external_job_id` nullable + unique constraint** ([`job.py:121-127`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/models/job.py#L121-L127)): The `UniqueConstraint("source_id", "external_job_id")` allows multiple NULL `external_job_id` entries per source in PostgreSQL (NULLs are considered distinct). This is correct behavior but worth documenting.

2. **No `location` index**: The `location` column on `jobs` is filterable via API but has no database index. This will become a performance issue at scale.

3. **No `work_mode` index**: Same issue — filterable but not indexed.

### ORM Mapping — **Strong**
- Consistent `to_domain()` / `from_domain()` pattern on all models
- Lazy relationship loading with explicit eager loading when needed
- `expire_on_commit=False` to prevent detached instance issues

### Transaction Management — **Good**
- Session lifecycle properly managed via FastAPI dependency (`get_db_session`)
- CrawlPersistenceManager uses separate transactions for initial run creation and ingestion
- Independent failure transaction for marking crawl runs as FAILED

---

## 10. API Review

### Endpoints Inventory

| Method | Path | Auth | Status |
|--------|------|------|--------|
| GET | `/health` | No | Implemented |
| GET | `/health/ready` | No | Implemented |
| GET | `/api/jobs` | No | Implemented |
| GET | `/api/jobs/{id}` | No | Implemented |
| GET, POST | `/api/sources` | No | Implemented |
| POST | `/api/crawl/run` | No | Implemented |
| GET | `/api/crawl/runs` | No | Implemented |
| GET | `/api/crawl/runs/{id}` | No | Implemented |
| GET | `/api/crawl/runs/{id}/jobs` | No | Implemented |
| POST | `/api/matches` | Yes (X-User-Id) | Implemented |
| GET, PUT, PATCH | `/api/profiles/base` | Yes (X-User-Id) | Implemented |
| Various | `/api/profiles/base/skills/*` | Yes (X-User-Id) | Implemented |
| Various | `/api/profiles/base/experiences/*` | Yes (X-User-Id) | Implemented |
| Various | `/api/profiles/base/educations/*` | Yes (X-User-Id) | Implemented |
| Various | `/api/profiles/base/projects/*` | Yes (X-User-Id) | Implemented |
| GET, POST | `/api/search-profiles` | Yes (X-User-Id) | Implemented |
| GET, PUT, DELETE | `/api/search-profiles/{id}` | Yes (X-User-Id) | Implemented |

### API Quality Assessment
- **Naming**: Consistent RESTful conventions
- **Validation**: Pydantic schema validation on request/response
- **Pagination**: Bounded with configurable `limit` (max 100) and `offset`
- **Filtering**: Multi-attribute filtering on jobs and crawl runs
- **Error responses**: Structured `{"error": {"code": ..., "message": ...}}` format

### Issues

1. **README documents `/api/v1/` prefix** but actual implementation uses `/api/` without versioning. The `v1` prefix does not exist.

2. **README lists `POST /api/v1/crawl/trigger`** but actual endpoint is `POST /api/crawl/run`. Different path and name.

3. **README lists `GET /api/v1/matches/job/{job_id}`** for fetching persisted match — this endpoint does not appear to exist in the codebase.

4. **Crawl endpoint is not authenticated**: Anyone can trigger crawls. For a personal tool this may be intentional, but `POST /api/crawl/run` could be expensive.

---

## 11. Testing Review

### Test Coverage — **Strong**

The test suite is extensive with 68 backend test files covering:

| Test Area | Files | Quality |
|-----------|-------|---------|
| Domain models | `test_job_and_source_models.py`, `test_cv_models.py`, `test_matching_and_application_models.py`, `test_profile_models.py`, `test_crawl_run_models.py` | Thorough entity construction and invariant tests |
| Repository implementations | `test_job_repository.py`, `test_source_repository.py`, `test_crawl_run_repository.py`, etc. | Good mock-based unit tests |
| Application services | `test_job_ingestion_service.py`, `test_matching_persistence.py`, `test_search_profile_service.py`, etc. | Service orchestration tests |
| API routes | `test_job_api.py`, `test_crawl_api.py`, `test_matching_api.py`, `test_source_api.py`, etc. | HTTP-level integration tests |
| ATS adapters | `test_greenhouse_adapter.py`, `test_lever_adapter.py`, `test_greenhouse_crawler_integration.py` | Adapter-specific parsing tests |
| Regression tests | `test_job_company_location_filter_regression.py`, `test_job_description_cleaning_regression.py`, etc. | Bug prevention tests |
| Hardening | `test_crawl_pipeline_hardening.py`, `test_phase_6_hardening.py` | Edge case and failure path tests |
| Infrastructure | `test_http_safe_client.py`, `test_safe_http_client_retries.py`, `test_source_health_probe.py` | HTTP client and safety tests |
| Match engine | `test_deterministic_match_engine.py`, `test_requirement_extractor.py` | Core algorithm tests |

### Frontend Tests — **Adequate**

12 test files covering component rendering, user flows, and utility functions.

### Testing Gaps

1. **Application tracking** — zero test coverage (zero implementation)
2. **No database integration tests** against real PostgreSQL — all tests appear to use mocks
3. **No end-to-end tests** spanning frontend → backend
4. **No load/performance tests**

---

## 12. Security Review

### Confirmed Issues

**SEC-001: Database credentials committed to Git**

| Aspect | Detail |
|--------|--------|
| **Location** | [`.env:16`](file:///c:/Users/aharu/Documents/GitHub/jobscope/.env#L16) |
| **Evidence** | `DATABASE_URL=postgresql+asyncpg://jobscope:147147@localhost:5432/jobscope` — password `147147` committed |
| **Severity** | MEDIUM (local dev password, but `.env` should never be committed) |
| **Mitigation** | `.gitignore` includes `.env` but the file is already tracked |

**SEC-002: No `.env.example` file**

| Aspect | Detail |
|--------|--------|
| **Location** | Root directory |
| **Evidence** | README instructs `cp .env.example .env` but `.env.example` does not exist |
| **Severity** | LOW (documentation gap) |

### Likely Issues

**SEC-003: Docker Compose uses default password**

| Aspect | Detail |
|--------|--------|
| **Location** | [`docker-compose.yml:9`](file:///c:/Users/aharu/Documents/GitHub/jobscope/docker-compose.yml#L9) |
| **Evidence** | `POSTGRES_PASSWORD: jobscope` — should reference environment variable for production |
| **Severity** | LOW (acceptable for local dev) |

### Good Security Practices Observed
- **SSRF protection** with comprehensive IP/DNS validation ([`ssrf.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/http/ssrf.py))
- **Secret masking in logs** via `SecretMaskingFilter` ([`logger.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/logging/logger.py))
- **X-User-Id header validation** with UUID parsing and format check
- **Production auth enforcement** — rejects unauthenticated requests when `environment != development`
- **Global exception handler** that doesn't leak internal details
- **Frontend HTML sanitization** in `jobContent.ts` (XSS prevention)
- **`ondelete="RESTRICT"`** on source→job relationship prevents orphaned jobs

---

## 13. Performance Review

### Potential Bottlenecks

1. **Synchronous crawl execution**: `POST /api/crawl/run` performs all crawling synchronously in the request handler. With multiple sources, this can time out. This is acceptable for a personal tool but would need async task queue (Celery, etc.) for scale.

2. **N+1 query risk in job listing**: The `list_jobs` repository method loads jobs with their source relationships. If `joinedload` or `selectinload` is not consistently used, N+1 queries could occur.

3. **Missing indexes on filter columns**: `location` and `work_mode` are filterable via API but have no database indexes.

4. **DeterministicMatchEngine runs 6 evaluators sequentially**: Each evaluator processes requirements independently. For jobs with many requirements, this could be slow, though likely acceptable for a personal tool.

5. **Large raw content storage**: `raw_jobs.raw_content` stores full HTML in TEXT columns. Over time with many crawls, this table will grow significantly.

### Good Performance Practices
- `pool_pre_ping=True` on database engine
- Content hash-based change detection avoids unnecessary updates
- Bounded pagination on all list endpoints (max 100)
- `expire_on_commit=False` prevents unnecessary re-queries

---

## 14. Configuration Review

### Settings Architecture — **Good**
- Pydantic Settings with `.env` file support ([`settings.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/config/settings.py))
- Cached singleton via `@lru_cache` on `get_settings()`
- Database URL validation (`postgresql+asyncpg://` or `postgresql://`)
- Reasonable defaults for all settings

### Issues

1. **Missing `.env.example`**: README references it but it doesn't exist
2. **Hardcoded Alembic URL** in [`alembic.ini:17`](file:///c:/Users/aharu/Documents/GitHub/jobscope/alembic.ini#L17): `sqlalchemy.url = postgresql+asyncpg://jobscope:jobscope@localhost:5432/jobscope` — though it's noted as "overridden dynamically by env.py"
3. **`DEBUG=true` default**: Default `debug=True` in Settings means debug mode is on by default
4. **No environment validation**: No check that `ENVIRONMENT` is one of `development|test|production`
5. **`.env` password mismatch**: `.env` has `147147` but `docker-compose.yml` has `jobscope` as password

---

## 15. Dependency Review

### Backend Dependencies — **Clean**

| Package | Version | Purpose | Status |
|---------|---------|---------|--------|
| fastapi | ≥0.110.0 | Web framework | Appropriate |
| uvicorn[standard] | ≥0.28.0 | ASGI server | Appropriate |
| pydantic | ≥2.6.0 | Data validation | Appropriate |
| pydantic-settings | ≥2.2.0 | Configuration | Appropriate |
| sqlalchemy | ≥2.0.28 | ORM | Appropriate |
| asyncpg | ≥0.29.0 | PostgreSQL async driver | Appropriate |
| psycopg2-binary | ≥2.9.9 | PostgreSQL sync driver | For Alembic migrations |
| alembic | ≥1.13.0 | Migrations | Appropriate |
| python-dotenv | ≥1.0.1 | Env file loading | Appropriate |
| httpx | ≥0.27.0 | HTTP client | Appropriate |
| tzdata | ≥2024.1 | Timezone data | Appropriate |

**Dev dependencies**: pytest, pytest-asyncio, ruff — minimal and appropriate.

**Observation**: `httpx` is listed in both production and dev contexts (used by `SafeHttpClient` for crawling AND by test fixtures). This is correct — it's a runtime dependency.

### Frontend Dependencies — **Lean**

Only 3 production dependencies: `next`, `react`, `react-dom`.  
Dev dependencies: testing library, TypeScript, Vitest — all appropriate.

**No unnecessary dependencies detected.**

---

## 16. CI/CD & DevOps Review

### CI/CD — **Missing**

> [!WARNING]
> No GitHub Actions, no CI/CD configuration, no automated quality gate. Broken code can be pushed to any branch without checks.

### Docker — **Minimal**
- `docker-compose.yml` only provisions PostgreSQL
- No Dockerfile for backend or frontend
- No multi-service Docker Compose for full-stack development

### DevOps Tools
- `scripts/dev.py` provides a helpful CLI for `test`, `lint`, `format`, `run`, `migrate`, `check`
- No deployment scripts or documentation

---

## 17. Documentation Review

### README — **Good with Inaccuracies**

The README is comprehensive and well-structured, covering:
- Architecture overview
- Repository structure
- Setup instructions
- Testing commands
- API endpoint table
- Links to design docs

**Inaccuracies:**
1. **API paths use `/api/v1/`** but actual implementation uses `/api/` — no version prefix exists
2. **`POST /api/v1/crawl/trigger`** should be `POST /api/crawl/run`
3. **`GET /api/v1/matches/job/{job_id}`** endpoint does not exist
4. **`cp .env.example .env`** references non-existent file
5. **Ashby and Workday** listed as supported crawlers but only empty stubs exist

### Design Documents — **Thorough**
3 design documents in `docs/design/`:
- `01_mvp_technical_design.md` (24.9KB)
- `02_database_and_api_design.md` (23.9KB)
- `03_data_model_and_architecture.md` (22.6KB)

### Agent Reports — **Extensive**
49 implementation walkthroughs documenting development phases. These provide excellent traceability of design decisions but are gitignored (`docs/agent-reports/` in `.gitignore`).

---

## 18. Missing Features & Gaps

### GAP-001: Application Tracking (Services & API)

| Aspect | Detail |
|--------|--------|
| **Evidence** | Domain entities ([`application/entities.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/application/entities.py)), enums ([`application/enums.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/application/enums.py)), ORM models ([`models/application.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/models/application.py)), and migration exist. Empty `application/application_tracking/` package. |
| **What's Missing** | Application service, repository implementation, API routes, schemas, tests |
| **Where** | `application/application_tracking/services.py`, `infrastructure/database/repositories/application_repository.py`, `interfaces/api/routes/applications.py` |
| **Why It Matters** | Core use case — users need to track which jobs they've applied to |
| **Scope** | MVP (design docs suggest this is a core feature) |

### GAP-002: CV Upload & Parsing

| Aspect | Detail |
|--------|--------|
| **Evidence** | Domain entity ([`cv/entities.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/domain/cv/entities.py)), enums, ORM model ([`models/cv.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/models/cv.py)), migration exist. No service, no API, no parser. |
| **What's Missing** | File upload endpoint, CV parsing service, profile import logic |
| **Scope** | Future (useful but not blocking core workflow) |

### GAP-003: AI/LLM Analysis

| Aspect | Detail |
|--------|--------|
| **Evidence** | Domain entities `AIAnalysis`, `AIEvidence` with ORM models exist. `infrastructure/llm/` is empty. |
| **What's Missing** | LLM provider adapter, prompt engineering, AI scoring service |
| **Scope** | Future (deterministic engine is primary; AI is supplementary) |

### GAP-004: Ashby & Workday Adapters

| Aspect | Detail |
|--------|--------|
| **Evidence** | README lists 4 ATS providers. Only Greenhouse and Lever have implementations. `ats/ashby/` and `ats/workday/` contain only empty `__init__.py`. |
| **What's Missing** | Adapter implementations for these ATS platforms |
| **Scope** | Medium-term (expands job source coverage) |

### GAP-005: Frontend Profile Management Page

| Aspect | Detail |
|--------|--------|
| **Evidence** | Backend has full CRUD API for BaseProfile with skills, experiences, education, projects. Frontend has no `/profile` page. |
| **What's Missing** | Profile creation/editing UI |
| **Scope** | MVP (users need to set up their profile to use matching) |

### GAP-006: `GET /api/matches/job/{job_id}` Endpoint

| Aspect | Detail |
|--------|--------|
| **Evidence** | README documents this endpoint. No corresponding route handler exists. |
| **What's Missing** | Endpoint to retrieve persisted match result for a specific job |
| **Scope** | MVP (frontend match panel may need this for cached results) |

---

## 19. TODO / FIXME / HACK Review

**No TODO, FIXME, HACK, or XXX comments found** in the backend or frontend source code. The codebase is remarkably clean of technical debt markers.

The `pass` statements found are all legitimate:
- [`ssrf.py:69`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/http/ssrf.py#L69): Catch `ValueError` for non-IP hostnames — intentional flow control
- [`base.py:14`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/base.py#L14): Empty `DeclarativeBase` — standard SQLAlchemy pattern
- [`migrations/env.py:94`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/infrastructure/database/migrations/env.py#L94): Standard Alembic template
- [`normalizer.py:184`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/normalizer.py#L184): Silent date parsing failure (should log warning)
- [`content_cleaning.py:100`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/content_cleaning.py#L100): Silent content cleaning failure (should log warning)

---

## 20. Dead Code & Cleanup Opportunities

### Confirmed Unused / Empty Packages

| Package | Status | Evidence |
|---------|--------|---------|
| `application/application_tracking/` | Empty package | Only `__init__.py` with docstring |
| `application/job_matching/` | Empty package | Only `__init__.py` with docstring |
| `infrastructure/llm/` | Empty package | Only `__init__.py` with docstring |
| `infrastructure/ats/ashby/` | Empty package | Only `__init__.py` with docstring |
| `infrastructure/ats/workday/` | Empty package | Only `__init__.py` with docstring |

### Potentially Unused

| Item | Status | Evidence |
|------|--------|---------|
| `domain/cv/` | No references from application layer | Entity exists but no service or API uses it |
| `AIAnalysis`, `AIEvidence` domain entities | No active code references | ORM models exist but no service creates/reads them |
| `ApplicationModel`, `ApplicationStatusHistoryModel` | No repository or service uses them | Created in migration but no CRUD operations |

> [!IMPORTANT]
> These are not "dead code" — they are **planned features** with the data layer already built. They represent forward-looking architecture, not abandoned code.

---

## 21. Consistency Issues

### Harmless Inconsistencies
- Frontend uses `snake_case` for API type properties (matching backend JSON) — this is correct
- Some domain modules have `normalization.py` (source, matching) and some don't — acceptable, not all domains need normalization

### Problematic Inconsistencies

1. **Exception hierarchy split**: `ProfileNotFoundError` extends `JobScopeError` (centralized handling), but `MatchingError` extends plain `Exception` (manual HTTP exception mapping). This creates two parallel error handling paths.

2. **API prefix inconsistency**: README documents `/api/v1/` but code uses `/api/`. No versioning strategy is implemented despite documentation suggesting one.

3. **Password mismatch between `.env` and `docker-compose.yml`**: `.env` has `147147` as database password, `docker-compose.yml` has `jobscope`. One of them is wrong, or both need to be aligned.

4. **Crawl endpoint naming**: README says `POST /api/v1/crawl/trigger`, implementation is `POST /api/crawl/run`. Different verb and path.

---

## 22. Technical Debt Inventory

| ID | Location | Problem | Why It Exists | Impact | Risk | Priority | Category | Suggested Resolution |
|----|----------|---------|---------------|--------|------|----------|----------|----------------------|
| TD-001 | `.env` | Database password committed to Git | Oversight | Security hygiene violation | MEDIUM | **Critical** | Security | Remove from tracking, add `.env.example`, rotate password |
| TD-002 | Root | No CI/CD pipeline | Early-stage project | No automated quality gate | HIGH | **Critical** | Infrastructure | Add GitHub Actions for lint, test, build |
| TD-003 | `application/matching/exceptions.py` | Exceptions don't extend `JobScopeError` | Different author/phase | Two parallel error handling paths | MEDIUM | **High** | Code Quality | Refactor to extend `JobScopeError` |
| TD-004 | README | API paths don't match implementation | Documentation drift | Developer confusion, incorrect integration | MEDIUM | **High** | Documentation | Update README to match actual API paths |
| TD-005 | `application/application_tracking/` | Empty package | Planned, not implemented | False expectations | LOW | **Medium** | Code Quality | Implement or remove |
| TD-006 | `application/job_matching/` | Empty package | Planned, not implemented | Confusion with `application/matching/` | LOW | **Medium** | Code Quality | Remove — `matching/` already exists |
| TD-007 | `infrastructure/llm/` | Empty package | Planned, not implemented | No immediate impact | LOW | **Low** | Code Quality | Keep as marker for future work |
| TD-008 | `normalizer.py:184`, `content_cleaning.py:100` | Silent `pass` in exception handlers | Quick implementation | Debugging difficulty | MEDIUM | **Medium** | Code Quality | Add logging.warning |
| TD-009 | `crawl_persistence.py:110-123` | Hardcoded service composition | Expediency | Testing inflexibility | LOW | **Medium** | Architecture | Accept injectable service |
| TD-010 | `engine.py`, `session.py` | Global mutable singletons | FastAPI pattern | Test isolation challenges | LOW | **Low** | Architecture | Acceptable for current scale |
| TD-011 | Root | No `.env.example` | Oversight | New developer setup friction | LOW | **High** | Developer Experience | Create `.env.example` |
| TD-012 | `docker-compose.yml` / `.env` | Password mismatch | Configuration drift | Application cannot connect if wrong | MEDIUM | **High** | Configuration | Align passwords |
| TD-013 | `jobs` table | Missing indexes on `location`, `work_mode` | Not yet needed | Query performance at scale | LOW | **Low** | Database | Add indexes when performance degrades |
| TD-014 | `ats/ashby/`, `ats/workday/` | Documented but not implemented | Planned features | README inaccuracy | LOW | **Medium** | Documentation | Remove from README or implement |
| TD-015 | `infrastructure/logging/logger.py` | No structured JSON logging | Not prioritized | Production observability | LOW | **Low** | Infrastructure | Add JSON formatter for production |

---

## 23. Risk Register

| Risk | Evidence | Probability | Impact | Severity | Mitigation |
|------|----------|-------------|--------|----------|------------|
| Committed credentials rotated or used maliciously | `.env` file with password `147147` in Git history | LOW | MEDIUM | MEDIUM | Rotate password, use `.env.example`, clean Git history |
| Broken code pushed to main branch | No CI/CD pipeline | HIGH | MEDIUM | HIGH | Add GitHub Actions with lint+test gates |
| Crawl endpoint abuse (DoS/resource exhaustion) | `POST /api/crawl/run` is unauthenticated | LOW | MEDIUM | LOW | Add authentication or rate limiting |
| Data integrity issues from unaligned passwords | `.env` password differs from `docker-compose.yml` | MEDIUM | HIGH | MEDIUM | Align configuration files |
| False documentation leading to incorrect integrations | README API paths don't match actual routes | MEDIUM | LOW | LOW | Update documentation |
| Raw job content table growth | `raw_jobs` stores full HTML, no cleanup policy | MEDIUM | MEDIUM | MEDIUM | Add retention policy or compression |
| Match result orphaning on profile deletion | Cascade deletes propagate through profiles | LOW | LOW | LOW | Already handled by `ON DELETE CASCADE` |

---

## 24. What Should NOT Be Changed

1. **Clean Architecture layering**: The domain → application → infrastructure → interfaces separation is well-implemented and appropriate for this project's scale. Do not flatten or restructure.

2. **Repository Protocol pattern**: The use of `Protocol` interfaces in the domain layer with SQLAlchemy implementations in infrastructure is correct and clean.

3. **Domain entities as pure dataclasses**: No ORM coupling, no framework imports — this is exactly right.

4. **`to_domain()` / `from_domain()` mapping pattern**: Consistent bidirectional mapping between domain and ORM. Don't replace with automapping.

5. **DeterministicMatchEngine design**: Composable evaluators with weighted scoring and blocker caps. Clean, testable, explainable.

6. **Job lifecycle safety invariants**: The 5-rule `evaluate_crawl_completeness()` method prevents false mass-closures. This is well-thought-out defensive engineering.

7. **SafeHttpClient + SSRF validation**: Production-quality HTTP safety layer with retries, SSRF checks, and proper error handling.

8. **Frontend CSS design system**: Custom vanilla CSS with CSS variables, dark theme, glassmorphism — this is well-suited and avoids unnecessary framework dependencies.

9. **Test suite scope**: 648+ backend tests covering models, services, repositories, APIs, and regressions. This is excellent for the project's maturity.

10. **FastAPI dependency injection**: The `Annotated[X, Depends(get_x)]` pattern with typed aliases is clean and idiomatic.

---

## 25. Recommended Improvements

### Immediate

| Problem | Solution | Benefit | Complexity | Priority |
|---------|----------|---------|------------|----------|
| `.env` committed with password | Remove from Git tracking, add `.env.example`, rotate DB password | Security hygiene | Low | **Critical** |
| No CI/CD | Add GitHub Actions: `ruff check`, `ruff format --check`, `pytest`, `npm test`, `npm run build` | Automated quality gate | Low | **Critical** |
| README API paths incorrect | Update to match actual `/api/` prefix and correct endpoint names | Developer trust | Low | **High** |
| Password mismatch `.env` vs `docker-compose.yml` | Align to same password | Application connectivity | Low | **High** |
| Create `.env.example` | Template with placeholder values | Developer onboarding | Low | **High** |

### Short Term

| Problem | Solution | Benefit | Complexity | Priority |
|---------|----------|---------|------------|----------|
| Matching exceptions inconsistency | Refactor to extend `JobScopeError` | Unified error handling | Low | **High** |
| Silent `pass` in exception handlers | Add `logging.warning()` calls | Debuggability | Low | **Medium** |
| Empty `application/job_matching/` | Remove (redundant with `application/matching/`) | Reduce confusion | Low | **Medium** |
| Frontend Profile management UI | Build `/profile` page for BaseProfile CRUD | Complete user workflow | Medium | **High** |
| Missing `GET /api/matches/job/{job_id}` | Implement persisted match retrieval endpoint | Frontend cache support | Low | **Medium** |

### Medium Term

| Problem | Solution | Benefit | Complexity | Priority |
|---------|----------|---------|------------|----------|
| Application Tracking not implemented | Implement services, repository, API, UI | Core feature completion | Medium | **High** |
| Ashby/Workday adapters missing | Implement or remove from docs | Expanded job source coverage | Medium | **Medium** |
| No structured logging | Add JSON formatter for production mode | Observability | Low | **Medium** |
| Missing database indexes | Add indexes on `location`, `work_mode` | Query performance | Low | **Low** |
| Synchronous crawl execution | Add background task support (asyncio.create_task or task queue) | Non-blocking crawls | Medium | **Medium** |

### Long Term

| Problem | Solution | Benefit | Complexity | Priority |
|---------|----------|---------|------------|----------|
| AI/LLM Analysis layer | Implement LLM provider adapter | Enhanced match intelligence | High | **Low** |
| CV Upload & Parsing | Implement file upload + parsing pipeline | Automated profile creation | High | **Low** |
| Full-stack Docker Compose | Dockerize backend + frontend | Reproducible deployment | Medium | **Low** |
| Real authentication | Implement JWT/OAuth2 | Multi-user support | High | **Low** |
| Raw job content growth | Add retention policy or compression | Storage management | Low | **Low** |

---

## 26. Prioritized Roadmap

```text
Phase 1: Security & DevOps Foundation (Immediate)
├── 1.1 Remove .env from Git, create .env.example
├── 1.2 Align database passwords across configs
├── 1.3 Add GitHub Actions CI (lint + test + build)
└── 1.4 Fix README API documentation

Phase 2: Code Quality & Consistency (Short-term)
├── 2.1 Unify exception hierarchy (matching → JobScopeError)
├── 2.2 Add logging to silent exception handlers
├── 2.3 Remove empty application/job_matching/ package
└── 2.4 Add missing GET /api/matches/job/{job_id} endpoint

Phase 3: Feature Completion (Medium-term)
├── 3.1 Build frontend Profile management page (/profile)
├── 3.2 Implement Application Tracking (services → API → UI)
├── 3.3 Implement Ashby adapter (or remove from docs)
└── 3.4 Add structured JSON logging for production

Phase 4: Scale & Enhancement (Long-term)
├── 4.1 Background crawl execution (async tasks)
├── 4.2 CV upload and parsing
├── 4.3 AI/LLM analysis integration
├── 4.4 Real authentication (JWT/OAuth2)
└── 4.5 Full-stack Docker Compose
```

---

## 27. Critical Findings

### [CRITICAL-001] Database Password Committed to Version Control

**Problem:** `.env` file containing `DATABASE_URL=postgresql+asyncpg://jobscope:147147@localhost:5432/jobscope` is committed to Git.

**Location:** [`.env:16`](file:///c:/Users/aharu/Documents/GitHub/jobscope/.env#L16)

**Evidence:** File exists in repository. `.gitignore` includes `.env` (line 61), indicating intent to exclude it, but the file was already tracked before the rule was added.

**Impact:** Password exposed in Git history. If this is a public repository or shared, credentials are compromised.

**Recommended Action:**
```bash
git rm --cached .env
# Create .env.example with placeholder values
# Rotate the database password
# Consider git-filter-repo to remove from history
```

### [CRITICAL-002] No CI/CD Pipeline

**Problem:** No GitHub Actions, no automated checks of any kind. Any code can be pushed to any branch without lint, test, or build validation.

**Location:** Root directory — no `.github/workflows/` directory exists.

**Evidence:** `Get-ChildItem -Path ".github"` returns no results in the project root.

**Impact:** Code quality regression risk. Broken builds can reach main branch. 648 tests exist but nothing enforces running them.

**Recommended Action:** Create `.github/workflows/ci.yml` with ruff check, pytest, npm test, and npm run build steps.

---

### High Priority

**[HIGH-001]** README API documentation mismatch — `/api/v1/` paths, wrong endpoint names. Location: [`README.md:216-229`](file:///c:/Users/aharu/Documents/GitHub/jobscope/README.md#L216-L229)

**[HIGH-002]** Password mismatch between [`.env:16`](file:///c:/Users/aharu/Documents/GitHub/jobscope/.env#L16) (`147147`) and [`docker-compose.yml:9`](file:///c:/Users/aharu/Documents/GitHub/jobscope/docker-compose.yml#L9) (`jobscope`). Application will fail to connect if using wrong config.

**[HIGH-003]** Missing `.env.example` — setup instructions reference non-existent file. Location: [`README.md:122`](file:///c:/Users/aharu/Documents/GitHub/jobscope/README.md#L122)

**[HIGH-004]** Matching exceptions don't participate in centralized error handling. Location: [`application/matching/exceptions.py`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/matching/exceptions.py)

**[HIGH-005]** No frontend Profile management page despite full backend API. Users cannot set up their profile through the UI, which is required before matching can work.

---

### Medium Priority

**[MED-001]** Application Tracking domain fully modeled but zero implementation.

**[MED-002]** Silent exception handling in [`normalizer.py:184`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/normalizer.py#L184) and [`content_cleaning.py:100`](file:///c:/Users/aharu/Documents/GitHub/jobscope/backend/application/job_processing/content_cleaning.py#L100).

**[MED-003]** Empty `application/job_matching/` package creates confusion with existing `application/matching/`.

**[MED-004]** Ashby and Workday adapters documented as supported but are empty stubs.

---

### Low Priority

**[LOW-001]** No structured JSON logging for production.

**[LOW-002]** Missing database indexes on `location` and `work_mode` filter columns.

**[LOW-003]** LLM infrastructure package is empty scaffold.

**[LOW-004]** No full-stack Docker Compose for reproducible development.

---

## 28. Suggested Next Development Phase

```text
1. Fix .env security issue (remove from Git, create .env.example, align passwords)
   → Why now: Security hygiene, blocks nothing but should not be deferred
   → Depends on: Nothing
   → Unlocks: Safe sharing of repository

2. Add GitHub Actions CI pipeline
   → Why now: Prevents quality regressions as development accelerates
   → Depends on: Nothing
   → Unlocks: Confidence in pushing code

3. Fix README API documentation
   → Why now: Low effort, high trust impact
   → Depends on: Nothing
   → Unlocks: Accurate developer documentation

4. Unify matching exception hierarchy
   → Why now: Small refactor with outsized consistency benefit
   → Depends on: Nothing
   → Unlocks: Removes matching route's manual HTTPException mapping

5. Build frontend Profile management page (/profile)
   → Why now: Required for users to use matching feature
   → Depends on: Backend API (already complete)
   → Unlocks: Complete end-to-end matching workflow

6. Implement Application Tracking services and API
   → Why now: Domain model is ready; core user workflow
   → Depends on: Profile page (users need identity context)
   → Unlocks: Job application pipeline tracking

7. Add missing GET /api/matches/job/{job_id} endpoint
   → Why now: Frontend may need cached match results
   → Depends on: Matching service (already complete)
   → Unlocks: Match result caching in UI

8. Clean up empty packages and add logging to silent handlers
   → Why now: Low effort, improves maintainability
   → Depends on: Nothing
   → Unlocks: Cleaner codebase, better debugging
```

---

## 29. Final Assessment

| Dimension | Status | Explanation |
|-----------|--------|-------------|
| **Architecture** | **Strong** | Clean/Hexagonal architecture consistently maintained across all layers. Dependency direction is correct. Appropriate for project scale. |
| **Domain Design** | **Strong** | Rich domain model with proper entities, value-like objects, pure dataclasses. No ORM coupling. Well-separated business logic. |
| **Code Quality** | **Strong** | Consistent naming, comprehensive type annotations, docstrings, well-scoped functions. Minor issues with 2 silent exception handlers. |
| **Testing** | **Strong** | 648+ backend tests across models, services, repos, APIs, and regressions. 55 frontend tests. Comprehensive coverage. |
| **Security** | **Needs Attention** | SSRF protection and secret masking are excellent. `.env` committed with password is the main issue. Auth is placeholder. |
| **Database** | **Strong** | Well-designed schema with proper constraints, indexes, cascades, and migrations. Minor missing indexes on filter columns. |
| **Performance** | **Adequate** | Acceptable for personal tool. Synchronous crawling and missing filter indexes are future concerns. |
| **Documentation** | **Needs Attention** | Good README structure but contains API path inaccuracies, references non-existent `.env.example`, and lists unimplemented features. |
| **DevOps** | **Significant Gaps** | No CI/CD. Docker only for PostgreSQL. No deployment configuration. |
| **Maintainability** | **Strong** | Clean separation, consistent patterns, comprehensive tests, and extensive development documentation. |

> **Overall Assessment:** JobScope is a **well-engineered early-stage project** with strong architectural foundations, excellent test coverage, and a clean domain model. The primary gaps are operational (CI/CD, documentation accuracy, security hygiene) rather than architectural. The codebase is in good shape for continued development, with a clear path from current state to feature completion.
