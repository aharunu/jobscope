# Requirements and deterministic matching

This guide preserves the implemented extraction/scoring details and unresolved
model limitations from historical notes. It does not change algorithms, prompts,
weights, thresholds, ingestion or dedup rules.

## Requirement extraction

The infrastructure `DeterministicRequirementExtractor` implements an application
port and returns domain `JobRequirement` objects. It reads canonical title,
description and responsibilities, rather than provider-specific raw JSON.
Its curated taxonomy/regexes identify technical skills, experience years,
education, languages and certifications. Word boundaries distinguish Java from
JavaScript, and SQL from PostgreSQL; this is deterministic pattern matching,
not semantic comprehension or a guarantee of zero false positives.

Recognized required/preferred section headings establish context. Line-level
required/plus/preferred indicators override it. Repeated requirements reconcile
deterministically, with REQUIRED winning over PREFERRED. Title skill mentions
are high-importance REQUIRED signals; required degrees can become blockers.
Evidence excerpts and normalized keys stay with each structured requirement.
Output is sorted deterministically by type/key/description; generated UUIDs are
not evidence of semantic change.

Persistence replaces the current requirement set atomically in the caller's
transaction. Empty extraction can persist an empty set without duplicates.
Pure extractor failures and SQL persistence failures are distinct: the legacy
extraction service can wrap a pure failure for nonfatal ingestion warnings;
database failures must propagate and roll back. The A5 occurrence path re-extracts
when the Logical Job is new or its canonical projection changes; unchanged
sightings do not create new requirements/raw snapshots. Do not copy an old plan's
claim that every observation re-extracts.

## Scores, blockers and confidence

The pure domain engine uses six fixed category weights:

| Category | Weight |
|---|---:|
| Role | 0.20 |
| Skills | 0.30 |
| Experience | 0.20 |
| Location/work mode | 0.10 |
| Education | 0.10 |
| Other criteria | 0.10 |

Overall deterministic score is the weighted category sum multiplied by 100,
quantized to two decimals and bounded to 0–100. An evaluated unmet blocker caps
it at 40.00 and remains visible in the explanation/requirement evidence. UNKNOWN
is distinct from NOT_MATCHED: absent job skill requirements currently receive
neutral 1.00, while unavailable candidate skill evidence receives 0.50. Other
category defaults and partial scores are evaluator-specific; missing information
must not be rendered as a proved mismatch.

Confidence is known-signals / total-signals × 100, bounded to 0–100; when there
are no signals, the engine uses 50.00. It is evidence coverage, not a calibrated
probability of getting an offer. A high/unchanged score with sparse requirements
can follow from neutral defaults; this is an existing product-model limitation,
not a reason to alter it in archival cleanup.

Category weights are fixed in `category_weights.py`; current SearchProfile API
does not expose configurable evaluator weights. Explicit matching saves one
current `(job_id, base_profile_id, search_profile_id)` snapshot and its evidence;
retrieval does not calculate it. Content changes/merges invalidate current results
without automatically invoking AI. See [saved matching](profiles-matching-applications.md).

## Candidate evidence vs search preferences

BaseProfile represents candidate capabilities and recorded experience; SearchProfile
represents desired roles/skills/location/salary. Historical plans proposed excluding
search target skills from candidate evidence. Current `SkillEvaluator` still includes
`SearchProfile.target_skills` alongside BaseProfile skills and experience/project
skills, labeling that source explicitly. The proposal was **not implemented** and
must not be documented as an existing guarantee. This ambiguity and scoring
calibration require a separate product/model review; no rule is relaxed here.

Owned BaseProfile → owned SearchProfile → Job → MatchResult remains the service
boundary. Cross-user resources are inaccessible; `X-User-Id` is scoped context
rather than verified authentication. Optional [AI matching](ai-matching.md) uses
its separate strict quote/reference validation and backend-owned ±8 adjustment;
deterministic calculation remains usable without an AI provider.

Permanent taxonomy, repository, ingestion, engine and ownership tests remain in
`tests/`. Provider calls and AI inference are not required for these regressions.
