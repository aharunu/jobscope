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
