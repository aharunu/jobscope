"""Job processing and ingestion data transfer objects (DTOs)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from backend.domain.crawl.enums import CrawlStatus


@dataclass(slots=True)
class JobIngestionResultDTO:
    """Summary of the normalization, deduplication, and persistence lifecycle."""

    crawl_run_id: uuid.UUID
    source_id: uuid.UUID
    status: CrawlStatus
    jobs_found: int
    jobs_created: int
    jobs_updated: int
    jobs_unchanged: int
    jobs_closed: int
    error_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
