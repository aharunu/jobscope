"""Occurrence persistence port used by the existing ingestion orchestrator."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from backend.application.job_discovery.dtos import DiscoveredJobDTO
from backend.domain.crawl.enums import CrawlJobAction
from backend.domain.job.entities import Job


class OccurrenceStore(Protocol):
    async def prepare(self, jobs: list[Job]) -> None: ...
    async def observe(
        self, canonical: Job, discovered: DiscoveredJobDTO, now: datetime
    ) -> tuple[CrawlJobAction, UUID, UUID]: ...
    async def active_count(self, source_id: UUID) -> int: ...
    async def close_absent(
        self, source_id: UUID, seen: set[UUID], now: datetime
    ) -> list[UUID]: ...
