"""Pydantic schemas for the Source Registry API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceResponse(BaseModel):
    """Response schema representing a registered job source."""

    id: uuid.UUID = Field(description="Unique source ID")
    name: str = Field(description="Source name")
    company: str | None = Field(default=None, description="Company name")
    url: str = Field(description="Career page or API endpoint URL")
    country: str | None = Field(default=None, description="Source country")
    ats_type: str = Field(description="ATS platform type (e.g. greenhouse, lever)")
    active: bool = Field(description="Whether the source is active for discovery")
    adapter_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific configuration",
    )
    pagination_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Pagination configuration",
    )
    endpoint_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Endpoint query or header configuration",
    )
    rate_limit_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Rate limiting and retry configuration",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form metadata attributes",
    )
    created_at: datetime | None = Field(
        default=None,
        description="Timestamp when registered",
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Timestamp when last updated",
    )

    model_config = ConfigDict(from_attributes=True)


class SourceListResponse(BaseModel):
    """Response schema for listing registered sources."""

    items: list[SourceResponse] = Field(
        description="List of registered job discovery sources",
    )
    total: int = Field(description="Total count of sources matching filter criteria")


class SourceSyncResponse(BaseModel):
    """Response schema for catalog synchronization."""

    total_scanned: int = Field(description="Total entries processed from catalog")
    created: int = Field(description="Number of new sources registered")
    updated: int = Field(description="Number of existing sources updated")
    skipped: int = Field(description="Number of invalid entries skipped")
    errors: list[str] = Field(
        default_factory=list,
        description="Warnings or skipped entries during sync",
    )


class SourceProbeResponse(BaseModel):
    """Response schema for an individual source health probe."""

    source_id: uuid.UUID | None = Field(default=None, description="Source ID if known")
    url: str = Field(description="Target URL probed")
    is_reachable: bool = Field(
        description="Whether target returned a 2xx or 3xx terminal status"
    )
    status_code: int | None = Field(
        default=None, description="HTTP status code received"
    )
    latency_ms: float | None = Field(
        default=None, description="Total request latency in milliseconds"
    )
    final_url: str | None = Field(
        default=None, description="Final URL reached after any redirects"
    )
    redirect_count: int = Field(
        default=0, description="Number of redirect hops followed"
    )
    error_type: str | None = Field(
        default=None, description="Categorized error reason if probe failed"
    )
    error_message: str | None = Field(
        default=None, description="Descriptive error detail if probe failed"
    )
    ats_type: str | None = Field(default=None, description="Source ATS type if known")
    probed_at: datetime = Field(description="UTC timestamp of the probe")

    model_config = ConfigDict(from_attributes=True)


class SourceBatchProbeResponse(BaseModel):
    """Response schema for batch source health probe execution."""

    total_probed: int = Field(description="Total sources probed")
    reachable_count: int = Field(description="Number of sources successfully reached")
    unreachable_count: int = Field(
        description="Number of sources unreachable or failing"
    )
    results: list[SourceProbeResponse] = Field(
        default_factory=list, description="Detailed probe metrics per source"
    )

    model_config = ConfigDict(from_attributes=True)


class SourceUpdateRequest(BaseModel):
    """Request schema for updating operational configuration.

    Does NOT contain active.
    """

    name: str | None = Field(
        default=None, min_length=1, max_length=150, description="Display name"
    )
    adapter_config: dict[str, Any] | None = Field(
        default=None, description="Adapter parameters"
    )
    pagination_config: dict[str, Any] | None = Field(
        default=None, description="Pagination parameters"
    )
    endpoint_config: dict[str, Any] | None = Field(
        default=None, description="Endpoint query/header parameters"
    )
    rate_limit_config: dict[str, Any] | None = Field(
        default=None, description="Rate limit settings"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Operational metadata attributes"
    )

    model_config = ConfigDict(extra="forbid")


class SourceStatusUpdateRequest(BaseModel):
    """Request schema for explicitly setting source active/inactive status."""

    active: bool = Field(description="Whether the source is active for discovery")

    model_config = ConfigDict(extra="forbid")


class SourceStatsResponse(BaseModel):
    """Response schema for operational source statistics."""

    total_sources: int = Field(description="Total registered sources")
    active_sources: int = Field(description="Number of active sources")
    inactive_sources: int = Field(description="Number of inactive sources")
    by_ats_type: dict[str, int] = Field(
        default_factory=dict, description="Source count by ATS type"
    )
    by_country: dict[str, int] = Field(
        default_factory=dict, description="Source count by country"
    )

    model_config = ConfigDict(from_attributes=True)
