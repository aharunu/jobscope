"""Job and RawJob domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.job.enums import (
    JobStatus,
    RequirementLevel,
    RequirementType,
)


@dataclass(slots=True)
class Job:
    """Domain entity representing a canonical job posting.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    source_id: uuid.UUID
    canonical_url: str
    company: str
    title: str
    description: str
    content_hash: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
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
    status: JobStatus = JobStatus.ACTIVE
    created_at: datetime | None = None
    updated_at: datetime | None = None
    source_name: str | None = None
    ats_type: str | None = None
    source_url: str | None = None


@dataclass(slots=True)
class RawJob:
    """Domain entity representing raw unparsed job data fetched from a source.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    job_id: uuid.UUID
    source_id: uuid.UUID
    raw_content: str
    content_type: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    fetched_at: datetime | None = None


@dataclass(slots=True)
class JobRequirement:
    """Domain entity representing a parsed/normalized requirement of a job posting.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    job_id: uuid.UUID
    type: RequirementType
    description: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    normalized_skill: str | None = None
    required_level: RequirementLevel = RequirementLevel.REQUIRED
    importance: str = "MEDIUM"
    criticality: str = "NORMAL"
    evidence: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
