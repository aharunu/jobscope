# Database and application boundaries

This guide preserves the useful foundation decisions from the old implementation
notes, checked against current code. It describes existing behavior, not a new
migration or a proposed persistence redesign.

## Domain and ORM mapping

Domain entities are pure Python dataclasses and repository contracts are Protocols.
SQLAlchemy models, sessions and query construction live in infrastructure. Explicit
`from_domain`/`to_domain` conversions cross that boundary; domain entities do not
perform database I/O. API dependencies compose concrete implementations.

The shared [ORM base](../../backend/infrastructure/database/base.py) provides UUID
keys with Python/server defaults and timezone-aware audit timestamps. Some audit
models intentionally have only `created_at`; do not add `updated_at` merely to make
every model inherit the same base. The
[model registry](../../backend/infrastructure/database/models/__init__.py) is imported
by Alembic for metadata discovery. A seemingly unused registration import can be
required by migrations and must not be removed based on static import counts.

All existing revisions remain authoritative migration history. Early plans naming
`0006_cvs` as head describe an old snapshot; use Alembic for the current revision.
CV entities/ORM/table are a storage foundation. They do **not** implement CV upload,
parsing, candidate import or approval. Those remain in the product backlog.

## Sessions and transactions

The [session factory](../../backend/infrastructure/database/session.py) uses
`expire_on_commit=False`. Request/context dependencies own commit/rollback and
close sessions. Repositories may flush to enforce constraints or obtain persisted
values; they do not commit independent transactions. A SQL failure must propagate
to the owner for rollback, rather than continuing with a failed session.

Crawling separates short initialization/finalization transactions from provider
network I/O. PostgreSQL advisory admission uses dedicated AUTOCOMMIT connections;
it is not a long ORM transaction. Canonical persistence, requirements, occurrence
provenance and audit finalization commit atomically. See
[crawler foundation](acquisition_a2.md), [ingestion control](ingestion-control.md)
and [merge safety](hybrid-deduplication.md).

`CrawlRun`/`CrawlRunJob` are operational audit, not a replacement vacancy model.
Ingestion decisions count Source observations; Job lists show Logical Jobs.
Occurrence closures and logical closures can differ. Do not impose an old
pre-occurrence counter equation on current ingestion totals.

## Async conversion pitfall: server defaults

A historical Greenhouse manual test created 31 Jobs successfully. The identical
second crawl failed on all 31 saves after `flush`, before action audit links were
written. SQLAlchemy expired the server-generated `updated_at` after UPDATE;
synchronous `to_domain()` access attempted database I/O and raised `MissingGreenlet`.
The old per-item catch could still commit timestamps while marking the run FAILED.
This explains why successful INSERT alone did not validate the UPDATE path.

Current `TimestampMixin` sets `eager_defaults=True`, so generated defaults are
loaded during awaited persistence. Keep conversion free of implicit lazy I/O and
load required relationships explicitly. `expire_on_commit=False` alone does not
solve server-default expiration during flush. Do not reintroduce blanket per-item
SQL exception containment; current unexpected database failures roll back the unit.

Useful permanent regressions cover save twice, repeated identical ingestion,
authoritative timestamps, coherent audit/provenance and transactional rollback.
The old diagnosis's proposed per-save refresh was a possible remedy, not the
implemented current solution.

## Health, errors and observability

Application lifespan manages the engine/client lifecycle; module imports do not
contact the database. `/health` reports process liveness independently of database
connectivity. `/health/ready` checks database access and returns sanitized ready/not
ready data with 200/503. Readiness does not expose raw driver errors or credentials.

Application errors use the central `JobScopeError` hierarchy/API handlers. Important
recoverable parsing/extractor failures retain safe warnings; infrastructure SQL
failures propagate. Existing secret masking and hidden SQL parameters must remain.
Do not log provider payloads, profiles, keys or connection credentials while
diagnosing failures. See [verification and local setup](local-development.md).
