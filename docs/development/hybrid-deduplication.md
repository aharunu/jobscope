# Hybrid deduplication (A5)

## Authority and identity

A `Job` is the logical vacancy shown in job lists and used by matching and
applications. A `JobOccurrence` is one Source's published representation of that
vacancy. Adapters still return `DiscoveredJobDTO`; they do not deduplicate,
persist, close vacancies, or consult SearchProfiles.

```
Accepted A4 observation → source occurrence identity → bounded candidates
    → deterministic decision → logical Job + occurrence + raw observation
```

Occurrence identity is `(source_id, external_job_id)` when a provider ID exists.
For observations without an external ID, use the Source-specific canonical URL.
Database constraints enforce both source/external and source/URL uniqueness.
A conflicting Source URL cannot silently transfer ownership. Global URL equality
is evidence, not a global uniqueness constraint: uncertain cross-source postings
must be able to remain separate. A URL collision with a different company/title
retains the existing safe ingestion-conflict behavior.

`Job.source_id`, `external_job_id`, and `canonical_url` remain preferred-source
compatibility fields. All provider identities, alternate URLs, status, hashes,
first/last sightings, and original projections live on occurrences. Source and
ATS list filters use occurrence existence without duplicating logical rows.

## Candidate generation and concurrency

Company/title normalization uses Unicode NFKC, case folding, punctuation and
whitespace normalization. It preserves seniority, leadership terms and legal
suffixes. Exact normalized company/title form an indexed candidate block;
unmerged cross-source jobs are ordered by recency and ID. At most 50 candidates
are scored; a 51st row detects overflow and disables automatic attachment.
Same-source repeated roles are never compared as cross-source candidates.

PostgreSQL transaction advisory locks serialize only the relevant normalized
company/title namespaces. Ingestion acquires batch namespaces in sorted order,
then Source identity locks and occurrence/job row locks. Different namespaces
can progress independently. Uniqueness constraints remain the final identity
guard. Review uses the same namespace locks and ordered row locks. Applications
and match writes lock their logical Job, preventing writes into a concurrently
retired row. Transaction ownership remains outside repositories.

## Scoring and outcomes

| Signal | Weight |
|---|---:|
| Nonempty exact normalized company | 30 |
| Exact normalized title, including seniority | 30 |
| Exact known normalized location | 10 |
| Shared reliable employer reference OR identical posting URL | 20 |
| Substantial descriptions with token Jaccard similarity >= 0.80 | 10 |

Descriptions are substantial when each contains at least 40 distinct normalized
words after HTML/entity cleaning. Similarity alone never permits a merge.
Reliable references are explicitly supplied `requisition_id`, `requisitionId`
or `jobRequisitionId`. Provider posting IDs and Greenhouse `internal_job_id` are
not cross-provider employer references.

Contradictions override the score: different companies/titles, conflicting
references, different known locations/countries, incompatible known employment
or work mode, or substantial descriptions with similarity below 0.25 produce
`NEW_JOB`. A known publication distance over 180 days blocks automatic merging.
Missing dates neither prove nor contradict identity.

`AUTO_MERGE` requires score >= 90, company/title/location agreement, and a shared
reference or posting URL, with no contradiction. It attaches a **new occurrence**
to an existing Job; it does not merge historical Job rows. Exactly one candidate
must satisfy the rule. Candidate overflow, multiple known references, or multiple
automatic candidates demote to review. Company/title/location alone score 70;
even identical rich text only raises this to 80, still requiring review.

`REVIEW` creates a separate logical Job and a durable review candidate; ingestion
continues. `NEW_JOB` creates a separate Job without an unnecessary review pair.
Occurrence audit stores the outcome, score, signals and candidate count,
including negative evidence. Candidate UUID pairs are sorted and uniquely stored
for their entire lifetime, so reverse pairs and previously resolved
`KEEP_SEPARATE` pairs cannot reappear as new unresolved candidates.

These deliberately conservative gates were chosen after inspecting 667 local
jobs and 69 repeated company/title blocks. None were cross-source; repeated
generic roles and distinct locations demonstrated why basic equality is unsafe.
The dataset cannot establish measured positive-match precision or recall.
Cross-source true-positive behavior is tested with controlled fixtures. Revisit
calibration using reviewed real pairs before relaxing any gate.

## Canonical projection

The preferred Source owns title/company/preferred URL corrections. Alternate
Sources enrich missing responsibilities, employment, work mode, salary,
location and publication date; they do not erase existing known values with
nulls. Unknown/global location markers cannot replace a concrete location.
Alternate descriptions replace only when cleaned text is longer; ties preserve
preference. Title-only content is never projected over a description. A
substantial existing description cannot be replaced by a non-substantial one,
including a preferred-source observation. Otherwise preferred-source content
corrections remain supported. This is a deterministic richness policy, not
semantic text reconciliation.

Each occurrence retains its own normalized projection, resolved A4 country,
URL, hash and complete provider raw observation. The existing A2 meaningful
content hash remains authoritative; A5 does not introduce AI or hash redesign.
RawJob is written on occurrence create/update/reopen, not unchanged sightings.
It carries both logical `job_id` and `occurrence_id`, retaining Source provenance.

## Lifecycle and A4

An observed occurrence becomes ACTIVE and refreshes last_seen_at. Reopening an
occurrence reopens its logical Job. A logical Job is ACTIVE while any occurrence
is ACTIVE; it closes only after all occurrences have safely closed.

