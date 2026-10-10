# Source registry and read projections

This guide consolidates registry, catalog, runtime and query-boundary decisions
from the historical Source/crawler walkthroughs. Actual routes/schemas remain
authoritative; the [API reference](api.md) lists the implemented endpoints.

## Catalog synchronization and ownership

`data/turkish-job-sources.md` is curated input. The Markdown parser identifies
Source entries and provider configuration; adapters acquire Jobs. Synchronization
is explicit and idempotent, not a startup/background discovery service. Malformed
catalog rows are skipped with warnings rather than aborting all valid entries.

Source URL normalization trims whitespace, lowercases scheme/host, removes
fragments/tracking parameters, sorts retained functional query parameters and
removes trailing path slashes. It preserves path case. Normalization is not an
SSRF or endpoint-ownership check; provider binding and safe HTTP validation are
separate infrastructure responsibilities.

Repeated sync preserves existing Source IDs, manual active state and operational
configuration. Sync does not undo deactivation or silently replace existing
pagination/endpoint/rate-limit overrides. `PATCH /api/sources/{id}/status` is the
canonical administrative active-state mutation; general configuration PATCH does
not provide another status path. Registry APIs intentionally have no deletion
workflow: deactivate a Source without discarding its provenance/history.

## Probes and runtime access

Health probing answers whether the registered public HTTP(S) target is reachable.
It does not acquire/persist Jobs, prove a provider's complete population, or
automatically activate/deactivate a Source. Domain/application services depend on
probe/client ports; DNS/IP/redirect/TLS checks stay in infrastructure.

`RuntimeSourceDTO` is a frozen dataclass with deep-copied nested config maps. Its
fields cannot be reassigned, and adapter-local map changes cannot mutate the
registry entity/database. The copied dictionaries are not recursively immutable.
Runtime retrieval itself has no sync/probe/network side effects.

Recognized ATS labels and registered adapters are different capabilities. The
product ingestion selector excludes `custom` and Kariyer.net because neither has
an acquisition adapter. Provider-aware schemas validate existing JSONB configuration
at the adapter boundary; recognition alone does not prove a board is supported.
See [provider contracts](acquisition_a3.md) and [acquisition authority](acquisition-architecture.md).

Source list queries support active/inactive/all filtering, provider filtering,
case-insensitive search over name/company/URL and bounded pagination with
deterministic tie-break ordering. Source statistics describe registry state,
not the count of complete live boards or unique vacancies.

## Read-only Job and crawl history projections

Entity identity lookup and rich public detail projection serve different uses.
Read APIs do not trigger acquisition, normalization, requirement extraction,
matching or lifecycle changes. Job query filtering uses logical rows/occurrence
existence without duplicating Logical Jobs. Retired Job IDs resolve their survivor
under the [dedup contract](hybrid-deduplication.md).

Job/history responses use compact Source projections rather than serializing
runtime configuration. Adapter/endpoint/rate-limit dictionaries and private
provider payloads are not exposed just because a joined ORM relationship exists.
Crawl history is paginated/ordered audit; durations/success rates are derived
operational metrics, not proof of coverage. A missing audit link, failed run or
zero returned jobs alone cannot establish that upstream Jobs were closed.

Current PARTIAL/filtered acquisition and zero-result anomaly rules remain the
authority for absence closure. See [ingestion control](ingestion-control.md).
Index additions and retention policies require measured future review; old phase
notes' proposed row-count thresholds are not current operating requirements.
