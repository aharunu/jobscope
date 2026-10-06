# API reference

The running backend publishes its generated contract at [OpenAPI documentation](http://localhost:8000/docs). Routes and schemas are authoritative if a dated design/audit differs.

## Authentication & Authorization Model

JobScope implements a scoped user identity pattern:
- **Authentication Header:** Client requests supply the candidate ID via the `X-User-Id` HTTP header (UUID format).
- **Development Environment (`ENVIRONMENT=development`):** If `X-User-Id` is omitted, the backend falls back to a deterministic development candidate (`00000000-0000-0000-0000-000000000001`) and ensures its User record exists.
- **Production configuration (`ENVIRONMENT=production`, `DEBUG=false`):** `X-User-Id` is required and must identify an existing user. Missing or unknown users receive `401`; malformed UUIDs receive `400`. Debug mode also enables the development fallback.

This header supplies user context; it is not verified authentication. JWT/OAuth and a trusted identity boundary remain future work. `GET /api/profile` auto-provisions the blank BaseProfile when needed.

Match retrieval GET routes resolve this identity without provisioning a User or BaseProfile. In development an unknown identity receives an empty match collection; production still requires an existing user.

## REST API Endpoints

All application routes are served under `/api` (or at root for health checks):

| Category | Endpoint | Method | Description |
|---|---|---|---|
| **Health** | `/health` | GET | System liveness probe |
| **Health** | `/health/ready` | GET | Database connectivity readiness probe |
| **Jobs** | `/api/jobs` | GET | Paginated Logical Jobs with search/filter params; Source/ATS filters include alternate occurrences |
| **Jobs** | `/api/jobs/{id}` | GET | Logical job, requirements and compact occurrences; retired IDs resolve the survivor |
| **Dedup** | `/api/dedup/candidates` | GET | Paginated pending review pairs, scores and signals |
| **Dedup** | `/api/dedup/candidates/{id}` | GET | Side-by-side candidate details |
| **Dedup** | `/api/dedup/candidates/{id}/merge` | POST | Atomic manual merge; requires `{"confirm": true}` |
| **Dedup** | `/api/dedup/candidates/{id}/keep-separate` | POST | Persist a durable separate resolution |
| **Sources** | `/api/sources` | GET | List registered ATS and career sources |
| **Sources** | `/api/sources/stats` | GET | Sources breakdown and health summary |
| **Sources** | `/api/sources/sync` | POST | Sync sources from canonical Markdown catalog into DB |
| **Sources** | `/api/sources/probe` | POST | Execute batch source health probes |
| **Sources** | `/api/sources/{id}` | GET, PATCH | Retrieve or update a source |
| **Sources** | `/api/sources/{id}/status` | PATCH | Update source active status |
| **Sources** | `/api/sources/{id}/probe` | POST | Probe specific source health |
| **Ingestion** | `/api/ingestion/runs` | POST / GET | Start background preview/persist; `from_preview_run_id` persists a completed preview through fresh acquisition |
| **Ingestion** | `/api/ingestion/runs/{id}` | GET | Persisted progress and counters |
| **Ingestion** | `/api/ingestion/runs/{id}/sources` | GET | Per-Source acquisition, policy and closure audit |
| **Ingestion** | `/api/ingestion/runs/{id}/decisions` | GET | Paginated accepted/rejected decisions |
| **Ingestion** | `/api/ingestion/runs/{id}/cancel` | POST | Cooperative cancellation |
| **Ingestion** | `/api/ingestion/policies/default` | GET / PUT | Global geographic policy |
| **Ingestion** | `/api/ingestion/policies/sources/{id}` | GET / PUT / DELETE | Source policy override |
| **Crawl** | `/api/crawl/run` | POST | Low-level crawl/debug path; does not apply ingestion policies |
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