Only the existing complete, warning-free, successful, unfiltered authoritative
crawl gate may close missing ACTIVE occurrences of that Source. PARTIAL,
filtered A4 runs, errors, provider coverage warnings and the existing zero-result
anomaly guard suppress absence closure. Closing one Source's occurrence cannot
close a logical vacancy still exposed by another Source. CrawlRun continues to
audit logical actions, while occurrence timestamps/status preserve Source state.

A4 PREVIEW does not invoke occurrence persistence and creates no Job,
JobOccurrence, RawJob, Requirement or DedupCandidate. Preview-run bookkeeping is
unchanged. Persisting a preview still performs fresh acquisition under its
frozen policy; it is not an unchecked replay of provider payloads.

## Manual historical merge and preservation

Manual review is one outer transaction. Lock the pair and occurrences, verify
neither Job was already retired, then check Applications. If the same user has
an Application on both jobs, return `DEDUP_APPLICATION_CONFLICT` (409); delete
nothing. Otherwise prefer the Job containing an Application, then earliest
first_seen_at and UUID. Move occurrences, raw logical references and Applications
to the survivor. Application IDs, notes and status history remain unchanged.

Old Job rows are retained with `merged_into_id`. Requirement sets are archived;
survivor current requirements are extracted deterministically without duplicates.
Historical MatchResults, RequirementMatches, AIAnalysis and AIEvidence remain
referentially valid. Both jobs' match results are invalidated and hidden from
current matching queries. Explicit deterministic recalculation creates/reactivates
the survivor's current result using the established unique job/profile contract;
AI is never called automatically. Existing explicit recomputation semantics may
replace that survivor result's old AI cache.

`JobMergeRecord` preserves retired/target IDs, reason, score and signals. Pending
pairs involving the retired job are resolved as `JOB_RETIRED`. Already retired
jobs cannot merge again into a cycle. Job detail and matching/application
creation resolve old IDs to the survivor. Historical audit FKs remain on durable
rows, avoiding orphan records. Any failure rolls back the entire operation.

## API and frontend

`GET /api/jobs/{id}` includes compact occurrences: source ID/name, ATS, provider
ID, URL, status and first/last seen. Job detail renders a Sources / Occurrences
section. Existing crawl request/response contracts are unchanged.

| Endpoint | Purpose |
|---|---|
| GET `/api/dedup/candidates?pending=true&limit=25&offset=0` | Bounded review queue |
| GET `/api/dedup/candidates/{id}` | Pair, score, signals and comparison |
| POST `/api/dedup/candidates/{id}/merge` | Explicit `{"confirm": true}` required |
| POST `/api/dedup/candidates/{id}/keep-separate` | Durable separate resolution |

`/dedup` displays company/title/location/employment/provider/publication and
abbreviated descriptions side by side. Merge requires a second confirmation.
Duplicate submissions are disabled; failures retain the review and confirmation,
and successful responses refresh the authoritative queue. Existing MVP user
context is reused; A5 does not add an authentication system.

## Migration and controlled historical analysis

Revision `0011_hybrid_dedup` follows `0010_ingestion_control`. It inserts exactly
one occurrence per existing Job, copying provider identity, status, hash and
dates, attributes existing raw records, and backfills indexed normalized blocks.
It does not merge historical jobs or change Application/Match/Requirement IDs.
Downgrade refuses a lossy reversal after multi-occurrence or manual merges.

Activate migration before restarting the backend with the new code:

```powershell
python -m alembic upgrade head
python -m alembic check
python -m scripts.analyze_historical_dedup --limit 1000
```

The analysis command defaults to dry-run, compares bounded cross-source pairs
using the same scorer and conservative guards, and writes
`docs/agent-reports/historical_dedup_a5.json`. `--record-candidates` explicitly
persists suggestions only; it never merges jobs. Batch limit is 1..5000.
Application conflicts demote suggestions to review. No mass-merge command or
Scheduler is introduced. Review candidates through the API/UI before any real
historical merge.

Read-only evidence commands:

```powershell
python -m scripts.calibrate_dedup
python -m scripts.verify_occurrence_backfill
```

Calibration outputs hashed company/title blocks rather than employer content.
The backfill verifier compares current counts to the recorded pre-migration
baseline; rerunning it after legitimate ingestion naturally changes that result.

## Validation and remaining limitations

PostgreSQL tests cover identity, conservative false positives, ambiguity,
richness, Source lifecycle/closure suppression, provenance, Applications,
archived matching/AI evidence, atomic rollback and concurrent discovery.
Frontend tests cover occurrences, review comparison, confirmation/cancellation,
safe failures, authoritative queue refresh and duplicate submissions. A4 preview
tests now also assert no occurrence/candidate mutation. CI tests use fake
provider acquisition, never live boards.

Exact company/title/location blocking intentionally misses aliases and
translations. Multi-location/provider-country enrichment and provider-specific
reference trust need reviewed data before broadening identity. Historical
analysis is bounded and may need multiple controlled batches for larger datasets.
Retired rows and archived requirements/matches need an eventual retention policy.
Occurrence close counts are not new CrawlRun API fields: `jobs_closed` still
counts logical vacancies closed. Last-crawl/ingestion-run occurrence FKs and
Scheduler are deferred.
