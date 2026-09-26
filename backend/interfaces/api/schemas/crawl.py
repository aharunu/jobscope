"""Pydantic schemas for the crawl execution API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CrawlRunRequest(BaseModel):
    """Request payload for manually triggering an operational crawl run.

    Supports:
    - Crawl a single source by `source_id`.
    - Crawl active sources filtered by `ats_type`.
    - Crawl all active sources when both `source_id` and `ats_type` are omitted.
    - Bound batch execution size by `limit` (maximum sources to crawl).
    """

    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Target a specific registered source ID. If omitted, crawls active sources."
        ),
    )
    ats_type: str | None = Field(
        default=None,
        description="Filter active sources by ATS platform (e.g. 'lever').",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of active sources to crawl in this batch.",
    )


class CrawlSourceResultResponse(BaseModel):
    """Per-source crawl execution outcome."""

    model_config = ConfigDict(from_attributes=True)

    crawl_run_id: uuid.UUID | None = Field(
        default=None,
        description="Persistent ID of the CrawlRun audit record.",
    )
    source_id: uuid.UUID = Field(description="Target source unique ID.")
    source_name: str = Field(description="Target source display name.")
    ats_type: str = Field(description="Target source ATS platform type.")
    status: str = Field(
        description="Final execution status (COMPLETED, PARTIAL, FAILED)."
    )
    jobs_found: int = Field(
        default=0,
        description="Total job postings discovered during crawl.",
    )
    jobs_created: int = Field(
        default=0,
        description="New canonical job postings created and persisted.",
    )
    jobs_updated: int = Field(
        default=0,
        description="Existing canonical job postings updated.",
    )
    jobs_unchanged: int = Field(
        default=0,
        description="Existing canonical job postings whose content hash was unchanged.",
    )
    jobs_closed: int = Field(
        default=0,
        description="Existing canonical job postings closed due to verified absence.",
    )
    error_count: int = Field(
        default=0,
        description="Count of item-level errors encountered during processing.",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Total crawl execution duration in milliseconds.",
    )
    error_type: str | None = Field(
        default=None,
        description="Error classification code if crawl failed.",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error explanation if crawl failed.",
    )


class CrawlRunResponse(BaseModel):
    """Aggregate response for a batch crawl execution."""

    model_config = ConfigDict(from_attributes=True)

    total_sources_crawled: int = Field(
        description="Total number of active sources crawled in this execution batch."
    )
    successful_crawls: int = Field(
        description="Number of sources that completed successfully or partially."
    )
    failed_crawls: int = Field(
        description="Number of sources whose crawl run ended in FAILED status."
    )
    runs: list[CrawlSourceResultResponse] = Field(
        description="Detailed execution results for each crawled source."
    )


class CrawlRunSummaryResponse(BaseModel):
    """Historical crawl run summary item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique crawl run identifier")
    source_id: uuid.UUID = Field(description="Target source identifier")
    source_name: str = Field(description="Display name of the target source")
    ats_type: str = Field(description="ATS platform type of the target source")
    status: str = Field(
        description="Crawl run outcome status (RUNNING, COMPLETED, FAILED, PARTIAL)"
    )
    started_at: datetime = Field(description="Run initiation timestamp")
    finished_at: datetime | None = Field(
        default=None, description="Run completion timestamp"
    )
    duration_ms: float | None = Field(
        default=None,
        description="Run duration in milliseconds (null if RUNNING)",
    )
    jobs_found: int = Field(default=0, description="Total jobs discovered")
    jobs_created: int = Field(default=0, description="Total new jobs created")
    jobs_updated: int = Field(default=0, description="Total existing jobs updated")
    jobs_unchanged: int = Field(default=0, description="Total existing jobs unchanged")
    jobs_closed: int = Field(default=0, description="Total jobs marked closed")
    error_count: int = Field(default=0, description="Total errors encountered")
    created_at: datetime = Field(description="Record creation timestamp")


class CrawlRunListResponse(BaseModel):
    """Paginated list of historical crawl runs."""

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(description="Total count of runs matching filters")
    limit: int = Field(description="Pagination limit applied")
    offset: int = Field(description="Pagination offset applied")
    items: list[CrawlRunSummaryResponse] = Field(description="Page of crawl runs")


class CrawlRunJobItemResponse(BaseModel):
    """Item record of a job action during a crawl run."""

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID = Field(description="Canonical Job identifier")
    crawl_run_id: uuid.UUID = Field(description="Crawl run identifier")
    action: str = Field(
        description="Action taken on job (CREATED, UPDATED, UNCHANGED, CLOSED)"
    )
    title: str | None = Field(default=None, description="Job title")
    company: str | None = Field(default=None, description="Company name")
    canonical_url: str | None = Field(default=None, description="Canonical job URL")
    status: str | None = Field(default=None, description="Job status (ACTIVE, CLOSED)")
    first_seen_at: datetime | None = Field(
        default=None, description="Timestamp first discovered"
    )
    last_seen_at: datetime | None = Field(
        default=None, description="Timestamp last seen in crawl"
    )


class CrawlRunJobListResponse(BaseModel):
    """Paginated list of job actions for a crawl run."""

    model_config = ConfigDict(from_attributes=True)

    crawl_run_id: uuid.UUID = Field(description="Target crawl run identifier")
    total: int = Field(description="Total count of job actions in run matching filter")
    limit: int = Field(description="Pagination limit applied")
    offset: int = Field(description="Pagination offset applied")
    items: list[CrawlRunJobItemResponse] = Field(description="Page of job actions")
