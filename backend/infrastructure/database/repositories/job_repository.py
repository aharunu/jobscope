"""SQLAlchemy implementation of JobRepository and RawJobRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.infrastructure.database.models.job import JobModel, RawJobModel
from backend.infrastructure.database.models.source import SourceModel


class SQLAlchemyJobRepository(JobRepository):
    """SQLAlchemy async implementation of the JobRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job by its primary key ID."""
        orm_job = await self.session.get(JobModel, job_id)
        return orm_job.to_domain() if orm_job is not None else None

    async def get_by_source_and_external_id(
        self,
        source_id: uuid.UUID,
        external_job_id: str,
    ) -> Job | None:
        """Retrieve a job by its source and external ATS identifier."""
        stmt = select(JobModel).where(
            JobModel.source_id == source_id,
            JobModel.external_job_id == external_job_id,
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
        stmt = select(func.count()).select_from(JobModel)
        if source_id is not None:
            stmt = stmt.where(JobModel.source_id == source_id)
        if status is not None:
            stmt = stmt.where(JobModel.status == status)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_job_detail(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job with related source metadata projected."""
        stmt = (
            select(JobModel)
            .options(joinedload(JobModel.source))
            .where(JobModel.id == job_id)
        )
        result = await self.session.execute(stmt)
        orm_job = result.scalars().first()
        return orm_job.to_domain() if orm_job is not None else None

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
        stmt = select(JobModel).options(joinedload(JobModel.source))
        if ats_type is not None:
            stmt = stmt.join(SourceModel, JobModel.source_id == SourceModel.id)
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if status is not None:
            stmt = stmt.where(JobModel.status == status)

        if source_id is not None:
            stmt = stmt.where(JobModel.source_id == source_id)

        if company is not None and company.strip():
            stmt = stmt.where(JobModel.company == company.strip())

        if location is not None and location.strip():
            stmt = stmt.where(JobModel.location == location.strip())

        if work_mode is not None and work_mode.strip():
            stmt = stmt.where(JobModel.work_mode == work_mode.strip())

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
        stmt = select(func.count(JobModel.id))
        if ats_type is not None:
            stmt = stmt.join(SourceModel, JobModel.source_id == SourceModel.id)
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if status is not None:
            stmt = stmt.where(JobModel.status == status)

        if source_id is not None:
            stmt = stmt.where(JobModel.source_id == source_id)

        if company is not None and company.strip():
            stmt = stmt.where(JobModel.company == company.strip())

        if location is not None and location.strip():
            stmt = stmt.where(JobModel.location == location.strip())

        if work_mode is not None and work_mode.strip():
            stmt = stmt.where(JobModel.work_mode == work_mode.strip())

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
