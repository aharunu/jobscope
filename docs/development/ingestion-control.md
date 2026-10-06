# Ingestion Control Center (A4)

Open `/ingestion` after applying the current migration and restarting the backend:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
```

The new migration is `0010_ingestion_control`, following `0009_ai_details`.
It adds ingestion policies, top-level runs, source runs and compact decisions.
Existing canonical tables and provider request contracts are unchanged.

## Running safely

Kariyer.net and `custom` registry entries are excluded from ingestion source/ATS/policy
selectors and from all-source runs because no acquisition adapter exists.
Explicit Kariyer.net/custom Source IDs return `422 INVALID_INGESTION_SCOPE`;
excluded ATS selections are also rejected with 422 (the request schema already
rejects `custom`). The Source Registry/catalog and previous run
history remain intact. An old preview containing those Sources must be replaced
with a new eligible preview.

1. Start with **Preview** and one existing Source. Select a Source or an ATS type;
   the all-sources scope uses the active-sources checkbox by default.
2. Choose saved policies or an override for this run. On first use, Turkey is
   suggested with unknown countries excluded. Nothing is saved or crawled
   automatically.
3. Inspect accepted/rejected decisions, coverage warnings and the policy snapshot.
4. Click **Persist this preview** beneath the completed preview when the decisions
   are suitable. Direct Persist mode remains available for runs without a preview.

Persist this preview starts a new acquisition, not a replay of the preview payload.
Preview stores compact decisions, not full descriptions/provider objects. The
backend reuses exactly the preview's Source IDs and frozen per-Source policy
snapshots, even if the form or saved policies have changed. Current Source runtime
configuration is used, so corrected provider URLs are respected. Live listings
and counts may differ. If an originally active-only Source is now inactive, the
request fails and requires a new preview instead of silently dropping it.
Only COMPLETED / COMPLETED_WITH_WARNINGS previews are eligible. Partial acquisition
warnings still suppress closure under the existing guards. The new run records
`from_preview_run_id` in its existing scope JSON; no additional migration is needed.

Preview performs real acquisition but writes only ingestion audit records.
SmartRecruiters and Workday previews acquire paginated listing records without
per-job detail calls. Deferred details are marked explicitly, and the source
warning `preview_details_deferred_until_persist` prevents those results being
mistaken for complete enriched acquisition. Preview country decisions use list
geography and may change when persist obtains richer location data. Persist
always re-acquires; an accepted deferred summary is rejected atomically with
`INGESTION_DETAILS_REQUIRED` rather than stored as a title-only Job.

During persist, these providers skip detail calls only for list records whose
known country is definitely outside the snapshotted policy. Such records still
appear in rejected audit decisions. Unknown countries are enriched before the
final policy decision. Unfiltered/direct crawls still acquire full descriptions.
The frozen ingestion policy can narrow provider list requests when unknown countries
are excluded: SmartRecruiters queries each selected country; Workday discovers the
board's own country facet IDs, then requests filtered pages. Unknown-country inclusion,
disabled/empty policies and ordinary direct crawls keep full-board acquisition.
Unsupported endpoints and unproven Workday facet mappings keep local filtering.
No SearchProfile input is used. See [provider country filtering](provider-country-filtering.md).

Workday retains the first trustworthy total when subsequent noninitial CXS pages
return `total=0` with postings. Numeric offsets, repeated-page detection, hard
page caps and the hosted-CXS incomplete coverage safeguard remain active.
The default page size remains 20: live 100-item requests to 3M, Accenture and HP
returned HTTP 400. No larger unsupported request size is used as a speed fix.
Workday posting identity is validated before enrichment using the same existing
posting-identity rule. Unmappable references are skipped with an incomplete
coverage warning; no detail request is spent on a record that cannot be projected.

If a source duration/request/byte budget is exhausted, validated observations
already acquired by these adapters can be retained as PARTIAL with
`acquisition_budget_exhausted_partial_results`. Empty snapshots, ordinary network
errors, malformed responses and task cancellation retain the existing failure
semantics. Partial and filtered acquisition never authorizes absence closure.
The source's owned timeout scope identifies duration exhaustion; timer rounding
cannot discard partial results, and unrelated early network timeouts cannot
release partial observations as a successful acquisition.
The one-second per-host operational minimum and source budgets are unchanged.

Acquisition runs at most three Sources concurrently. All tasks share the managed
SafeHttpClient, so requests to the same host still share its pacing lock and
Retry-After cooldown. Source advisory locks and the global ingestion lease remain
held. Each Source's result is ingested under one completion lock: canonical writes,
decision audit and aggregate updates remain serialized. Cancellation stops queued
Sources; up to three already-running Sources may finish their safe current work.
The run finishes only after those tasks release their Source guards. Unexpected
worker failure cancels and joins the remaining workers before releasing the lease.
The monitor may name one current Source; the source list shows all RUNNING units.
No Scheduler, distributed queue or new database schema is introduced.

Preview does not create/update Jobs, RawJobs, requirements, matches, applications,
or low-level CrawlRuns. Persist sends accepted DTOs through the existing
`JobIngestionService`. Rejected records contain only compact identifying audit
data; they create no RawJob or requirements. Unchanged accepted jobs retain the
existing RawJob persistence policy. Matching and AI are never automatically run.

Historical unwanted jobs are retained. A new filter is not a cleanup command.

The Jobs page's **Source Platform** filter includes all currently implemented ATS
providers and reads additional platform values from the Source Registry on mount
and when the tab becomes visible/focused again. Inactive Sources are included so
their historical jobs remain filterable. These are platform choices, not job
count facets; a platform may legitimately return zero jobs. Failed registry
refreshes retain existing choices and show a small refresh notice.

## Policies and country resolution

Policies use ISO 3166-1 alpha-2 country codes, normalized to uppercase and
deduplicated by the API. Precedence:

```
Explicit run override
    otherwise Source override
        otherwise global default
            otherwise no filter
