# JobScope — Post-MVP Product / UX / Data Quality Backlog

Inspection date: 2026-10-04. Scope: documentation only, during Core MVP manual acceptance testing. This document records the current working tree, including existing uncommitted corrections. It does not authorize implementation or start FAZ 5.

There are **26 entries: 22 open improvement items and 4 verified implemented baselines**. COMPLETE means implementation was confirmed in current source; it does not mean manual acceptance testing or regression suites were rerun for this documentation task.

Priority definitions: **P0** correctness/data integrity; **P1** core product quality; **P2** UX improvements; **P3** future polish. No item was elevated to P0: the inspected scope revealed no new verified correctness/data-integrity blocker. Reported score clustering needs measured investigation, not an assumed algorithm defect.

## Prioritized index

| ID | Item | Priority | Category | Suggested Timing | Status |
| --- | --- | --- | --- | --- | --- |
| PM-01 | HIGH PRIORITY — Matching quality calibration | P1 | Core product quality | First quality work after MVP acceptance | NEEDS INVESTIGATION |
| PM-02 | Employment type ingestion and normalization | P1 | Data quality | Early quality work; coordinate with FAZ 7 | NEEDS INVESTIGATION |
| PM-03 | Job search across skills and requirements | P1 | Discovery / data quality | Early quality work between phases | NEEDS INVESTIGATION |
| PM-04 | Personal application tracker product direction | P1 | Product design | After MVP acceptance, before tracker expansion | NEEDS DESIGN |
| PM-05 | Applications dashboard and pipeline | P2 | Application UX | After PM-04 design | NEEDS DESIGN |
| PM-06 | Application filters and sorting | P2 | Application UX | Incremental work after PM-04 | TODO |
| PM-07 | Notes, timeline and contextual navigation | P2 | Application UX | Incremental work after PM-04 | NEEDS DESIGN |
| PM-08 | Skill suggestions from observed job vocabulary | P2 | Profile / data quality | Between phases, after vocabulary review | NEEDS DESIGN |
| PM-09 | Further profile form usability review | P2 | Profile UX | After manual retest of existing fixes | TODO |
| PM-10 | Multi-seniority targeting model | P2 | Search Profile / domain | Dedicated post-MVP model design | NEEDS DESIGN |
| PM-11 | Search Profile controls and summaries | P2 | Search Profile UX | Between phases; coordinate with PM-08/10 | NEEDS DESIGN |
| PM-12 | Data-derived filter availability | P2 | Discovery UX / data quality | With PM-02/03 or shortly afterward | NEEDS DESIGN |
| PM-13 | Local/remote AI provider UX | P2 | AI UX | After matching calibration baseline | NEEDS DESIGN |
| PM-14 | Application lifecycle product policy review | P2 | Application domain | Before additional correction/reopening rules | NEEDS DESIGN |
| PM-15 | Favicon and page metadata | P3 | Visual polish | After core quality work | TODO |
| PM-16 | Consistent visual and responsive states | P3 | Visual polish | Continuous low-priority improvements | TODO |
| PM-17 | Rich application tracker fields and events | P3 | Future product model | After PM-04/14 design | NEEDS DESIGN |
| PM-18 | Archive, rejected grouping and priorities | P3 | Future tracker UX / model | After lifecycle and retention design | NEEDS DESIGN |
| PM-19 | Optional Kanban drag/drop | P3 | Future tracker interaction | Only after PM-05 proves useful | DEFERRED |
| PM-20 | Funnel / Sankey analytics | P3 | Future analytics | After stable tracker event semantics | DEFERRED |
| PM-21 | Reminders, calendar and email integration | P3 | Future integrations | After consent and scheduling design | DEFERRED |
| PM-22 | Operational logging and query tuning debt | P3 | Technical debt / operations | When measured operational needs justify | DEFERRED |
| BASE-01 | Profile manual form corrections | P2 | Implemented baseline | Preserve; manual retest now | COMPLETE |
| BASE-02 | Search Profile editing | P2 | Implemented baseline | Preserve; manual retest now | COMPLETE |
| BASE-03 | Generic OpenAI-compatible local provider | P1 | Implemented baseline | Preserve; optional AI | COMPLETE |
| BASE-04 | INTERVIEW → APPLIED correction | P2 | Implemented baseline | Preserve; manual retest now | COMPLETE |

