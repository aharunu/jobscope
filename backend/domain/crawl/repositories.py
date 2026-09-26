"""CrawlRun repository protocol (domain port)."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction


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

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve the most recent crawl run for a source."""
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
