# A3 provider acquisition

The factory registers Lever, Greenhouse and ten new adapters. All use the managed
A2 SafeHttpClient and source-wide acquisition budget. Product ingestion now uses
bounded Source concurrency; see [ingestion control](ingestion-control.md).
PostgreSQL admission and short transactions remain authoritative;
[occurrences](hybrid-deduplication.md) own provenance and Source lifecycle.
No database migration or credential is required by these public acquisition paths.

| Provider | Example Source URL | Runtime contract | Coverage policy |
|---|---|---|---|
| Ashby | `https://jobs.ashbyhq.com/acme` | public REST v1, includeCompensation=true | Full published list, unique/accounted jobs |
| Workday | `https://acme.wd3.myworkdayjobs.com/en-US/Careers` | empty CXS search, offset/total, conditional description detail | PARTIAL pending hosted-contract verification |
| SmartRecruiters | `https://careers.smartrecruiters.com/acme` | public postings offset/totalFound; conditional description detail | Exhausted consistent total, all records mapped |
| Recruitee | `https://acme.recruitee.com` | Careers Site /api/offers/ | PARTIAL; continuation/auth evolution unverified |
| Personio | `https://acme.jobs.personio.de` | enabled career XML feed | Valid full document, all positions mapped |
| Teamtailor | `https://acme.teamtailor.com` | jobs.json and safe same-host continuation | PARTIAL; feed exhaustion is not board proof |
| Workable | `https://apply.workable.com/acme` | public widget with details=true | PARTIAL; account-dependent continuation |
| Hirex | `https://app.gethirex.com/o/acme/` | HTML, all nested JobPosting JSON-LD blocks | PARTIAL; HTML cannot prove full coverage |
| BambooHR | `https://acme.bamboohr.com/careers` | public careers/list; conditional public JSON-LD detail | PARTIAL; public list/detail variants |
| Oracle | `https://acme.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1` | unfiltered CE finder limit/offset/TotalJobsCount | PARTIAL; internal hosted endpoint |

Example tokens are placeholders. Never change a Source's board population through
config overrides: board/host/site/tenant must agree with its observed URL. Use a
distinct Source for a different population. Custom-domain boards are not yet
accepted by the new adapters. No global/EU or Personio .com/.de error fallback.

Catalog parsing infers `adapter_config` board/host and, for Workday/Oracle,
tenant/site/locale. Existing catalog sync preserves prior IDs, active flags and
manual configuration. A bare Oracle `/hcmUI` URL requires explicit site/locale.
Workday URLs consisting of just a locale or missing site require explicit
`adapter_config.site`; prefer the actual board or CXS URL. Locale defaults to
en-US only when absent from both URL and config; explicit locale is validated.

Supported operational JSON maps:

```json
{
  "pagination_config": {"page_size": 20, "max_pages": 100},
  "rate_limit_config": {"delay_seconds": 0.3}
}
```

New-provider page_size accepts actual integers 1–100 (default 100, Workday 20);
max_pages accepts 1–1000 (default 100). Delay is finite numeric 0–60, applied
between every list/detail call; explicit zero wins over request_delay_seconds.
Global A2 budgets also bound attempts, decoded bytes and elapsed duration. Stored
unknown keys are retained but never forwarded as provider filters. Pagination
mode offset/none is accepted for storage compatibility; it does not disable
required traversal. Other modes and arbitrary base_url overrides are rejected.

Normal application crawls additionally share a same-host HTTP pacing gate:
`CRAWLER_MIN_REQUEST_INTERVAL_SECONDS=1.0` by default (allowed 0.25–60 seconds).
It applies to every physical page/detail/read-POST/retry/redirect request across
Sources using the managed client, including concurrent requests to that host.
Source-specific delays still apply and cannot disable this minimum. A provider's
429/503 `Retry-After` (seconds or HTTP date) postpones subsequent same-host calls;
429 is not automatically retried. Waiting counts against the acquisition time
budget; insufficient time fails safely without early requests or closure.
Provider terms may require a larger interval; configure it accordingly. This
limit is per application process, not a distributed limiter across workers.

PARTIAL snapshots carry warnings and can ingest useful jobs, but never close
absent jobs. Fatal root/network/body/budget/detail errors discard acquisition and
produce FAILED unless the provider explicitly retains a bounded partial result
with warnings, as documented in [ingestion control](ingestion-control.md).
Supported full-board proofs are conditional; historical A3.1 public-board checks
do not remove hosted/feed coverage limitations or guarantee future availability.

Descriptions and individual raw objects remain full length. Workday and
SmartRecruiters required detail use versioned list/detail envelopes; BambooHR
stores the original list item plus identified detail JSON-LD, never a page archive.
Personio stores each original semantic position as XML. Additional fields stay
namespaced in DTO metadata and raw snapshots, with no new canonical columns.
Unknown employment/work mode stays null. Relative Workday dates are not converted.

Important limits: Recruitee announces Careers API authentication enforcement
from February 10, 2027; 401 remains a safe failure, no stored token or bypass was
added. Recruitee, Workable and BambooHR unknown continuation is explicitly warned,
not followed speculatively. Oracle full description can be unavailable and short
content remains flagged PARTIAL. BambooHR without identifiable public detail
keeps useful list data with a warning; missing enrichment cannot erase existing
rich text under A2. Teamtailor public hosted feeds differ from its authenticated API.

References verified during A3: [Ashby public API](https://developers.ashbyhq.com/docs/public-job-posting-api),
[SmartRecruiters Posting API](https://developers.smartrecruiters.com/docs/endpoints),
[Personio XML](https://developer.personio.de/v1.0/reference/get_xml),
[Recruitee authentication](https://docs.recruitee.com/reference/authentication-1),
[Workable widget](https://help.workable.com/hc/en-us/articles/115012801727-How-to-embed-jobs-on-your-website-job-widget),
[Oracle CE endpoint classification](https://docs.oracle.com/en/cloud/saas/human-resources/farws/api-recruiting-ce-job-requisitions.html).

Hybrid Deduplication is implemented; see [its contract](hybrid-deduplication.md).
Country query optimization is described in [provider country filtering](provider-country-filtering.md).
Scheduler, provider credentials and additional detail/host variants remain planned
work. Public-board probes are manual and read-only; CI uses offline fixtures.