## Repository observations and evidence limits

- Application CRUD, private notes, six statuses, history, ownership-scoped listing, status filtering and pagination already exist. The application repository orders by `created_at DESC, id DESC`; alternative sorting and company/role/date/location filters are future work. The list displays Job status and links to both Application and Job; detail shows saved notes and status history. These are enhancements to a working baseline.
- `backend/domain/application/entities.py` and `frontend/src/components/applications/status.tsx` both allow INTERVIEW → APPLIED. Existing application API tests include CLOSED Job independence. Job lifecycle must remain separate from Application lifecycle.
- Search Profile seniority is **SINGLE**: domain `str | None`, ORM nullable `String(50)`, migration `20260919_0002_profiles_create_profile_tables.py` scalar column, API optional string, frontend scalar type/form. AI context also carries a scalar. There is no current multi-seniority contract.
- `backend/infrastructure/database/repositories/job_repository.py` searches title/company with ILIKE in both listing and counting. It does not search description, responsibilities, requirements or normalized skills. ORM Job fields already mark title, company, location and work_mode indexed; this does not establish effective indexes for substring/full-text search. Query plans and actual migrated indexes still need checking.
- Employment type is a nullable string in the Job domain/ORM, not a canonical enum. `normalizer.py` accepts top-level `employment_type` or `commitment`. Lever metadata retains `categories` but does not promote commitment to either expected key; Greenhouse metadata does not provide either key. This is a concrete ingestion gap to investigate, not proof that every upstream posting has that information.
- User-reported database snapshot: **382 total / 0 populated / 382 missing employment_type**. A read-only aggregate verification was attempted using application settings without printing credentials. The available Python environment reported `ModuleNotFoundError`; live counts were **NOT VERIFIED**. No dependencies were installed or database data changed. Treat the numbers as a manual-test snapshot until safely remeasured.
- AI prompt context currently includes deterministic score, category scores and explanation. Several evaluators assign neutral 0.50 to UNKNOWN signals; the engine aggregates fixed category weights and caps explicit unmet blockers. These are investigation leads for clustering/anchoring, not measured proof of the reported cause. No score-distribution study or live LLM run occurred in this task.
- `ProfileSection.tsx` already provides datalist suggestions, custom skill names, controlled level selection, bounded numeric experience, required indicators, date validation and draft retention. Suggestions come from the existing extraction vocabulary; observed database `normalized_skill` values are not yet an additional suggestion source.
- `frontend/src/app/layout.tsx` has title and description metadata. No favicon/icon asset was found in the app tree, and `frontend/public` is absent. Metadata needs review, not creation from scratch.

## Detailed open backlog

### PM-01 — HIGH PRIORITY — Matching quality calibration

- **Priority:** P1.
- **Category:** Core product quality.
- **Problem:** Manual testing reports deterministic and AI scores clustering too closely. Numeric deterministic context may anchor AI; UNKNOWN neutral scores and category weights may reduce discrimination. The exact contribution of each is unmeasured.
- **Desired outcome:** Analyze score distributions using controlled excellent/good/mixed/weak/poor fixtures and representative consented data; review category weights, UNKNOWN semantics and critical requirement penalties. Design an independent AI scoring rubric and assess removal of deterministic numeric anchoring. Improve evidence quality and explain score differences. Preserve strict schema/evidence validation, backend-owned final score, ±8 adjustment, explicit AI triggers, deterministic fallback, cache/fingerprint versioning and force re-analysis.
- **Likely affected areas:** `backend/domain/matching/deterministic_engine.py`, evaluators/category weights, `backend/application/matching/ai/prompt.py`, analyzer/evidence checks, matching tests and fixture documentation.
- **Dependencies:** The separately referenced detailed implementation prompt must be retrieved/reviewed before implementation; it was not supplied for this task. Agree expected ranking and score distributions before changing algorithms. Version cache inputs when semantics change.
- **Suggested timing:** First quality investigation after MVP acceptance; separate implementation scope before relying on ranking quality for further features.
- **Status:** NEEDS INVESTIGATION.

