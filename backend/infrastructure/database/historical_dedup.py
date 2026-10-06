"""Bounded historical analysis. Dry-run by default; never merges historical jobs."""

from sqlalchemy import select

from backend.domain.job.dedup import guard_decision, score_pair
from backend.infrastructure.database.models.application import ApplicationModel
from backend.infrastructure.database.models.dedup import JobOccurrenceModel
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.occurrence_store import (
    SQLAlchemyOccurrenceStore,
    add_candidate,
    job_country,
)


async def analyze_historical(session, limit=500, record_candidates=False):
    if not 1 <= limit <= 5000:
        raise ValueError("Historical batch limit must be 1..5000")
    jobs = (
        await session.scalars(
            select(JobModel)
            .where(JobModel.merged_into_id.is_(None))
            .order_by(JobModel.id)
            .limit(limit + 1)
        )
    ).all()
    store = SQLAlchemyOccurrenceStore(session)
    if record_candidates:
        await store.prepare([job.to_domain() for job in jobs[:limit]])
    results, seen = [], set()
    for job in jobs[:limit]:
        candidates = await store.candidates(job.to_domain())
        left_refs = set(
            (
                await session.scalars(
                    select(JobOccurrenceModel.reference).where(
                        JobOccurrenceModel.job_id == job.id,
                        JobOccurrenceModel.reference.is_not(None),
                    )
                )
            ).all()
        )
        for other in candidates[:50]:
            pair = tuple(sorted((job.id, other.id)))
            if pair in seen:
                continue
            seen.add(pair)
            right_refs = set(
                (
                    await session.scalars(
                        select(JobOccurrenceModel.reference).where(
                            JobOccurrenceModel.job_id == other.id,
                            JobOccurrenceModel.reference.is_not(None),
                        )
                    )
                ).all()
            )
            decision = score_pair(
                job.to_domain(),
                other.to_domain(),
                next(iter(left_refs)) if len(left_refs) == 1 else None,
                next(iter(right_refs)) if len(right_refs) == 1 else None,
                job_country(job.to_domain()),
                job_country(other.to_domain()),
            )
            apps = (
                await session.scalars(
                    select(ApplicationModel.user_id).where(
                        ApplicationModel.job_id.in_(pair)
                    )
                )
            ).all()
            decision = guard_decision(
                decision,
                candidate_cap=len(candidates) > 50,
                multiple_references=len(left_refs) > 1 or len(right_refs) > 1,
                application_conflict=len(apps) != len(set(apps)),
            )
            if decision.outcome == "NEW_JOB":
                continue
            results.append(
                {
                    "left_job_id": str(pair[0]),
                    "right_job_id": str(pair[1]),
                    "score": decision.score,
                    "outcome": decision.outcome,
                    "signals": decision.signals,
                }
            )
    automatic_counts = {}
    for result in results:
        if result["outcome"] == "AUTO_MERGE":
            for key in ("left_job_id", "right_job_id"):
                automatic_counts[result[key]] = automatic_counts.get(result[key], 0) + 1
    for result in results:
        if result["outcome"] == "AUTO_MERGE" and any(
            automatic_counts.get(result[key], 0) > 1
            for key in ("left_job_id", "right_job_id")
        ):
            result["outcome"] = "REVIEW"
            result["signals"]["multiple_auto_candidates"] = True
    if record_candidates:
        import uuid

        from backend.domain.job.dedup import DedupDecision

        for result in results:
            await add_candidate(
                session,
                uuid.UUID(result["left_job_id"]),
                uuid.UUID(result["right_job_id"]),
                DedupDecision(result["score"], result["outcome"], result["signals"]),
            )
    return {
        "dry_run": not record_candidates,
        "jobs_analyzed": min(limit, len(jobs)),
        "batch_truncated": len(jobs) > limit,
        "pairs_compared": len(seen),
        "candidates": results,
        "merges_performed": 0,
    }
