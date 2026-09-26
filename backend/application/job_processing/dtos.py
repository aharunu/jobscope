"""Job processing and ingestion data transfer objects (DTOs)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus


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


@dataclass(slots=True)
class JobFilterDTO:
    """Filter parameters for querying canonical jobs."""

    status: JobStatus | None = None
    source_id: uuid.UUID | None = None
    ats_type: str | None = None
    company: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    q: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(slots=True)
class JobSummaryDTO:
    """Read-oriented projection of a canonical job for summary listings."""

    id: uuid.UUID
    source_id: uuid.UUID
    canonical_url: str
    company: str
    title: str
    status: JobStatus
    external_job_id: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    salary: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_name: str | None = None
    ats_type: str | None = None
    source_url: str | None = None


@dataclass(slots=True)
class JobDetailDTO:
    """Complete canonical job detail projection for inspection."""

    id: uuid.UUID
    source_id: uuid.UUID
    canonical_url: str
    company: str
    title: str
    description: str
    status: JobStatus
    content_hash: str
    external_job_id: str | None = None
    responsibilities: str | None = None
    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None
    salary: str | None = None
    published_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_name: str | None = None
    ats_type: str | None = None
    source_url: str | None = None
    requirements: list[dict[str, Any]] = field(default_factory=list)