### PM-02 — Employment type ingestion and normalization

- **Priority:** P1.
- **Category:** Data quality.
- **Problem:** Manual snapshot reports all 382 jobs missing the field; counts were not independently verified. Current adapter metadata does not directly supply the keys consumed by normalization. UI options are fixed display strings while persisted values are unconstrained strings.
- **Desired outcome:** Recount safe aggregates by source, inspect sanitized ATS payload fixtures, map source-supported commitment/employment fields, and evaluate extraction when reliable structured data is absent. Define canonical values and unknown handling before implementation. FULL_TIME, PART_TIME, INTERNSHIP, CONTRACT, TEMPORARY and OTHER are candidates, not existing domain enum values. Keep unavailable information unknown; do not invent employment type. Design any reprocessing/backfill separately.
- **Likely affected areas:** Greenhouse/Lever adapters, discovered metadata, job normalizer, Job schema/contracts, frontend employment options and ingestion tests.
- **Dependencies:** Source payload evidence, agreed mapping vocabulary, backward compatibility for existing strings, PM-12 availability UX. Additional ATS mappings can align with FAZ 7.
- **Suggested timing:** Early post-MVP data-quality work; existing providers need not wait for ATS expansion.
- **Status:** NEEDS INVESTIGATION.

### PM-03 — Job search across skills and requirements

- **Priority:** P1.
- **Category:** Discovery / data quality.
- **Problem:** Current title/company-only search misses Python and other skills appearing only in job content or extracted requirements.
- **Desired outcome:** Design search coverage for title, company, description, responsibilities, normalized requirements and `normalized_skill`. Compare a simple indexed normalized search with PostgreSQL full-text search using representative query plans and relevance fixtures. Maintain consistent counts, pagination and existing filters; avoid expensive unrestricted joins or scans. Elasticsearch/vector search require demonstrated need.
- **Likely affected areas:** Job repository list/count, Job/JobRequirement models and migrations if later justified, query API, search input/help text and retrieval tests.
- **Dependencies:** Inspect actual migrated indexes, language/tokenization expectations and data volume; current ordinary field indexes are not proof of full-text coverage. Agree ranking/count semantics before changing retrieval.
- **Suggested timing:** Early quality work between roadmap phases.
- **Status:** NEEDS INVESTIGATION.

### PM-04 — Personal application tracker product direction

- **Priority:** P1.
- **Category:** Product design.
- **Problem:** Functional tracking currently feels like CRUD rather than a personal job-search workspace.
- **Desired outcome:** Define a polished LinkedIn-style personal tracker with useful daily actions, clear status management and navigation. Use the existing INTERESTED, APPLYING, APPLIED, INTERVIEW, OFFER and REJECTED stages as the starting vocabulary. Split dashboard, query, timeline and richer model work into reviewable increments; do not imply all are MVP requirements.
- **Likely affected areas:** `/applications`, Application detail, Job tracking panel, application service/contracts and product design notes.
- **Dependencies:** Manual acceptance results, PM-14 lifecycle policy and scoped design for PM-05/06/07/17/18. Backend remains authoritative; no automatic status changes.
- **Suggested timing:** After MVP acceptance and before significant tracker expansion.
- **Status:** NEEDS DESIGN.

### PM-05 — Applications dashboard and pipeline

- **Priority:** P2.
- **Category:** Application UX.
- **Problem:** Current paginated cards and status filter provide limited overview of progress.
- **Desired outcome:** Add meaningful per-status counts and clear visual progression through the six existing stages. Consider a selectable list/pipeline or Kanban view after user testing. Counts must reflect the owned dataset and defined filter scope, not merely the current page. Drag/drop is separately deferred in PM-19.
- **Likely affected areas:** `ApplicationsClient.tsx`, status badges/helpers, application query/service aggregation and shared UI styles.
- **Dependencies:** PM-04 design, accessible keyboard/mobile interaction and authoritative transition rules. No client-only invented status policy.
- **Suggested timing:** After tracker direction is agreed.
- **Status:** NEEDS DESIGN.

