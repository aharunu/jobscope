# Documentation index and authority

Repository code, schemas and automated regressions define implemented behavior.
The development guides below document that behavior and repeatable operations.
Update the affected guide when a contract changes instead of adding another
permanent copy to a phase report or the root README.

| Document | Maintained responsibility |
|---|---|
| [Root README](../../README.md) | Product overview, quick setup and entry links |
| [Local development](local-development.md) | Docker/native setup, configuration, backup/restore, verification |
| [API](api.md) | Implemented endpoint inventory and scoped identity |
| [Profiles, matching and applications](profiles-matching-applications.md) | Product contracts, persistence, status transitions |
| [AI matching](ai-matching.md) | Explicit triggers, local/hosted configuration, strict evidence/scoring/cache guarantees |
| [Acquisition architecture](acquisition-architecture.md) | Current authority boundary, completeness, HTTP and lifecycle safety |
| [Lever/Greenhouse contracts](acquisition_a1.md) | Provider requests, mapping and runtime config |
| [Crawler foundation](acquisition_a2.md) | Budgets, admission, transaction boundaries and meaningful change detection |
| [Multi-provider contracts](acquisition_a3.md) | Provider bindings, coverage limitations and shared pacing |
| [Ingestion control](ingestion-control.md) | Preview/Persist, policy precedence, concurrency, progress/cancellation |
| [Country filtering](provider-country-filtering.md) | Provider query optimization and conservative local filtering |
| [Hybrid deduplication](hybrid-deduplication.md) | Occurrence identity, scoring, projection, review, merge and lifecycle |
| [Maintenance tools](maintenance-tools.md) | Developer CLI, read-only profiling, calibration and integrity checks |

The original [technical design](../design/01_mvp_technical_design.md),
[database/API design](../design/02_database_and_api_design.md) and
[data model](../design/03_data_model_and_architecture.md) preserve intended
architecture. They may describe future functionality; they are not feature
completion checklists. The [product backlog](../roadmap/post_mvp_product_backlog.md)
records planned work without automatically authorizing a new phase.

The two root audits dated 2026-10-01 preserve the initial architectural/security
baseline. They are historical evidence, including resolved findings. Local
`docs/agent-reports/` retains useful final milestone audits and original decisions,
measurements and unresolved limitations. Temporary evidence may be retired once
its results are recorded. Audit reports do not override current guides or code.
Do not require ignored evidence files for normal setup.
