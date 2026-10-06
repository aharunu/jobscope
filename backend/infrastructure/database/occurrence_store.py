"""Transactional occurrence identity, bounded candidate lookup and projection."""

import hashlib
import json
from dataclasses import asdict

from sqlalchemy import exists, func, select, update

from backend.application.ingestion.policy import CountryResolver
from backend.application.job_discovery.dtos import DiscoveredJobDTO
from backend.application.job_processing.errors import JobURLConflictError
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.crawl.enums import CrawlJobAction
from backend.domain.job.dedup import guard_decision, normalize, project, score_pair
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.models.dedup import (
    DedupCandidateModel as Candidate,
)
from backend.infrastructure.database.models.dedup import (
    JobOccurrenceModel as Occurrence,
)
from backend.infrastructure.database.models.job import JobModel, RawJobModel
from backend.infrastructure.database.models.matching import MatchResultModel
from backend.infrastructure.database.repositories.job_requirement_repository import (
    SQLAlchemyJobRequirementRepository,
)
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)


def employer_reference(discovered):
    """Employer requisitions only; posting/internal IDs are provider-specific."""
    values = dict(discovered.metadata)
    try:
        raw = json.loads(discovered.raw_content)
        if isinstance(raw, dict):
            values = {**raw, **values}
    except (ValueError, TypeError):
        pass
    for key in ("requisition_id", "requisitionId", "jobRequisitionId"):
        value = values.get(key)
        if (
            isinstance(value, (str, int))
            and not isinstance(value, bool)
            and str(value).strip()
        ):
            return str(value).strip()
    return None


async def block_lock(session, company, title):
    key = int.from_bytes(
        hashlib.sha256(
            f"dedup:{normalize(company)}:{normalize(title)}".encode()
        ).digest()[:8],
        "big",
        signed=True,
    )
    await session.execute(select(func.pg_advisory_xact_lock(key)))


def job_country(job):
    return CountryResolver().resolve(
        DiscoveredJobDTO(
            None,
            job.canonical_url,
            job.title,
            "",
            "text/plain",
            {"location": job.location},
        )
    )


async def add_candidate(session, left, right, decision):
    a, b = sorted((left, right))
    existing = await session.scalar(
        select(Candidate).where(Candidate.left_job_id == a, Candidate.right_job_id == b)
    )
    if existing is None:
        session.add(
            Candidate(
                left_job_id=a,
                right_job_id=b,
                score=decision.score,
                outcome=decision.outcome,
                signals=decision.signals,
            )
        )
        await session.flush()