### PM-06 — Application filters and sorting

- **Priority:** P2.
- **Category:** Application UX.
- **Problem:** Status filtering and newest-first pagination exist; company, role, date, location and alternative sorting are missing.
- **Desired outcome:** Preserve existing status filtering and add useful company/role/date/location filters; offer newest, recently updated, company and stage sorting with deterministic pagination. Define which date is filtered and explicit stage order rather than alphabetical enum order.
- **Likely affected areas:** Application list UI/API/types, repository/protocol queries, owned counts and query tests.
- **Dependencies:** PM-04 priorities, Job joins, ownership enforcement and measured query/index needs.
- **Suggested timing:** Incremental work between phases after tracker scope is agreed.
- **Status:** TODO.

### PM-07 — Notes, timeline and contextual navigation

- **Priority:** P2.
- **Category:** Application UX.
- **Problem:** Notes editing, status history and Job links exist, but the complete workflow could provide clearer context and a more useful activity experience.
- **Desired outcome:** Improve saved notes UX and Job → Application → Job navigation; show tracked date and persisted status changes together. Clearly explain that a CLOSED Job can still have an active Application. Interview dates and note/event history are future model additions under PM-17, not data already captured by the current status history.
- **Likely affected areas:** Application list/detail, Job detail tracking panel, timeline presentation and future event contracts.
- **Dependencies:** PM-04 direction and PM-17 event design for new event types. Preserve independent Job lifecycle, existing notes privacy and draft failure behavior.
- **Suggested timing:** Presentation improvements between phases; new events only after design.
- **Status:** NEEDS DESIGN.

### PM-08 — Skill suggestions from observed job vocabulary

- **Priority:** P2.
- **Category:** Profile / data quality.
- **Problem:** Canonical extraction-vocabulary suggestions and custom names already work, but observed Job requirement `normalized_skill` values are not included as an additional source.
- **Desired outcome:** Evaluate a bounded, deduplicated combination of canonical and observed normalized skills, with normalization/provenance and noise controls. Keep custom entry available. Category remains hidden unless a meaningful controlled vocabulary is justified; do not restore ambiguous free text.
- **Likely affected areas:** Skill suggestion service/API/dependency, requirement repository queries, profile skill datalist and future Search Profile selectors.
- **Dependencies:** Vocabulary quality and query-cost review; read-only suggestion access must preserve boundaries. Coordinate with PM-03 and PM-11.
- **Suggested timing:** Between phases after vocabulary review.
- **Status:** NEEDS DESIGN.

### PM-09 — Further profile form usability review

- **Priority:** P2.
- **Category:** Profile UX.
- **Problem:** The specific skills/experience validation and alignment defects have already been corrected; remaining usability opportunities require manual feedback rather than repeating those fixes.
- **Desired outcome:** Retest accessibility, mobile/tablet layout and Education/Projects consistency. Preserve required indicators, field-level errors, controlled levels, 0.5-year steps, sensible bounds, native date selection, date ordering/future-date checks, Current Role clearing/disabling End Date and draft retention on API failure. Improve only confirmed remaining friction.
- **Likely affected areas:** `ProfileSection.tsx`, Profile client, shared fields/styles and focused UI tests.
- **Dependencies:** BASE-01 manual retest. New validation changes require domain agreement; avoid silently changing legacy records.
- **Suggested timing:** After current corrections pass manual acceptance.
- **Status:** TODO.

### PM-10 — Multi-seniority targeting model

