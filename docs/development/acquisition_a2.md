# Acquisition Foundation A2

The existing Lever and Greenhouse contracts remain unchanged. The crawler now
uses short Source-read sessions, then cross-worker PostgreSQL admission, a short
RUNNING transaction, bounded network acquisition, and atomic ingestion/finalization.
No migration or new provider is required.

## Safety configuration

| Environment setting | Default | Allowed range |
|---|---:|---:|
| CRAWLER_MAX_RESPONSE_BYTES | 15728640 (15 MiB) | 1024–67108864 |
| CRAWLER_MAX_SOURCE_REQUESTS | 1000 | 1–10000 |
| CRAWLER_MAX_SOURCE_BYTES | 134217728 (128 MiB) | 1024–1073741824 |
| CRAWLER_MAX_SOURCE_SECONDS | 300 | 1–3600 |

These are application Settings, not Source JSON overrides. Byte limits count
decoded response bodies, including error/retry/redirect bodies. Request counts
include physical connection attempts, retries and redirects. One source-local
budget spans all pages and any future detail calls; it cannot reset within an
acquisition. Duration covers the adapter call, including its delays and mapping,
but excludes Source loading and database ingestion. Async deadline enforcement
and monotonic checks complement the existing per-request timeout. Synchronous DNS
resolution and CPU-bound parsing are not preemptible; deadline checks reject
expired results when control returns. DNS pinning remains deferred.

SafeHttpClient.get retains its signature. New post_json(url, json=..., headers=...,
timeout=...) is exclusively for adapter-owned read/search operations. There is no
mutation HTTP API, unsafe option or provider bypass. GET/POST stream through the
same TLS/SSRF/timeout/retry layer. POST rejects 301/302/303 and cross-origin
redirects; same-origin 307/308 preserve JSON and method. Cross-origin GET drops
caller headers. Only existing connection failures and 502/503/504 are retried;
429/Retry-After and read-timeout retry remain deferred. Body/budget overflow fails
the source; acquired earlier pages are not ingested or treated as an empty board.
This bounds response payload retention, not the entire Python object heap.

## Admission and transactions

A dedicated AUTOCOMMIT PostgreSQL connection holds a session advisory lock keyed
by the signed first 64 bits of SHA-256(namespace + Source UUID bytes). This works
across API workers connected to the same database. A competing Source crawl
returns the existing aggregate response with SOURCE_CRAWL_BUSY and no run ID;
it creates no CrawlRun and does not contact a provider. Different Sources use
independent keys. The lock remains held through ingestion and failure recording,
then releases in finally; failed acquire/unlock invalidates the connection rather
than returning a possibly locked session to the pool.

The lock consumes one pool connection during acquisition, but holds no database
transaction. Ingestion needs an additional connection; size the pool accordingly
before introducing future broad concurrency. Direct standalone orchestrators can
inject the admission guard; production FastAPI wiring always supplies it. The
optional no-persistence/no-guard constructor remains for isolated unit tests.

Expected URL ownership conflicts are checked before mutation/flush, recorded as
JOB_URL_OWNERSHIP_CONFLICT, and skipped. Safe later items can commit; the run is
PARTIAL if any item succeeded, otherwise FAILED, and absence closure is disabled.
Source-scoped provider identity remains authoritative. There is no URL fallback
when a provider ID exists; the additional global URL lookup is a uniqueness
precheck, never identity reassignment or merging. Unexpected SQL failures,
including concurrent uniqueness races, abort the whole ingestion transaction.
Earlier writes roll back and a fresh transaction records FAILED. No savepoints
or attempts to continue with a poisoned session are introduced.

Pure deterministic extractor failures remain nonfatal warnings before requirement
persistence. Requirement database failures propagate and roll back the source.
Incomplete acquisition without an adapter warning now receives an explicit
acquisition_incomplete warning and becomes PARTIAL. Existing closure and empty-board
anomaly safeguards remain intact.

## Canonical observations

Meaningful comparison includes title, full description, responsibilities, location,
work mode, employment type, salary and company. Both stored and incoming effective
values are hashed with the same canonical JSON algorithm. An old stored hash alone
cannot produce an update; it is refreshed during ordinary UNCHANGED observation
without RawJob or requirement extraction. A URL change for the same provider
identity passes ownership checks and persists as UPDATED. Verified publication-only
changes update the date without RawJob, extraction or a fake content update.

Missing/empty optional enrichment preserves previous canonical values. Available
Source company remains authoritative fallback. Provider title/description presence
flags distinguish actual text from adapter fallback labels; missing descriptions
cannot replace rich text with raw JSON. There is no authoritative clear contract
in the two current providers, so none is invented. RawJob still stores the actual
incoming individual object only on create/update/reopen; it never contains the
merged effective canonical projection.

Run focused tests with pytest tests/test_acquisition_a2_http.py
tests/test_acquisition_a2_ingestion.py tests/test_acquisition_a2_database.py -q.
The database suite requires real PostgreSQL and cleans only its generated UUID
fixtures. CI must continue running JOBSCOPE_REQUIRE_DATABASE=1 pytest. No live ATS
requests are needed.