class SQLAlchemyOccurrenceStore:
    def __init__(self, session):
        self.session = session

    async def prepare(self, jobs):
        # Consistent order across multi-item sources, without a global lock.
        for company, title in sorted(
            {(normalize(job.company), normalize(job.title)) for job in jobs}
        ):
            await block_lock(self.session, company, title)

    async def candidates(self, job, limit=50):
        # Indexed exact company/title block, then bounded latest canonical rows.
        return list(
            (
                await self.session.scalars(
                    select(JobModel)
                    .where(
                        JobModel.dedup_company == normalize(job.company),
                        JobModel.dedup_title == normalize(job.title),
                        JobModel.merged_into_id.is_(None),
                        JobModel.id != job.id,
                        ~exists().where(
                            Occurrence.job_id == JobModel.id,
                            Occurrence.source_id == job.source_id,
                        ),
                    )
                    .order_by(JobModel.first_seen_at.desc(), JobModel.id)
                    .limit(limit + 1)
                )
            ).all()
        )

    async def observe(self, canonical, discovered, now):
        await block_lock(self.session, canonical.company, canonical.title)
        # Source identity lock protects updates even when the normalized block changes.
        identity = canonical.external_job_id or canonical.canonical_url
        await block_lock(self.session, str(canonical.source_id), identity)
        criteria = (
            Occurrence.external_job_id == canonical.external_job_id
            if canonical.external_job_id
            else Occurrence.canonical_url == canonical.canonical_url
        )
        occurrence = await self.session.scalar(
            select(Occurrence)
            .where(Occurrence.source_id == canonical.source_id, criteria)
            .with_for_update()
        )
        url_owner = await self.session.scalar(
            select(Occurrence).where(
                Occurrence.source_id == canonical.source_id,
                Occurrence.canonical_url == canonical.canonical_url,
            )
        )
        if url_owner and (not occurrence or url_owner.id != occurrence.id):
            raise JobURLConflictError()
        reference = employer_reference(discovered)
        global_owner = await self.session.scalar(
            select(JobModel).where(
                JobModel.canonical_url == canonical.canonical_url,
                JobModel.merged_into_id.is_(None),
            )
        )
        if (
            not occurrence
            and global_owner
            and (
                normalize(global_owner.company) != normalize(canonical.company)
                or normalize(global_owner.title) != normalize(canonical.title)
            )
        ):
            raise JobURLConflictError()
        reviews = []
        new_occurrence = occurrence is None
        if occurrence:
            logical = await self.session.scalar(
                select(JobModel)
                .where(JobModel.id == occurrence.job_id)
                .with_for_update()
            )
            decision = None
        else:
            rows = await self.candidates(canonical)
            evaluated = []
            for row in rows[:50]:
                refs = (
                    await self.session.scalars(
                        select(Occurrence.reference).where(
                            Occurrence.job_id == row.id,
                            Occurrence.reference.is_not(None),
                        )
                    )
                ).all()
                # Multiple contradictory known references cannot prove auto merge.
                known = set(refs)
                decision = score_pair(
                    canonical,
                    row.to_domain(),
                    reference,
                    next(iter(known)) if len(known) == 1 else None,
                    CountryResolver().resolve(discovered),
                    job_country(row.to_domain()),
                )
                decision = guard_decision(
                    decision,
                    candidate_cap=len(rows) > 50,
                    multiple_references=len(known) > 1,
                )
                evaluated.append((row, decision))
            automatic = [(row, d) for row, d in evaluated if d.outcome == "AUTO_MERGE"]
            if len(automatic) == 1:
                logical, decision = automatic[0]
                logical = await self.session.scalar(
                    select(JobModel).where(JobModel.id == logical.id).with_for_update()
                )
            else:
                if len(automatic) > 1:
                    evaluated = [
                        (row, guard_decision(d, multiple_auto_candidates=True))
                        for row, d in evaluated
                    ]
                logical = JobModel.from_domain(canonical)
                logical.first_seen_at = now
                logical.last_seen_at = now
                self.session.add(logical)
                await self.session.flush()
                reviews = [
                    (row, d)
                    for row, d in evaluated
                    if d.outcome in ("REVIEW", "AUTO_MERGE")
                ]
                decision = max(
                    (d for _, d in reviews or evaluated),
                    key=lambda d: d.score,
                    default=None,
                )
            occurrence = Occurrence(
                job_id=logical.id,
                source_id=canonical.source_id,
                external_job_id=canonical.external_job_id,
                canonical_url=canonical.canonical_url,
                status="ACTIVE",
                first_seen_at=now,
                last_seen_at=now,
                reference=reference,
                dedup_outcome="AUTO_MERGE"
                if len(automatic) == 1
                else "REVIEW"
                if reviews
                else "NEW_JOB",
                dedup_score=decision.score if decision else 0,
                dedup_signals={
                    **(decision.signals if decision else {}),
                    "candidate_count": len(evaluated),
                },
            )
            self.session.add(occurrence)
            await self.session.flush()
            for row, d in reviews:
                await add_candidate(self.session, logical.id, row.id, d)
        previous_hash = occurrence.content_hash
        was_closed = occurrence.status == "CLOSED"
        previous_url = occurrence.canonical_url
        target = logical.to_domain()
        before = JobNormalizer.hash_job(target)
        # Preserve A2 missing content semantics instead of projecting serialized JSON.
        if discovered.metadata.get("description_available") is False or (
            discovered.content_type == "application/json"
            and not (
                discovered.metadata.get("description")
                or discovered.metadata.get("description_plain")
            )
        ):
            canonical.description = target.description
        if discovered.metadata.get("title_available") is False:
            canonical.title = target.title
        projected = project(
            target, canonical, alternate=logical.source_id != canonical.source_id
        )
        for key in (
            "title",
            "company",
            "canonical_url",
            "description",
            "responsibilities",
            "location",
            "work_mode",
            "employment_type",
            "salary",
            "published_at",
        ):
            setattr(logical, key, getattr(projected, key))
        logical.content_hash = JobNormalizer.hash_job(projected)
        logical.dedup_company, logical.dedup_title = (
            normalize(logical.company),
            normalize(logical.title),
        )
        logical.status, logical.closed_at, logical.last_seen_at = (
            JobStatus.ACTIVE,
            None,
            now,
        )
        occurrence.content_hash = JobNormalizer.hash_job(canonical)
        occurrence.last_seen_at, occurrence.closed_at, occurrence.status = (
            now,
            None,
            "ACTIVE",
        )
        occurrence.canonical_url = canonical.canonical_url
        occurrence.reference = reference or occurrence.reference
        occurrence.projection = {
            k: v.isoformat()
            if hasattr(v, "isoformat")
            else str(v)
            if k in ("id", "source_id")
            else v
            for k, v in asdict(canonical).items()
            if k not in ("requirements", "occurrences")
        }
        changed = (
            new_occurrence
            or was_closed
            or previous_hash != occurrence.content_hash
            or previous_url != occurrence.canonical_url
        )
        occurrence.projection["resolved_country"] = CountryResolver().resolve(
            discovered
        )
        if changed:
            self.session.add(
                RawJobModel(
                    job_id=logical.id,
                    source_id=canonical.source_id,
                    occurrence_id=occurrence.id,
                    raw_content=discovered.raw_content,
                    content_type=discovered.content_type,
                    fetched_at=now,
                )
            )
        if before != logical.content_hash or (
            new_occurrence and logical.id == canonical.id
        ):
            await self.session.execute(
                update(MatchResultModel)
                .where(MatchResultModel.job_id == logical.id)
                .values(invalidated=True)
            )
            requirements = DeterministicRequirementExtractor().extract(projected)
            await SQLAlchemyJobRequirementRepository(self.session).save_requirements(
                logical.id, requirements
            )
        await self.session.flush()
        action = (
            CrawlJobAction.CREATED
            if new_occurrence and logical.id == canonical.id
            else CrawlJobAction.UPDATED
            if changed
            else CrawlJobAction.UNCHANGED
        )
        return action, logical.id, occurrence.id

    async def active_count(self, source_id):
        return await self.session.scalar(
            select(func.count())
            .select_from(Occurrence)
            .where(Occurrence.source_id == source_id, Occurrence.status == "ACTIVE")
        )

    async def close_absent(self, source_id, seen, now):
        rows = (
            await self.session.scalars(
                select(Occurrence)
                .where(
                    Occurrence.source_id == source_id,
                    Occurrence.status == "ACTIVE",
                    Occurrence.id.not_in(seen),
                )
                .order_by(Occurrence.job_id)
                .with_for_update()
            )
        ).all()
        closed_jobs = []
        for occurrence in rows:
            occurrence.status, occurrence.closed_at = "CLOSED", now
        await self.session.flush()
        for job_id in sorted({row.job_id for row in rows}):
            logical = await self.session.scalar(
                select(JobModel).where(JobModel.id == job_id).with_for_update()
            )
            active = await self.session.scalar(
                select(Occurrence.id)
                .where(Occurrence.job_id == job_id, Occurrence.status == "ACTIVE")
                .limit(1)
            )
            if not active and logical.status != JobStatus.CLOSED:
                logical.status, logical.closed_at = JobStatus.CLOSED, now
                closed_jobs.append(job_id)
        await self.session.flush()
        return closed_jobs