- **Priority:** P2.
- **Category:** Search Profile / domain.
- **Problem:** Junior + Mid or Mid + Senior targeting is desired, but current persistence/API supports one scalar seniority.
- **Desired outcome:** Design canonical seniority vocabulary, multiple persisted values, migration/backward compatibility, matching meaning and proper multi-select UI. Existing profiles must remain editable. Do not serialize multiple selections as comma-separated strings.
- **Likely affected areas:** Search Profile domain, ORM/migrations, API schemas, frontend types/create-edit form, deterministic/AI context and cache inputs.
- **Dependencies:** Explicit product/model decision, matching semantics review with PM-01 and migration plan. This is not a frontend-only correction.
- **Suggested timing:** Dedicated post-MVP model change; no migration in this backlog task.
- **Status:** NEEDS DESIGN.

### PM-11 — Search Profile controls and summaries

- **Priority:** P2.
- **Category:** Search Profile UX.
- **Problem:** Working create/edit forms still use basic controls and list-text inputs that can make targeting difficult to understand.
- **Desired outcome:** Better supported multi-select controls, clearer target roles, canonical skill autocomplete with custom values, work-mode/location selection, salary ranges and profile summary cards. Keep seniority single-select until PM-10 changes the canonical model. Preserve existing persisted-value loading, authoritative save, cancel, draft failure, duplicate-submit prevention and create/delete behavior.
- **Likely affected areas:** Search Profiles list, shared create/edit client, frontend types/constants and suggestion integration.
- **Dependencies:** BASE-02 preservation; PM-08 skills and PM-10 seniority; salary units/currency and location/work-mode vocabulary decisions.
- **Suggested timing:** Incremental UX work between phases.
- **Status:** NEEDS DESIGN.

### PM-12 — Data-derived filter availability

- **Priority:** P2.
- **Category:** Discovery UX / data quality.
- **Problem:** Discovery offers fixed filter options regardless of whether the current dataset has usable values; employment type is the reported example.
- **Desired outcome:** Decide whether unavailable filters should be hidden, disabled with explanation or show availability counts. Derive usable options/counts from real data and a defined filter scope; do not hardcode the reported dataset. Preserve reset and deep-link behavior when a previously available value disappears.
- **Likely affected areas:** `JobFilters.tsx`, discovery query/contracts, bounded facets/aggregation and frontend state.
- **Dependencies:** PM-02 canonical vocabulary, count semantics, performance and accessibility review. Distinguish NULL/blank/unrecognized values.
- **Suggested timing:** Alongside or shortly after ingestion/search improvements.
- **Status:** NEEDS DESIGN.

### PM-13 — Local/remote AI provider UX

- **Priority:** P2.
- **Category:** AI UX.
- **Problem:** Generic local provider support exists, but status, provider context and timeout/error feedback could be clearer.
- **Desired outcome:** Friendly local/remote status and actionable safe timeout/provider-error messages. Consider opt-in health testing and model selection later; expose only approved non-secret metadata. AI remains optional and explicitly triggered. Provider failures must preserve deterministic matching and all validation guarantees.
- **Likely affected areas:** Job match detail, safe backend provider metadata/error contracts, settings and optional bounded health checks.
- **Dependencies:** BASE-03; metadata disclosure design, provider support differences and user consent before network checks. No API keys or raw provider output in UI.
- **Suggested timing:** After matching-quality baseline; health/model selection only if separately approved.
- **Status:** NEEDS DESIGN.

### PM-14 — Application lifecycle product policy review

- **Priority:** P2.
- **Category:** Application domain.
- **Problem:** INTERVIEW → APPLIED is already allowed; broader correction, reopening and terminal-state policy needs deliberate product decisions.
- **Desired outcome:** Review normal progression, backward corrections, reopening after rejection and terminal/non-terminal semantics. Define policy centrally; frontend choices mirror backend rules. Keep same-status updates invalid, ownership enforced, one history entry per actual transition and Job lifecycle independent. Do not infer OFFER/REJECTED changes from this backlog.
- **Likely affected areas:** Canonical domain transition map, application service, frontend status helper and policy tests/docs.
- **Dependencies:** BASE-04, PM-04 product review and explicit decisions before adding any rule.
- **Suggested timing:** Before additional transition or archive/reopening changes.
- **Status:** NEEDS DESIGN.

### PM-15 — Favicon and page metadata

