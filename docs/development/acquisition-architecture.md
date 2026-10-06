# Current acquisition architecture

JobScope is the authoritative host/domain system. External crawler research can
inform endpoint binding, provider IDs and field mapping; it does not introduce a
second persistence, checkpoint, normalization or lifecycle implementation.
This is the durable decision from the acquisition comparison, updated to include
the implemented ingestion and occurrence model.

```text
Catalog parsing → Source Registry → RuntimeSourceDTO → ATSAdapterRegistry
    → Provider adapter → managed safe HTTP client → CrawlResultDTO
    → existing ingestion → normalization / occurrence identity / bounded dedup
    → RawJob / requirements / lifecycle / crawl and ingestion audit → PostgreSQL
```

Adapters return discovered jobs, complete individual raw provider objects,
metadata, coverage warnings and `is_complete`. They never write Jobs/RawJobs,
commit transactions, close occurrences, calculate matches, consult SearchProfiles
or change Applications. Source discovery belongs to catalog parsing/registry;
runtime config binds acquisition to the observed provider board.

## Coverage and failure

Completeness and run status are separate. Exhaustion, trustworthy totals and
accountable unique mapped identities must prove the provider population. Repeated
pages, skipped essential records, unknown continuation, caps and total mismatch
cannot become complete snapshots. Useful incomplete acquisition carries reasons
and may ingest as PARTIAL. Fatal failures provide no authoritative snapshot.
Bounded partial retention is supported only where the adapter explicitly accounts
for the acquired portion; it is never permission for absence closure.

Lever uses numeric offsets, with another exhaustion request after an exactly full
page. Greenhouse uses one documented `content=true` full-list request and reconciles
`meta.total`. See [their contracts](acquisition_a1.md) and
[the provider matrix](acquisition_a3.md). Hosted feeds with unproven board coverage
remain PARTIAL even when a public-board probe succeeds.

## HTTP, budgets and progress

The managed HTTP layer enforces HTTP(S), validated public destinations, TLS,
redirect checks, bounded bodies and source-wide request/byte/time budgets.
Read/search POST uses the same safety layer; it is not an arbitrary mutation API.
Each physical request participates in shared per-host pacing, including retries,
redirects, pages and details. `Retry-After` on 429/503 postpones later same-host
requests; 429 and read timeouts are not automatically retried.

Source-specific delays can increase waiting but cannot disable the shared minimum.
Waiting counts against the budget. DNS pinning and a distributed cross-process
rate limiter remain outside current implementation. See
[crawler foundation](acquisition_a2.md) and [pacing settings](acquisition_a3.md).

Product ingestion uses bounded Source concurrency, shared host pacing and short
database transactions. PostgreSQL admission protects the active top-level run and
each Source. Database finalization stays serialized within a run. No ORM transaction
is held across network acquisition. Progress, cancellation and crash recovery are
documented in [ingestion control](ingestion-control.md).

## Policies and data authority

Source/run country policy is independent of SearchProfile preferences.
SmartRecruiters can push countries into its list API; Workday resolves a board's
structured country facets conservatively. Unsupported/uncertain mappings retain
local filtering. Preview may defer costly details; accepted Persist observations
still require provider enrichment. See [country filtering](provider-country-filtering.md).

Preview writes audit/progress but no Job, occurrence, RawJob, requirement or dedup
candidate. Persisting a preview performs fresh acquisition under frozen policies;
provider populations can change between requests.

Occurrence identity remains Source-specific, preferably `(source_id, external_job_id)`.
A new Source observation can attach to a Logical Job only through the conservative
dedup rules or the narrowly proven same-provider alias identity contract. All Source
URLs and raw observations retain provenance. Rich canonical text/known values are
protected from incomplete enrichment. Meaningful change detection includes
employment, responsibilities and salary as well as title/description/location/work
mode/company; the old A1 four-field limitation has been superseded.

Only complete, warning-free, successful, unfiltered authoritative acquisition may
close absent Source occurrences, subject to the zero-result anomaly guard. A Logical
Job remains ACTIVE while any occurrence is ACTIVE. PARTIAL providers and filtered
ingestion suppress absence closure. Applications and matching belong to the
Logical Job and remain independent of crawler preferences and occurrence status.
See [hybrid deduplication](hybrid-deduplication.md) for atomic merge/conflict rules.

No external SQLite, JSONL, checkpoint or HTML viewer participates in this pipeline.
Historical comparison exports remain local evidence. Scheduler is not implemented.
Provider CI tests use mock transports/fake clients, not live boards.
