"""SQLAlchemy implementation of JobRepository and RawJobRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.infrastructure.database.models.job import JobModel, RawJobModel


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