- **Priority:** P3.
- **Category:** Visual polish.
- **Problem:** No favicon asset was found. Root title/description already exist, but page-specific titles and wording may need review.
- **Desired outcome:** Appropriate favicon and consistent accurate page metadata; keep the work small and accessible.
- **Likely affected areas:** App icon/favicon assets, layout and page metadata.
- **Dependencies:** Agreed branding/assets and browser verification.
- **Suggested timing:** After core quality work.
- **Status:** TODO.

### PM-16 — Consistent visual and responsive states

- **Priority:** P3.
- **Category:** Visual polish.
- **Problem:** Manual testing requests consistency beyond functional MVP forms and screens; no blanket redesign is justified.
- **Desired outcome:** Review spacing, button hierarchy, form alignment, status colors, empty states, loading skeletons/spinners and mobile layouts using shared components. Preserve existing functional states and accessible contrast/announcements.
- **Likely affected areas:** Shared UI components, global styles and discovery/profile/application pages.
- **Dependencies:** Concrete manual-test observations; coordinate PM-05/09/11 instead of duplicating their work.
- **Suggested timing:** Continuous small improvements after core functionality.
- **Status:** TODO.

### PM-17 — Rich application tracker fields and events

- **Priority:** P3.
- **Category:** Future product model.
- **Problem:** Current Application focuses on Job link, status, notes and status history; richer tracking needs new product/model decisions.
- **Desired outcome:** Evaluate interview date/time and rounds, recruiter/contact, application source, external application URL, salary expectation/offer, follow-up date, attachments/CV version used, job snapshot at application time, company notes and application activity events. Prioritize independently; these are later candidates, not MVP gaps. Avoid confusing live Job data with a historical snapshot.
- **Likely affected areas:** Application domain/ORM/API, retention/privacy rules, detail forms, activity model and future attachment storage.
- **Dependencies:** PM-04/14, date/time/timezone semantics, privacy/retention and validation. CV versioning can coordinate with FAZ 9; reminders belong to PM-21.
- **Suggested timing:** After dedicated product design; implement only selected increments.
- **Status:** NEEDS DESIGN.

### PM-18 — Archive, rejected grouping and priorities

- **Priority:** P3.
- **Category:** Future tracker UX / model.
- **Problem:** Delete is currently available, while non-destructive organization and decluttering need design.
- **Desired outcome:** Evaluate archive, grouping rejected or no-longer-active applications, custom tags, favorites and priority. Define archive separately from application status, deletion and CLOSED Job state; decide restore and count semantics.
- **Likely affected areas:** Application model/queries, dashboard/list, retention and organization controls.
- **Dependencies:** PM-04/14 policy, PM-06 filters, privacy and data retention decisions.
- **Suggested timing:** After lifecycle and retention design.
- **Status:** NEEDS DESIGN.

### PM-19 — Optional Kanban drag/drop

- **Priority:** P3.
- **Category:** Future tracker interaction.
- **Problem:** Drag/drop may improve a pipeline view, but its value and accessibility are not established.
- **Desired outcome:** Consider only if PM-05 user testing supports it. Use canonical transition endpoints, backend validation, visible errors/recovery and keyboard alternatives; do not create automatic status changes or frontend-only lifecycle rules.
- **Likely affected areas:** Optional Kanban UI, application mutation state and interaction tests.
- **Dependencies:** PM-05, PM-14, duplicate-submit and concurrency behavior. A button/select workflow remains available.
- **Suggested timing:** Later, after pipeline UX is proven.
- **Status:** DEFERRED.

### PM-20 — Funnel / Sankey analytics

- **Priority:** P3.
- **Category:** Future analytics.
- **Problem:** Aggregate personal search insights are a future capability; corrections and reopening complicate stage analytics.
- **Desired outcome:** Design honest funnel/Sankey reporting with defined event/time-window/count semantics, accounting for backward transitions and reopened applications. Keep analytics separate from tracker baseline work.
- **Likely affected areas:** Read-only analytics queries/contracts, event semantics and future visualization.
- **Dependencies:** Stable lifecycle/event model PM-14/17, sufficient data and agreed metric definitions.
- **Suggested timing:** Later; not during current MVP acceptance or this task.
- **Status:** DEFERRED.

