"""CrawlRun and CrawlRunJob domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus


@dataclass(slots=True)
class CrawlRun:
    """Domain entity representing an operational crawl run.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    source_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: CrawlStatus = CrawlStatus.RUNNING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    jobs_found: int = 0
    jobs_created: int = 0
    jobs_updated: int = 0
    jobs_closed: int = 0
    error_count: int = 0
    created_at: datetime | None = None


@dataclass(slots=True)
class CrawlRunJob:
    """Domain entity representing a job action entry within a crawl run.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    crawl_run_id: uuid.UUID
    job_id: uuid.UUID
    action: CrawlJobAction
