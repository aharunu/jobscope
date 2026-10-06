"""Short transactional review operations; retired rows preserve historical snapshots."""

from datetime import UTC, datetime

from sqlalchemy import func, select, update

from backend.application.common.exceptions import JobScopeError
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.job.dedup import project
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.models.application import ApplicationModel
from backend.infrastructure.database.models.dedup import (
    DedupCandidateModel as Candidate,
)
from backend.infrastructure.database.models.dedup import JobMergeRecordModel as Merge
from backend.infrastructure.database.models.dedup import (
    JobOccurrenceModel as Occurrence,
)
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
    RawJobModel,
)
from backend.infrastructure.database.models.matching import MatchResultModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.occurrence_store import block_lock
from backend.infrastructure.database.repositories.job_requirement_repository import (
    SQLAlchemyJobRequirementRepository,
)
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)


class SQLAlchemyDedupReview:
    def __init__(self, session):
        self.session = session

    async def get(self, identity):
        row = await self.session.get(Candidate, identity)
        if row is None:
            raise JobScopeError("Dedup candidate not found", "DEDUP_NOT_FOUND", 404)
        return row

    async def detail(self, identity):
        row = await self.get(identity)
        result = {
            column.key: getattr(row, column.key)
            for column in Candidate.__table__.columns
        }
        jobs = []
        for job_id in (row.left_job_id, row.right_job_id):
            job = await self.session.get(JobModel, job_id)
            providers = (
                await self.session.execute(
                    select(Occurrence, SourceModel)
                    .join(SourceModel, SourceModel.id == Occurrence.source_id)
                    .where(Occurrence.job_id == job_id)
                )
            ).all()
            jobs.append(
                {
                    "id": job.id,
                    "company": job.company,
                    "title": job.title,
                    "location": job.location,
                    "employment_type": job.employment_type,
                    "work_mode": job.work_mode,
                    "published_at": job.published_at,
                    "description": job.description[:1500],
                    "merged_into_id": job.merged_into_id,
                    "sources": [
                        {
                            "source": source.name,
                            "ats_type": source.ats_type,
                            "url": occurrence.canonical_url,
                            "status": occurrence.status,
                        }
                        for occurrence, source in providers
                    ],
                }
            )
        result["jobs"] = jobs
        return result

    async def listing(self, limit=25, offset=0, pending=True):
        query = select(Candidate)
        if pending:
            query = query.where(Candidate.resolved_at.is_(None))
        total = await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )
        rows = (
            await self.session.scalars(
                query.order_by(Candidate.created_at.desc(), Candidate.id)
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return {
            "items": [await self.detail(row.id) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def resolve(self, identity, merge=False):
        row = await self.get(identity)
        pair = sorted((row.left_job_id, row.right_job_id))
        preliminary = [await self.session.get(JobModel, key) for key in pair]
        # Same company/title namespace as ingestion; deterministic lock order.
        for company, title in sorted(
            {(job.dedup_company, job.dedup_title) for job in preliminary}
        ):
            await block_lock(self.session, company, title)
        await self.session.scalars(
            select(Occurrence)
            .where(Occurrence.job_id.in_(pair))
            .order_by(Occurrence.job_id, Occurrence.id)
            .with_for_update()
        )
        jobs = list(
            (
                await self.session.scalars(
                    select(JobModel)
                    .where(JobModel.id.in_(pair))
                    .order_by(JobModel.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
        )
        row = await self.session.scalar(
            select(Candidate)
            .where(Candidate.id == identity)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if row.resolved_at:
            return await self.detail(identity)
        if any(job.merged_into_id for job in jobs):
            raise JobScopeError(
                "A candidate job was already merged; refresh review",
                "DEDUP_ALREADY_MERGED",
                409,
            )
        now = datetime.now(UTC)
        if not merge:
            row.resolved_at, row.resolution = now, "KEEP_SEPARATE"
            await self.session.flush()
            return await self.detail(identity)
        apps = (
            await self.session.scalars(
                select(ApplicationModel)
                .where(ApplicationModel.job_id.in_(pair))
                .order_by(ApplicationModel.id)
                .with_for_update()
            )
        ).all()
        users = [app.user_id for app in apps]
        if len(users) != len(set(users)):
            raise JobScopeError(
                "Both jobs have applications for the same user; merge is unsafe",
                "DEDUP_APPLICATION_CONFLICT",
                409,
            )
        app_jobs = {app.job_id for app in apps}
        jobs.sort(key=lambda job: (job.id not in app_jobs, job.first_seen_at, job.id))
        target, retired = jobs
        projected = project(target.to_domain(), retired.to_domain(), alternate=True)
        for key in (
            "description",
            "responsibilities",
            "location",
            "work_mode",
            "employment_type",
            "salary",
            "published_at",
        ):
            setattr(target, key, getattr(projected, key))
        target.content_hash = JobNormalizer.hash_job(projected)
        target.first_seen_at = min(target.first_seen_at, retired.first_seen_at)
        target.last_seen_at = max(target.last_seen_at, retired.last_seen_at)
        await self.session.execute(
            update(Occurrence)
            .where(Occurrence.job_id == retired.id)
            .values(job_id=target.id)
        )
        await self.session.execute(
            update(RawJobModel)
            .where(RawJobModel.job_id == retired.id)
            .values(job_id=target.id)
        )
        for app in apps:
            app.job_id = target.id
        # Keep historical matches and their requirements/AI evidence intact.
        # No stale historical score is exposed as current after canonical merge.
        await self.session.execute(
            update(MatchResultModel)
            .where(MatchResultModel.job_id.in_(pair))
            .values(invalidated=True)
        )
        await self.session.execute(
            update(JobRequirementModel)
            .where(JobRequirementModel.job_id.in_(pair))
            .values(archived=True)
        )
        requirements = DeterministicRequirementExtractor().extract(projected)
        await SQLAlchemyJobRequirementRepository(self.session).save_requirements(
            target.id, requirements
        )
        active = await self.session.scalar(
            select(Occurrence.id)
            .where(Occurrence.job_id == target.id, Occurrence.status == "ACTIVE")
            .limit(1)
        )
        target.status, target.closed_at = (
            (JobStatus.ACTIVE, None) if active else (JobStatus.CLOSED, now)
        )
        retired.merged_into_id = target.id
        self.session.add(
            Merge(
                source_job_id=retired.id,
                target_job_id=target.id,
                reason="MANUAL_REVIEW",
                score=row.score,
                signals=row.signals,
            )
        )
        row.resolved_at, row.resolution = now, "MERGED"
        # Pending pairs involving a retired row cannot later form a merge cycle.
        await self.session.execute(
            update(Candidate)
            .where(
                Candidate.id != row.id,
                Candidate.resolved_at.is_(None),
                (Candidate.left_job_id == retired.id)
                | (Candidate.right_job_id == retired.id),
            )
            .values(resolved_at=now, resolution="JOB_RETIRED")
        )
        await self.session.flush()
        return await self.detail(identity)