### PM-21 — Reminders, calendar and email integration

- **Priority:** P3.
- **Category:** Future integrations.
- **Problem:** Follow-up assistance and external integration require scheduling, permission and delivery decisions beyond MVP tracking.
- **Desired outcome:** Evaluate opt-in reminders, follow-up scheduling, calendar and email integrations with explicit consent, timezone support, deduplication and safe secret handling. Do not send messages or alter statuses automatically without an approved design.
- **Likely affected areas:** Future application events/settings, notification/integration adapters and scheduling infrastructure.
- **Dependencies:** PM-17, consent/privacy and provider authorization; reuse FAZ 8 capabilities only if appropriate. Crawling scheduler scope does not automatically include personal reminders.
- **Suggested timing:** Later, after design and suitable infrastructure.
- **Status:** DEFERRED.

### PM-22 — Operational logging and query tuning debt

- **Priority:** P3.
- **Category:** Technical debt / operations.
- **Problem:** Production structured JSON logging and measured index/query tuning remain operational work, distinct from product features. Historical missing-index claims must not override current ORM evidence.
- **Desired outcome:** Evaluate JSON formatting, non-secret diagnostics and workload-driven tuning when needed. Verify actual schema/query plans before proposing indexes; location/work_mode are already marked indexed in current ORM. Preserve useful recoverable-failure logging and secret masking.
- **Likely affected areas:** Logging configuration, repository queries and future migrations justified by measurements.
- **Dependencies:** Real operational requirements, actual migrated index inventory and query metrics. PM-03 owns its specific search performance design.
- **Suggested timing:** Later / Operations; avoid broad refactors or new infrastructure without need.
- **Status:** DEFERRED.

## Verified implemented baselines — preserve rather than reimplement

### BASE-01 — Profile manual form corrections

- **Priority:** P2.
- **Category:** Implemented baseline.
- **Problem:** Previously ambiguous skill inputs and experience/education/project validation and layout gaps prompted manual corrections.
- **Desired outcome:** Preserve current skill suggestions/custom entry, hidden Category, BEGINNER/INTERMEDIATE/ADVANCED/EXPERT level controls, numeric 0–50 bounds and 0.5-year UI steps. Preserve visibly required experience company/title/start, native dates, valid date order/no future experience dates, Current Role clearing/disabling End Date, paired responsive dates, Education/Projects field validation and draft retention on failure.
- **Likely affected areas:** `frontend/src/components/profile/ProfileSection.tsx`, global styles, profile validation/child services, skill suggestions/API and manual-correction tests.
- **Dependencies:** Manual acceptance retest; PM-08 covers observed requirement suggestions beyond the existing canonical vocabulary.
- **Suggested timing:** Already implemented; protect during further work.
- **Status:** COMPLETE — verified in current source, with focused regression tests present; not rerun here.

### BASE-02 — Search Profile editing

- **Priority:** P2.
- **Category:** Implemented baseline.
- **Problem:** Previously missing Edit UX has already been corrected.
- **Desired outcome:** Preserve clear Edit action, persisted initial values, canonical PATCH update, authoritative saved card data and reload persistence, cancel without save, safe error UI/draft retention and duplicate-submit prevention. Preserve create/delete and single-value seniority until a designed model change.
- **Likely affected areas:** `SearchProfilesClient.tsx`, `new/CreateSearchProfileClient.tsx`, search profile API client and `SearchProfileEditing.test.tsx` / backend correction tests.
- **Dependencies:** Existing canonical update API; PM-10 is separate future multi-seniority work.
- **Suggested timing:** Already implemented; manual retest now.
- **Status:** COMPLETE — current list invokes the shared edit form with `initialProfile`, `onCancel` and authoritative `onSaved` handling.

### BASE-03 — Generic OpenAI-compatible local provider

