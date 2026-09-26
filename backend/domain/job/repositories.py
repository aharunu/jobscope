"""Job and RawJob repository protocols (domain ports)."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus


@runtime_checkable
class JobRepository(Protocol):
    """Domain repository interface for canonical Job persistence and retrieval."""

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job by its primary key ID."""
        ...

    async def get_by_source_and_external_id(
        self,
        source_id: uuid.UUID,
        external_job_id: str,
    ) -> Job | None:
        """Retrieve a job by its source and external ATS identifier."""
        ...

    async def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        """Retrieve a job by its normalized canonical URL."""
        ...

    async def save(self, job: Job) -> Job:
        """Persist or update a canonical job entity."""
        ...

    async def save_bulk(self, jobs: list[Job]) -> list[Job]:
        """Persist multiple canonical job entities in batch."""
        ...

    async def count(
        self,
        source_id: uuid.UUID | None = None,
        status: JobStatus | None = None,
    ) -> int:
        """Count jobs matching optional source and status filters."""
        ...

    async def get_job_detail(self, job_id: uuid.UUID) -> Job | None:
        """Retrieve a canonical job with related source metadata projected."""
        ...

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
        ...

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
        ...

    async def get_active_jobs_by_source(self, source_id: uuid.UUID) -> list[Job]:
        """Retrieve all currently active canonical jobs for a source."""
        ...


@runtime_checkable
class RawJobRepository(Protocol):
    """Domain repository interface for raw unparsed job data persistence."""

    async def save(self, raw_job: RawJob) -> RawJob:
        """Persist an unparsed raw job payload entry."""
        ...

    async def get_by_id(self, raw_job_id: uuid.UUID) -> RawJob | None:
        """Retrieve a raw job entry by its ID."""
        ...

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[RawJob]:
        """Retrieve all historical raw payloads associated with a canonical job."""
        ...
