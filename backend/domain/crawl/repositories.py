"""CrawlRun repository protocol (domain port)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol, runtime_checkable

from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus


@runtime_checkable
class CrawlRunRepository(Protocol):
    """Domain repository interface for CrawlRun and CrawlRunJob persistence."""

    async def create_run(self, run: CrawlRun) -> CrawlRun:
        """Persist a new crawl run record."""
        ...

    async def update_run(self, run: CrawlRun) -> CrawlRun:
        """Update an existing crawl run record."""
        ...

    async def get_by_id(self, run_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve a crawl run by its primary key ID."""
        ...

    async def get_run_detail(self, run_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve a crawl run by its primary key ID with source metadata."""
        ...

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve the most recent crawl run for a source."""
        ...

    async def list_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRun]:
        """List crawl runs matching filter criteria with deterministic ordering."""
        ...

    async def count_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """Count total crawl runs matching filter criteria."""
        ...

    async def record_job_action(
        self,
        run_id: uuid.UUID,
        job_id: uuid.UUID,
        action: CrawlJobAction,
    ) -> None:
        """Record an action performed on a job during a crawl run."""
        ...

    async def record_job_actions(self, links: list[CrawlRunJob]) -> None:
        """Record multiple job actions in batch."""
        ...

    async def list_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRunJob]:
        """List job actions for a specific crawl run with deterministic ordering."""
        ...

    async def count_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
    ) -> int:
        """Count total job actions for a specific crawl run."""
        ...
