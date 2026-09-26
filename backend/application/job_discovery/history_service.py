"""Crawl history application service."""

from __future__ import annotations

import uuid

from backend.application.job_discovery.dtos import (
    CrawlRunFilterDTO,
    CrawlRunJobItemDTO,
    CrawlRunSummaryDTO,
)
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlJobAction
from backend.domain.crawl.repositories import CrawlRunRepository


class CrawlHistoryService:
    """Application service coordinating crawl history inspection and audit queries.

    Upholds Clean Architecture:
    - Pure application service with zero infrastructure or ORM dependencies.
    - Validates pagination boundaries and filter semantics.
    - Projects safe read DTOs excluding sensitive source configurations.
    - Derives deterministic run durations and unchanged counters.
    """

    def __init__(self, repository: CrawlRunRepository) -> None:
        self._repository = repository

    async def list_runs(
        self,
        filter_: CrawlRunFilterDTO,
    ) -> tuple[list[CrawlRunSummaryDTO], int]:
        """List historical crawl runs matching filter criteria with pagination."""
        self._validate_pagination(filter_.limit, filter_.offset)
        self._validate_date_range(filter_.date_from, filter_.date_to)

        runs = await self._repository.list_runs(
            source_id=filter_.source_id,
            status=filter_.status,
            ats_type=filter_.ats_type,
            date_from=filter_.date_from,
            date_to=filter_.date_to,
            limit=filter_.limit,
            offset=filter_.offset,
        )
        total = await self._repository.count_runs(
            source_id=filter_.source_id,
            status=filter_.status,
            ats_type=filter_.ats_type,
            date_from=filter_.date_from,
            date_to=filter_.date_to,
        )

        items = [self._to_summary_dto(run) for run in runs]
        return items, total

    async def get_run(self, run_id: uuid.UUID) -> CrawlRunSummaryDTO | None:
        """Retrieve details for an individual crawl run."""
        run = await self._repository.get_run_detail(run_id)
        if run is None:
            return None
        return self._to_summary_dto(run)

    async def list_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CrawlRunJobItemDTO], int]:
        """List job actions associated with a specific crawl run."""
        self._validate_pagination(limit, offset)

        links = await self._repository.list_run_jobs(
            run_id=run_id,
            action=action,
            limit=limit,
            offset=offset,
        )
        total = await self._repository.count_run_jobs(
            run_id=run_id,
            action=action,
        )

        items = [
            CrawlRunJobItemDTO(
                job_id=link.job_id,
                crawl_run_id=link.crawl_run_id,
                action=link.action,
                title=link.title,
                company=link.company,
                canonical_url=link.canonical_url,
                status=link.job_status,
                first_seen_at=link.first_seen_at,
                last_seen_at=link.last_seen_at,
            )
            for link in links
        ]
        return items, total

    @staticmethod
    def _validate_pagination(limit: int, offset: int) -> None:
        """Enforce strict bounded pagination."""
        if limit < 1 or limit > 100:
            raise ValueError(f"Limit must be between 1 and 100, got {limit}")
        if offset < 0:
            raise ValueError(f"Offset must be non-negative, got {offset}")

    @staticmethod
    def _validate_date_range(date_from: object, date_to: object) -> None:
        """Validate half-open date interval consistency."""
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValueError("date_from must not be later than date_to")

    @staticmethod
    def _to_summary_dto(run: CrawlRun) -> CrawlRunSummaryDTO:
        """Map domain CrawlRun to projected summary DTO with derived fields."""
        duration_ms: float | None = None
        if run.finished_at is not None and run.started_at is not None:
            duration_ms = round(
                (run.finished_at - run.started_at).total_seconds() * 1000, 2
            )

        jobs_unchanged = max(
            0,
            run.jobs_found - run.jobs_created - run.jobs_updated - run.error_count,
        )

        return CrawlRunSummaryDTO(
            id=run.id,
            source_id=run.source_id,
            source_name=run.source_name or "Unknown",
            ats_type=run.ats_type or "unknown",
            status=run.status,
            started_at=run.started_at or run.created_at,
            finished_at=run.finished_at,
            duration_ms=duration_ms,
            jobs_found=run.jobs_found,
            jobs_created=run.jobs_created,
            jobs_updated=run.jobs_updated,
            jobs_unchanged=jobs_unchanged,
            jobs_closed=run.jobs_closed,
            error_count=run.error_count,
            created_at=run.created_at or run.started_at,
        )