- **Priority:** P1.
- **Category:** Implemented baseline.
- **Problem:** Hosted-only configuration previously prevented local OpenAI-compatible use; current code supports a configurable endpoint.
- **Desired outcome:** Preserve optional `AI_BASE_URL`, unchanged hosted default and explicit configured API key (a harmless local placeholder when local authentication is disabled). Keep generic endpoint/model selection, strict JSON schema and Pydantic/evidence validation, ±8 adjustment, backend score ownership, endpoint-aware fingerprint/cache, force re-analysis and deterministic fallback. Preserve the existing proxy timeout correction and rejection of database-unsafe NUL output.
- **Likely affected areas:** Settings, `backend/infrastructure/llm/openai_provider.py`, AI schema/analyzer, Next proxy configuration and compatible-provider/output-safety tests.
- **Dependencies:** Correct operator configuration and provider structured-output capability; no secret exposure. PM-13 is future UX, not provider reimplementation.
- **Suggested timing:** Already implemented; AI remains optional.
- **Status:** COMPLETE — configurable base URL, hosted fallback and strict structured request are verified in source. No live local-model call was made here.

### BASE-04 — INTERVIEW → APPLIED correction

- **Priority:** P2.
- **Category:** Implemented baseline.
- **Problem:** This manual correction was previously rejected; both canonical policy and frontend helper now allow it.
- **Desired outcome:** Preserve backend-authorized INTERVIEW → APPLIED, normal persisted transition history, one entry per real change, invalid same-status changes, ownership checks and independent Job lifecycle. Preserve OFFER/REJECTED policy until explicitly redesigned.
- **Likely affected areas:** Application domain transition map, frontend status helper and application domain/API/UI regression tests.
- **Dependencies:** Existing canonical application update flow. PM-14 is the separate future full-policy review.
- **Suggested timing:** Already implemented; manual retest now.
- **Status:** COMPLETE — confirmed in both transition maps and focused regression test source.

## Relation to the existing roadmap

The following numbered sequence is preserved as requested. These feature phases are not started, renumbered or declared complete by this backlog document; core design documents describe intended architecture and are not proof of implementation.

| Roadmap feature phase | Boundary / relationship to this backlog |
| --- | --- |
| FAZ 5 — Manual Job Entry | Separate authorized implementation; reuse agreed normalization/search semantics when appropriate. |
| FAZ 6 — Hybrid Deduplication | Separate data-identity feature; do not bundle UX work or redesign deduplication here. |
| FAZ 7 — ATS Expansion | Coordinate employment type mappings and data-quality fixtures for additional providers. Greenhouse/Lever exist; Ashby/Workday remain planned. |
| FAZ 8 — Scheduler | Separate crawling scheduling feature; personal reminders require their own design and consent. |
| FAZ 9 — CV Import | Separate profile ingestion feature; coordinate later CV version/attachment tracking after model design. |

Continuous product/UX work: PM-04–11, PM-13–21 can be selected between phases when appropriate. Data-quality/core ranking work: PM-01–03, PM-08 and PM-12 should have measured acceptance criteria. Technical debt: PM-22 stays Later / Operations. This grouping creates no new numbered phase.

Suggested first review sequence: matching calibration investigation, employment type source/count investigation, indexed skill/requirement search design, then scoped tracker and form UX design. Product owners can reprioritize without automatically authorizing implementation.

## Documentation-task validation and closure

- Created only `docs/roadmap/post_mvp_product_backlog.md`; existing working-tree code/config corrections are outside this task and were preserved.
- Inspected domain/ORM/API/frontend contracts, repositories, ATS metadata, normalization, matching prompt/evaluators, form code and relevant regression test source.
- No application code, API, migration, matching algorithm, prompt, UI or core design document changed. No dependencies installed; no FAZ 5 work begun.
- No backend/frontend tests or build were rerun for this documentation-only task; source inspection is not a new passing-test claim.
- Live employment type counts remain NOT VERIFIED; the safe read-only attempt could not run due to the available Python environment's missing dependency.
- All open entries include priority, category, problem, outcome, affected areas, dependencies, timing and status. No new verified P0/blocker was found in the inspected scope.

**Backlog documented — awaiting separate prioritization and implementation instructions.**
