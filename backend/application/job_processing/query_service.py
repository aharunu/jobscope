"""Job query application service for exploration and retrieval."""

from __future__ import annotations

import uuid

from backend.application.job_processing.dtos import (
    JobDetailDTO,
    JobFilterDTO,
    JobSummaryDTO,
)
from backend.domain.job.entities import Job
from backend.domain.job.repositories import JobRepository


class JobQueryService:
    """Application service coordinating canonical job search, filtering, and retrieval.

    Upholds Clean Architecture:
    - Pure application service with zero infrastructure or ORM dependencies.
    - Validates pagination boundaries and filter semantics.
    - Projects safe read DTOs excluding sensitive source configurations.
    - Defensive fallback for source metadata when unjoined.
    """

    def __init__(self, job_repo: JobRepository) -> None:
        self._job_repo = job_repo

    async def list_jobs(
        self,
        filter_: JobFilterDTO,
    ) -> tuple[list[JobSummaryDTO], int]:
        """List canonical jobs matching filter criteria with pagination."""
        self._validate_pagination(filter_.limit, filter_.offset)

        # Normalize empty string filters to None
        company = (
            filter_.company.strip()
            if filter_.company and filter_.company.strip()
            else None
        )
        location = (
            filter_.location.strip()
            if filter_.location and filter_.location.strip()
            else None
        )
        work_mode = (
            filter_.work_mode.strip()
            if filter_.work_mode and filter_.work_mode.strip()
            else None
        )
        employment_type = (
            filter_.employment_type.strip()
            if filter_.employment_type and filter_.employment_type.strip()
            else None
        )
        search_query = filter_.q.strip() if filter_.q and filter_.q.strip() else None
        ats_type = (
            filter_.ats_type.strip()
            if filter_.ats_type and filter_.ats_type.strip()
            else None
        )

        jobs = await self._job_repo.list_jobs(
            status=filter_.status,
            source_id=filter_.source_id,
            ats_type=ats_type,
            company=company,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            search_query=search_query,
            limit=filter_.limit,
            offset=filter_.offset,
        )
        total = await self._job_repo.count_jobs(
            status=filter_.status,
            source_id=filter_.source_id,
            ats_type=ats_type,
            company=company,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            search_query=search_query,
        )

        items = [self._to_summary_dto(job) for job in jobs]
        return items, total

    async def get_job(self, job_id: uuid.UUID) -> JobDetailDTO | None:
        """Retrieve full detail for an individual canonical job."""
        job = await self._job_repo.get_job_detail(job_id)
        if job is None:
            return None
        return self._to_detail_dto(job)

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        """Enforce strict bounded pagination."""
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")
        if offset < 0:
            raise ValueError(f"Offset must be non-negative, got {offset}")

    @staticmethod
    def _to_summary_dto(job: Job) -> JobSummaryDTO:
        """Map canonical Job domain entity to public summary DTO."""
        return JobSummaryDTO(
            id=job.id,
            source_id=job.source_id,
            canonical_url=job.canonical_url,
            company=job.company,
            title=job.title,
            status=job.status,
            external_job_id=job.external_job_id,
            location=job.location,
            work_mode=job.work_mode,
            employment_type=job.employment_type,
            salary=job.salary,
            published_at=job.published_at,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            closed_at=job.closed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            source_name=job.source_name or "Unknown",
            ats_type=job.ats_type or "unknown",
            source_url=job.source_url or "",
        )

    @staticmethod
    def _to_detail_dto(job: Job) -> JobDetailDTO:
        """Map canonical Job domain entity to public detail DTO."""
        return JobDetailDTO(
            id=job.id,
            source_id=job.source_id,
            canonical_url=job.canonical_url,
            company=job.company,
            title=job.title,
            description=job.description,
            status=job.status,
            content_hash=job.content_hash,
            external_job_id=job.external_job_id,
            responsibilities=job.responsibilities,
            location=job.location,
            work_mode=job.work_mode,
            employment_type=job.employment_type,
            salary=job.salary,
            published_at=job.published_at,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            closed_at=job.closed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
            source_name=job.source_name or "Unknown",
            ats_type=job.ats_type or "unknown",
            source_url=job.source_url or "",
            requirements=[],
        )
