"""SQLAlchemy implementation of JobRepository and RawJobRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.infrastructure.database.models.dedup import JobOccurrenceModel
from backend.infrastructure.database.models.job import JobModel, RawJobModel
from backend.infrastructure.database.models.source import SourceModel


class SQLAlchemyJobRepository(JobRepository):
    """SQLAlchemy async implementation of the JobRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job by its primary key ID."""
        orm_job = await self.session.get(JobModel, job_id)
        visited = {job_id}
        while orm_job is not None and orm_job.merged_into_id is not None:
            if orm_job.merged_into_id in visited or len(visited) >= 64:
                return None  # Defensive cycle guard; review merge never creates cycles.
            visited.add(orm_job.merged_into_id)
            orm_job = await self.session.get(JobModel, orm_job.merged_into_id)
        return orm_job.to_domain() if orm_job is not None else None

    async def get_by_source_and_external_id(
        self,
        source_id: uuid.UUID,
        external_job_id: str,
    ) -> Job | None:
        """Retrieve a job by its source and external ATS identifier."""
        stmt = select(JobModel).where(
            JobModel.merged_into_id.is_(None),
            sa.or_(
                sa.and_(
                    JobModel.source_id == source_id,
                    JobModel.external_job_id == external_job_id,
                ),
                sa.exists().where(
                    JobOccurrenceModel.job_id == JobModel.id,
                    JobOccurrenceModel.source_id == source_id,
                    JobOccurrenceModel.external_job_id == external_job_id,
                ),
            ),
        )
        result = await self.session.execute(stmt)
        orm_job = result.scalars().first()
        return orm_job.to_domain() if orm_job is not None else None

    async def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        """Retrieve a job by its normalized canonical URL."""
        stmt = select(JobModel).where(JobModel.canonical_url == canonical_url)
        result = await self.session.execute(stmt)
        orm_job = result.scalars().first()
        return orm_job.to_domain() if orm_job is not None else None

    async def save(self, job: Job) -> Job:
        """Persist or update a canonical job entity via session.merge."""
        orm_job = JobModel.from_domain(job)
        merged = await self.session.merge(orm_job)
        await self.session.flush()
        return merged.to_domain()

    async def save_bulk(self, jobs: list[Job]) -> list[Job]:
        """Persist multiple canonical job entities in batch."""
        saved: list[Job] = []
        for job in jobs:
            orm_job = JobModel.from_domain(job)
            merged = await self.session.merge(orm_job)
            saved.append(merged.to_domain())
        await self.session.flush()
        return saved

    async def count(
        self,
        source_id: uuid.UUID | None = None,
        status: JobStatus | None = None,
    ) -> int:
        """Count jobs matching optional source and status filters."""
        stmt = (
            select(func.count())
            .select_from(JobModel)
            .where(JobModel.merged_into_id.is_(None))
        )
        if source_id is not None:
            stmt = stmt.where(
                sa.or_(
                    JobModel.source_id == source_id,
                    sa.exists().where(
                        JobOccurrenceModel.job_id == JobModel.id,
                        JobOccurrenceModel.source_id == source_id,
                    ),
                )
            )
        if status is not None:
            stmt = stmt.where(JobModel.status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_job_detail(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job with related source metadata projected."""
        stmt = (
            select(JobModel)
            .options(
                joinedload(JobModel.source),
                selectinload(JobModel.requirements),
            )
            .where(JobModel.id == job_id)
        )
        result = await self.session.execute(stmt)
        orm_job = result.scalars().first()
        if orm_job is None:
            return None
        if orm_job.merged_into_id is not None:
            resolved = await self.get_by_id(job_id)
            if resolved is None:
                return None
            return await self.get_job_detail(resolved.id)
        job = orm_job.to_domain()
        rows = (
            await self.session.execute(
                select(JobOccurrenceModel, SourceModel)
                .join(SourceModel, SourceModel.id == JobOccurrenceModel.source_id)
                .where(JobOccurrenceModel.job_id == job.id)
                .order_by(JobOccurrenceModel.first_seen_at, JobOccurrenceModel.id)
            )
        ).all()
        job.occurrences = [
            {
                "id": row.id,
                "source_id": row.source_id,
                "source": source.name,
                "ats_type": source.ats_type,
                "external_job_id": row.external_job_id,
                "url": row.canonical_url,
                "status": row.status,
                "first_seen_at": row.first_seen_at,
                "last_seen_at": row.last_seen_at,
            }
            for row, source in rows
        ]
        return job

    async def list_jobs(
        self,
        status: JobStatus | None = None,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
        company: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        """List canonical jobs matching filter criteria with deterministic ordering."""
        stmt = (
            select(JobModel)
            .options(joinedload(JobModel.source))
            .where(JobModel.merged_into_id.is_(None))
        )
        if ats_type is not None:
            stmt = stmt.where(
                sa.or_(
                    sa.exists().where(
                        JobOccurrenceModel.job_id == JobModel.id,
                        JobOccurrenceModel.source_id == SourceModel.id,
                        SourceModel.ats_type == ats_type,
                    ),
                    sa.exists().where(
                        JobModel.source_id == SourceModel.id,
                        SourceModel.ats_type == ats_type,
                    ),
                )
            )

        if status is not None:
            stmt = stmt.where(JobModel.status == status)

        if source_id is not None:
            stmt = stmt.where(
                sa.or_(
                    JobModel.source_id == source_id,
                    sa.exists().where(
                        JobOccurrenceModel.job_id == JobModel.id,
                        JobOccurrenceModel.source_id == source_id,
                    ),
                )
            )

        if company is not None and company.strip():
            c_pat = f"%{company.strip()}%"
            stmt = stmt.where(JobModel.company.ilike(c_pat))

        if location is not None and location.strip():
            loc_pat = f"%{location.strip()}%"
            stmt = stmt.where(JobModel.location.ilike(loc_pat))

        if work_mode is not None and work_mode.strip():
            clean_mode = work_mode.strip().lower().replace("-", "")
            norm_mode = sa.func.replace(sa.func.lower(JobModel.work_mode), "-", "")
            stmt = stmt.where(norm_mode == clean_mode)

        if employment_type is not None and employment_type.strip():
            stmt = stmt.where(JobModel.employment_type == employment_type.strip())

        if search_query is not None and search_query.strip():
            q_pat = f"%{search_query.strip()}%"
            stmt = stmt.where(
                sa.or_(
                    JobModel.title.ilike(q_pat),
                    JobModel.company.ilike(q_pat),
                )
            )

        stmt = (
            stmt.order_by(JobModel.first_seen_at.desc(), JobModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [orm_job.to_domain() for orm_job in result.scalars().all()]

    async def count_jobs(
        self,
        status: JobStatus | None = None,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
        company: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        """Count canonical jobs matching filter criteria."""
        stmt = select(func.count(JobModel.id)).where(JobModel.merged_into_id.is_(None))
        if ats_type is not None:
            stmt = stmt.where(
                sa.or_(
                    sa.exists().where(
                        JobOccurrenceModel.job_id == JobModel.id,
                        JobOccurrenceModel.source_id == SourceModel.id,
                        SourceModel.ats_type == ats_type,
                    ),
                    sa.exists().where(
                        JobModel.source_id == SourceModel.id,
                        SourceModel.ats_type == ats_type,
                    ),
                )
            )

        if status is not None:
            stmt = stmt.where(JobModel.status == status)

        if source_id is not None:
            stmt = stmt.where(
                sa.or_(
                    JobModel.source_id == source_id,
                    sa.exists().where(
                        JobOccurrenceModel.job_id == JobModel.id,
                        JobOccurrenceModel.source_id == source_id,
                    ),
                )
            )

        if company is not None and company.strip():
            c_pat = f"%{company.strip()}%"
            stmt = stmt.where(JobModel.company.ilike(c_pat))

        if location is not None and location.strip():
            loc_pat = f"%{location.strip()}%"
            stmt = stmt.where(JobModel.location.ilike(loc_pat))

        if work_mode is not None and work_mode.strip():
            clean_mode = work_mode.strip().lower().replace("-", "")
            norm_mode = sa.func.replace(sa.func.lower(JobModel.work_mode), "-", "")
            stmt = stmt.where(norm_mode == clean_mode)

        if employment_type is not None and employment_type.strip():
            stmt = stmt.where(JobModel.employment_type == employment_type.strip())

        if search_query is not None and search_query.strip():
            q_pat = f"%{search_query.strip()}%"
            stmt = stmt.where(
                sa.or_(
                    JobModel.title.ilike(q_pat),
                    JobModel.company.ilike(q_pat),
                )
            )

        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_active_jobs_by_source(self, source_id: uuid.UUID) -> list[Job]:
        """Retrieve all currently active canonical jobs for a source."""
        stmt = (
            select(JobModel)
            .where(
                JobModel.source_id == source_id,
                JobModel.status == JobStatus.ACTIVE,
            )
            .order_by(JobModel.first_seen_at.desc(), JobModel.id.desc())
        )
        result = await self.session.execute(stmt)
        return [orm_job.to_domain() for orm_job in result.scalars().all()]


class SQLAlchemyRawJobRepository(RawJobRepository):
    """SQLAlchemy async implementation of the RawJobRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, raw_job: RawJob) -> RawJob:
        """Persist an unparsed raw job payload entry."""
        orm_raw = RawJobModel.from_domain(raw_job)
        merged = await self.session.merge(orm_raw)
        await self.session.flush()
        return merged.to_domain()

    async def get_by_id(self, raw_job_id: uuid.UUID) -> RawJob | None:
        """Retrieve a raw job entry by its ID."""
        orm_raw = await self.session.get(RawJobModel, raw_job_id)
        return orm_raw.to_domain() if orm_raw is not None else None

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[RawJob]:
        """Retrieve all historical raw payloads associated with a canonical job."""
        stmt = (
            select(RawJobModel)
            .where(RawJobModel.job_id == job_id)
            .order_by(RawJobModel.fetched_at.desc())
        )
        result = await self.session.execute(stmt)
        orm_raws: Sequence[RawJobModel] = result.scalars().all()
        return [r.to_domain() for r in orm_raws]
