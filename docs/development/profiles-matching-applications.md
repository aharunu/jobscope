# Profiles, matching and applications

## Application tracking backend

The backend supports tracking an existing job, listing/filtering/paginating the current user's applications, retrieving details, updating status or notes, and deleting a tracking record. The frontend and core workflow are also **complete (FAZ 4)**.

- Creation defaults to `INTERESTED`; any valid explicit ApplicationStatus is accepted. Initial creation has no history entry because there is no previous application status.
- One application per `(job_id, user_id)` is enforced by PostgreSQL and the service. Duplicate tracking returns `409 APPLICATION_ALREADY_EXISTS`, including insert races.
- Every actual allowed status change writes history in the same request transaction. A failure rolls back status and history together. Concurrent status/notes edits lock and refresh the owned application before mutation.
- Same-status requests return `422 INVALID_STATUS_TRANSITION` and create no history. Existing transition policy is preserved:

  | Current status | Allowed next statuses |
  |---|---|
  | INTERESTED | APPLYING, APPLIED, REJECTED |
  | APPLYING | INTERESTED, APPLIED, REJECTED |
  | APPLIED | INTERVIEW, OFFER, REJECTED |
  | INTERVIEW | APPLIED, OFFER, REJECTED |
  | OFFER | REJECTED |
  | REJECTED | INTERESTED, APPLYING, APPLIED, INTERVIEW |

- Missing or another user's application returns `404 APPLICATION_NOT_FOUND` for detail, status, notes, deletion and history. Payload `user_id` is rejected; ownership comes from request context.
- Notes are optional, limited to 5,000 characters, and trimmed; null/blank notes clear the value. Notes edits create no status history.
- Detail embeds chronological history; `/history` exposes the same ordering by `changed_at`, then ID. Lists use status filtering and `limit` (1–100) / `offset` (non-negative), returning `items`, `total`, `limit`, `offset`.
- Optional `job_id` UUID filtering uses the existing owned unique lookup. It returns zero or one matching application without downloading the full list; status and pagination constraints still apply.
- Job and Application statuses are independent: closing a job preserves an application in `INTERVIEW`. Explicitly deleting the application deletes its history; closing the job does neither.

## Application tracking frontend and core workflow

Configure `/profile`, manage search personas at `/search-profiles`, browse `/jobs` and open a job. The MatchPanel retrieves saved deterministic results and optionally runs explicit calculation or AI analysis. **Track Application** creates an `INTERESTED` record even without a match or AI. An existing record shows its current status and **Manage application**; duplicate creation races recover through the owned job lookup.

`/applications` shows job summaries, application/job status, notes previews and timestamps in responsive cards, with server status filtering and 20-item pagination. `/applications/{id}` survives refresh/direct navigation and provides **View job**, allowed next-status choices, notes editing/clearing (5,000 characters), real persisted history and separate **Remove application → Confirm removal** controls. Removal deletes tracking/history, preserves the job and allows tracking again on a later visit.

Status, notes and removal requests share a synchronous mutation guard; authoritative PATCH responses update the record without optimistic status changes. Notes drafts survive failures and status saves. Requests are aborted on navigation, and stale responses cannot update a different application or job. Application identity is User + Job and remains independent of SearchProfile/AI selection.

| Core capability | Status |
|---|---|
| BaseProfile backend/frontend | COMPLETE |
| SearchProfile backend/frontend | COMPLETE |
| Job Discovery | COMPLETE |
| Deterministic Matching / Persistence / Retrieval | COMPLETE |
| Optional AI Matching | COMPLETE |
| Application Tracking backend/frontend | COMPLETE |
| Core JobScope workflow | COMPLETE |
| Ingestion Control Center (A4) | COMPLETE |
| Hybrid Deduplication / Occurrences / Review (A5) | COMPLETE |

Validation combines real PostgreSQL/API workflow tests and frontend behavioral tests, with targeted desktop/tablet/mobile browser smoke checks. This is not a full automated browser E2E suite or production authentication/deployment certification.

## Candidate profile and saved matching

Open `/profile` from navigation, create/edit the candidate name and summary, then manage skills, experience, education and projects. The existing backend initializes a blank `Candidate Profile` on GET; the UI's Create Profile action saves its metadata through PATCH. SearchProfiles remain separate search personas configured at `/search-profiles`.

Skill names offer optional suggestions from the existing extraction taxonomy. Custom names remain valid. The editor offers Beginner, Intermediate, Advanced, Expert or Not specified; historical free-text levels and category metadata are preserved when editing other fields. Category is omitted from the editor because matching does not consume it. Optional experience years accept 0–50 in half-year steps in the UI; the API rejects non-finite or out-of-range numbers.

Experience company, role title and start date are required. Native date controls remain empty until a date is entered, accept dates from 1900-01-01 through today, and require end date to be on or after start date. Current role immediately clears/disables end date, and the backend persists it as null. Historical invalid dates are flagged for manual correction rather than replaced with an invented date. Field errors preserve the draft, and save requests use the existing duplicate-request guard.

`GET /api/matches/job/{job_id}?search_profile_id={id}` is the canonical detail lookup. It returns the same persisted representation as POST, including scores, category breakdowns, requirement evidence, blockers and explanation. Missing saved results return `404 MATCH_RESULT_NOT_FOUND`; missing jobs or inaccessible SearchProfiles return their resource 404s. GET never calls the match engine or writes results. Collection GET returns `items`, `total`, `limit`, `offset`, ordered by `updated_at` descending then ID descending; `limit` is 1–100 and `offset` is non-negative.

Each `(job_id, base_profile_id, search_profile_id)` stores one current snapshot. Explicit POST re-evaluation overwrites that snapshot, retaining its ID and creation timestamp. Profile edits do not automatically recalculate it. A5 canonical content changes and manual merges invalidate affected saved matches so stale results are not exposed as current. Historical merge records, requirements and match/AI evidence remain referentially valid; explicit deterministic recalculation restores a current result without calling AI. MatchPanel displays the saved timestamp and offers explicit re-evaluation.

Run `alembic upgrade head` before using retrieval. Migration `0008_match_snapshot` persists category scores and explanation that previously existed only in the POST response. Legacy rows retain their stored scalar scores and requirement evidence with `{}` category scores and a null explanation. GET does not invent or backfill missing evidence; explicitly re-evaluate to obtain a complete current snapshot.
