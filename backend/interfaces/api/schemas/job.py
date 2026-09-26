"""Pydantic schemas for the canonical Jobs query and retrieval API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobSummaryResponse(BaseModel):
    """Read-oriented projection of a canonical job for summary listings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique job identifier")
    source_id: uuid.UUID = Field(description="Originating source identifier")
    canonical_url: str = Field(description="Normalized canonical job URL")
    company: str = Field(description="Company offering the position")
    title: str = Field(description="Job title")
    status: str = Field(description="Current status (ACTIVE, CLOSED)")
    external_job_id: str | None = Field(
        default=None, description="External ATS job identifier"
    )
    location: str | None = Field(default=None, description="Job location")
    work_mode: str | None = Field(
        default=None, description="Work mode (e.g. Remote, Hybrid, On-site)"
    )
    employment_type: str | None = Field(
        default=None, description="Employment type (e.g. Full-time, Contract)"
    )
    salary: str | None = Field(default=None, description="Salary or compensation text")
    published_at: datetime | None = Field(
        default=None, description="Original publication timestamp"
    )
    first_seen_at: datetime | None = Field(
        default=None, description="Timestamp when first discovered by JobScope"
    )
    last_seen_at: datetime | None = Field(
        default=None, description="Timestamp when last confirmed active by crawl"
    )
    closed_at: datetime | None = Field(
        default=None, description="Timestamp when closed"
    )
    created_at: datetime | None = Field(
        default=None, description="Record creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Record update timestamp"
    )
    source_name: str | None = Field(
        default=None, description="Originating source display name"
    )
    ats_type: str | None = Field(
        default=None, description="ATS platform type of source"
    )
    source_url: str | None = Field(
        default=None, description="Originating source base URL"
    )


class JobListResponse(BaseModel):
    """Paginated list of canonical jobs matching search/filter criteria."""

    model_config = ConfigDict(from_attributes=True)

    jobs: list[JobSummaryResponse] = Field(description="Page of job summaries")
    total: int = Field(description="Total count of jobs matching filters")
    limit: int = Field(description="Pagination limit applied")
    offset: int = Field(description="Pagination offset applied")


class JobDetailResponse(BaseModel):
    """Complete canonical job detail projection for inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique job identifier")
    source_id: uuid.UUID = Field(description="Originating source identifier")
    canonical_url: str = Field(description="Normalized canonical job URL")
    company: str = Field(description="Company offering the position")
    title: str = Field(description="Job title")
    description: str = Field(description="Full text job description")
    status: str = Field(description="Current status (ACTIVE, CLOSED)")
    content_hash: str = Field(description="SHA-256 content hash")
    external_job_id: str | None = Field(
        default=None, description="External ATS job identifier"
    )
    responsibilities: str | None = Field(
        default=None, description="Parsed job responsibilities"
    )
    location: str | None = Field(default=None, description="Job location")
    work_mode: str | None = Field(
        default=None, description="Work mode (e.g. Remote, Hybrid, On-site)"
    )
    employment_type: str | None = Field(
        default=None, description="Employment type (e.g. Full-time, Contract)"
    )
    salary: str | None = Field(default=None, description="Salary or compensation text")
    published_at: datetime | None = Field(
        default=None, description="Original publication timestamp"
    )
    first_seen_at: datetime | None = Field(
        default=None, description="Timestamp when first discovered by JobScope"
    )
    last_seen_at: datetime | None = Field(
        default=None, description="Timestamp when last confirmed active by crawl"
    )
    closed_at: datetime | None = Field(
        default=None, description="Timestamp when closed"
    )
    created_at: datetime | None = Field(
        default=None, description="Record creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Record update timestamp"
    )
    source_name: str | None = Field(
        default=None, description="Originating source display name"
    )
    ats_type: str | None = Field(
        default=None, description="ATS platform type of source"
    )
    source_url: str | None = Field(
        default=None, description="Originating source base URL"
    )
    requirements: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Parsed job requirements (populated in later matching phases)",
    )
