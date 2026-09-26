"""Pydantic schemas for the crawl execution API."""

from __future__ import annotations

import uuid

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
