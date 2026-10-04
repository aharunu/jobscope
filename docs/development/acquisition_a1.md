# Lever and Greenhouse acquisition configuration

A1 corrects existing provider contracts. It adds no adapter, migration, scheduler,
HTTP retry policy or persistence system. Source JSONB remains the configuration
store; validation occurs in infrastructure before the adapter's first request.

Shared safety budgets, PostgreSQL admission and richer canonical update detection
are documented in [Acquisition Foundation A2](acquisition_a2.md). Unknown provider
values remain null on creation and preserve existing rich values on later crawls.

## Lever

Default requests use `mode=json`, `limit=100`, and integer `skip=0`, then numeric
offsets advanced by the received count. A full page needs another request to prove
exhaustion. Default `max_pages=10` is retained from existing operation; exhausting
the ceiling after a full page produces an incomplete, warning-bearing result.

Supported configuration example:

```json
{
  "adapter_config": {"site_token": "example", "region": "global"},
  "pagination_config": {"pagination_mode": "offset", "page_size": 100, "max_pages": 10},
  "endpoint_config": {"base_url": "https://api.lever.co/v0/postings"},
  "rate_limit_config": {"delay_seconds": 0.0}
}
```

All of these maps may be empty for a normal board URL. Token aliases are
`site_token`, `board_token`, `token`, `company_slug`, in that precedence order.
An explicitly supplied invalid token is rejected rather than silently bypassed.
Tokens must be single ASCII path identifiers of 1–255 characters: letters,
digits, underscores and hyphens, starting with a letter or digit.

`page_size` and `max_pages` must be actual integers in 1–1000, not strings or
booleans. `pagination_mode` may be omitted or be `offset`. An existing explicit
`cursor` setting fails with `INVALID_SOURCE_CONFIG`; remove it or change it to
`offset` using the existing Source configuration update route. No automatic
database update or catalog rewrite is performed.

EU boards at `jobs.eu.lever.co` or `api.eu.lever.co` select
`https://api.eu.lever.co/v0/postings` deterministically. A configured region,
recognized Source URL and API base must agree. Only these two HTTPS API bases are
accepted; arbitrary endpoint overrides are rejected. A failure never triggers a
switch to another region. Explicit token overrides for valid custom catalog
URLs remain supported; region/base must then identify the intended provider.

Delay is a finite numeric value in 0–60 seconds, applied between Lever pages.
`delay_seconds` takes precedence over `request_delay_seconds`, including explicit
zero. It is not a host-wide throttle or a retry policy.

Full combined opening/body, list sections and closing content flow to explicit
description metadata. HTML/plain alternatives and responsibilities are preserved;
the complete individual provider object is JSON raw content. Commitment maps
conservatively to Full-time, Part-time, Contract or Internship; structured
workplaceType maps to Remote, Hybrid or On-site. Unknown values remain canonical
null and are preserved in raw/namespaced provider metadata. No title/location
inference is used. `createdAt` is retained upstream rather than asserted to be an
original publication date: the inspected public contract does not establish that
semantic guarantee.

## Greenhouse

Acquisition makes exactly one full-list GET to
`https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`, with only
`content=true`. Token aliases are `board_token`, `site_token`, `token`,
`company_slug`; standard board, EU board, API and embed URL forms remain supported.

The only supported API base override is the same documented HTTPS base. Delay
values are validated as above; there is no between-page sleep because this
contract has only one request. Legacy `page_size`, `max_pages`, and
`pagination_mode` JSON keys remain stored unchanged but are intentionally ignored,
even if their old values are invalid. They cannot filter, truncate or paginate
the response. Other unused configuration keys remain stored but are not request
parameter passthroughs.

Completeness requires a nonnegative integer `meta.total` (not boolean, string or
float) that equals received records, unique posting identities and successfully
mapped jobs, with no warnings. Missing/invalid totals, duplicates, count mismatch
and skipped malformed records yield incomplete results with explicit warnings.
Posting `id` is identity; a null `internal_job_id` does not exclude prospect posts.

Full content, departments, offices, requisition/internal identifiers, custom
metadata and updated_at survive in DTO metadata/raw JSON. `updated_at` does not
populate published_at. There is no universal employment/work-mode inference.
An absent optional description uses title, never serialized raw JSON as prose.

## Ingestion and remaining limits

The existing ingestion/status/lifecycle framework is unchanged. Every incomplete
Lever/Greenhouse return carries warnings, so usable jobs ingest as PARTIAL and
absence closure is suppressed. Fatal network/root errors return no authoritative
snapshot. Complete warning-free crawls retain existing closure rules, including
the zero-result anomaly guard.

RawJob is still saved only on create/update/reopen. No unchanged snapshots or
RawJob→CrawlRun link are added. The existing four-field content hash is unchanged:
an employment-type-only change can remain undetected until A2. Rich mapped fields
are saved on creation or when an existing hashed field genuinely changes.

Reference contracts: [Lever postings API](https://github.com/lever/postings-api)
and [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html).
Offline mocks verify request/mapping/lifecycle behavior; no live-board completeness
claim is made.