```

A saved **disabled Source override overrides the global default with no filter**.
An enabled policy with an empty country list is also unfiltered. Removing a Source
override restores inheritance. An active country filter defaults to rejecting
unknown countries; the include-unknown checkbox explicitly changes that behavior.
Run overrides never modify saved policies. All selected policies and runtime
Source configurations are copied at run creation, so edits do not change an
already-running acquisition.

Country resolution uses:

1. Explicit reliable `DiscoveredJobDTO.country_code`.
2. Structured normalized `country_code` / `country` metadata.
3. Recognized country names/codes or deterministic Turkish location aliases.
4. Unknown.

All 81 Turkish provinces and Gebze are recognized, with Unicode normalization for
Turkish letters. Turkey, Türkiye, TR and remote-with-Turkey forms are supported.
Whole country/location fields containing ISO codes are case-insensitive and
trimmed: `tr` resolves to Turkey (`TR`), `es` to Spain (`ES`). Spain, España and
İspanya are supported aliases. Codes embedded in ordinary prose retain conservative
case-sensitive matching; for example, “work in Europe” is not interpreted as India.
Conflicting country names remain unknown. Remote, Worldwide, Anywhere, EMEA,
Europe and Global do not establish a country. Company/Source country, job titles,
SearchProfiles, network geocoding and raw provider payloads are not consulted.
Structured country metadata is retained where already supplied by
SmartRecruiters, Recruitee and Workable. Provider-side country query optimization
is documented in [provider country filtering](provider-country-filtering.md);
unsupported or unproven paths keep local filtering.
Non-Turkish city-only locations can remain unknown. This deliberately conservative
resolver can be expanded later with reviewed, unambiguous location data.

Decision reasons: `COUNTRY_ALLOWED`, `COUNTRY_NOT_ALLOWED`, `COUNTRY_UNKNOWN`,
`UNKNOWN_INCLUDED`, `NO_COUNTRY_FILTER`, `INVALID_DISCOVERED_JOB`.

## Closure and acquisition completeness

An active job-level country filter **always disables absence closure**, even on a
complete, warning-free board. Its recorded reason is
`INGESTION_POLICY_FILTER_ACTIVE`. Preview records `PREVIEW_MODE` and never calls
the lifecycle service. Unfiltered Persist uses the existing completeness,
partial/failure, ingestion-error and zero-result guards. No second closure
algorithm exists. `acquisition_complete` remains the adapter's assertion and is
independent of closure authorization and ingestion status.

Complete source success is `COMPLETED`; coverage or ingestion warnings result in
`PARTIAL`; fatal source failure is `FAILED`. A mixed top-level run becomes
`COMPLETED_WITH_WARNINGS`, while all-source failure becomes `FAILED`.

## Background execution and cancellation

`POST /api/ingestion/runs` returns `202` with a persisted run promptly. Bounded
in-process Source concurrency performs acquisition under shared host pacing,
with serialized short database finalization as described above. PostgreSQL advisory leases enforce
one active top-level run across workers and reuse existing per-Source exclusion.
A partial unique database index also prevents simultaneous active run records.
Busy requests return `409 INGESTION_RUN_BUSY`.

No ORM transaction stays open during provider calls. Only the existing dedicated
AUTOCOMMIT advisory connections remain held. Decisions, canonical persistence,
source results and progress commit atomically in a short source transaction.
Failures roll back that unit and are recorded using a fresh transaction.

Cancel records a durable timestamp, finishes the already-running safe Source
units, then marks queued units cancelled. Completed work remains valid. Shutdown uses the
same cooperative path. Crash/restart recovery marks stale active runs
`INTERRUPTED`; recovery must first acquire the top-level lease and cannot interrupt
a different live worker. Start also reconciles abandoned runs under that lease.

The UI polls every 1.5 seconds while active and stops on terminal status. Reload
restores run history and authoritative backend progress. Cancellation does not
abort an HTTP request or database transaction.

## API

| Method | Path | Purpose |
|---|---|---|
| GET / PUT | `/api/ingestion/policies/default` | Global policy (GET returns null if absent) |
| GET / PUT / DELETE | `/api/ingestion/policies/sources/{source_id}` | Source override |
| POST / GET | `/api/ingestion/runs` | Start / paginated history |
| GET | `/api/ingestion/runs/{run_id}` | Persisted totals and current progress |
| GET | `/api/ingestion/runs/{run_id}/sources` | Source statuses, snapshots, warnings, closure |
| GET | `/api/ingestion/runs/{run_id}/decisions` | Compact paginated decisions |
| POST | `/api/ingestion/runs/{run_id}/cancel` | Cooperative cancellation |

Start request:

```json
{
  "mode": "PREVIEW",
  "source_ids": ["<existing-source-uuid>"],
  "active_sources_only": true,
  "policy_mode": "OVERRIDE_SELECTED_SOURCES",
  "allowed_country_codes": ["TR"],
  "include_unknown_country": false
}
```

Omit `source_ids` / `ats_types` for all matching Sources. If both are provided,
their intersection is selected. Empty selections and unknown Source IDs fail
validation. `active_sources_only=false` allows explicitly selected inactive
Sources; it does not mutate their active flag. Arbitrary URLs are not accepted.

Decision query filters: `decision`, `source_id`, `reason`, `country`, `limit`
(1–200), `offset`. Run history accepts `limit` (1–100), `offset`.
Invalid essential job fields are rejected before canonical ingestion; unusable
URLs are not exposed in their decision records. Source warnings are compact
(first 50 plus the actual warning count). Raw exceptions and payloads are not
returned. Source runtime snapshots are not exposed in API responses.

The existing `/api/crawl/run` remains a low-level debugging path and does not
apply product ingestion policies. Use `/ingestion` for geographically controlled
ingestion. The existing local-development authentication posture is unchanged.

## Verification

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_ingestion_a4.py
.\venv\Scripts\python.exe -m ruff check .
.\venv\Scripts\python.exe -m ruff format --check .
$env:JOBSCOPE_REQUIRE_DATABASE='1'
.\venv\Scripts\python.exe -m pytest
```

From `frontend`: `npx tsc --noEmit`, `npm test`, `npm run build`.
Automated acquisition uses fake adapters; CI does not depend on public boards.
Live evidence and acceptance results are in the local A4 agent report.
Scheduler remains planned. The implemented [occurrence/dedup model](hybrid-deduplication.md)
and [provider-side country optimization](provider-country-filtering.md) extend the
original A4 scope without weakening its Preview or closure guarantees.
