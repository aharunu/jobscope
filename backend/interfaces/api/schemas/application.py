"""Pydantic schemas for the Application Tracking API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.application.enums import ApplicationStatus


class ApplicationCreateRequest(BaseModel):
    """Payload to start tracking a job application."""

    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID = Field(
        description="Unique identifier of the canonical job to track",
    )
    status: ApplicationStatus = Field(
        default=ApplicationStatus.INTERESTED,
        description="Initial lifecycle status (default: INTERESTED)",
    )
    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional candidate notes regarding the job or application",
    )


class ApplicationStatusUpdateRequest(BaseModel):
    """Payload to transition an application's lifecycle status."""

    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus = Field(
        description="Target lifecycle status to transition into",
    )


class ApplicationNotesUpdateRequest(BaseModel):
    """Payload to update candidate notes on a tracked application."""

    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(
        default=None,
        max_length=5000,
        description="Updated candidate notes",
    )


class ApplicationJobSummaryResponse(BaseModel):
    """Summary of canonical job details embedded in an application response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Canonical job ID")
    canonical_url: str = Field(description="Normalized job URL")
    company: str = Field(description="Company offering the position")
    title: str = Field(description="Job title")
    status: str = Field(description="Job lifecycle status (ACTIVE, CLOSED)")
    location: str | None = Field(default=None, description="Job location")
    work_mode: str | None = Field(default=None, description="Work mode")
    employment_type: str | None = Field(default=None, description="Employment type")
    salary: str | None = Field(default=None, description="Salary or compensation text")
    source_name: str | None = Field(
        default=None, description="Originating source display name"
    )


class ApplicationStatusHistoryResponse(BaseModel):
    """Historical status transition audit record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Status history record ID")
    application_id: uuid.UUID = Field(description="Related application ID")
    from_status: str = Field(description="Previous status before transition")
    to_status: str = Field(description="New status after transition")
    changed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the transition occurred",
    )


class ApplicationResponse(BaseModel):
    """Full representation of a tracked application."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(description="Unique application ID")
    job_id: uuid.UUID = Field(description="Associated canonical job ID")
    user_id: uuid.UUID = Field(description="Candidate user ID")
    status: str = Field(description="Current application lifecycle status")
    notes: str | None = Field(default=None, description="Private candidate notes")
    created_at: datetime | None = Field(
        default=None, description="Tracking creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    job: ApplicationJobSummaryResponse | None = Field(
        default=None,
        description="Embedded canonical job details if loaded",
    )
    status_history: list[ApplicationStatusHistoryResponse] = Field(
        default_factory=list,
        description="Audit log of status transitions",
    )


class ApplicationListResponse(BaseModel):
    """Paginated list of tracked applications."""

    items: list[ApplicationResponse] = Field(description="List of tracked applications")
    total: int = Field(
        description="Total count of applications matching query criteria"
    )
    limit: int = Field(description="Page size limit")
    offset: int = Field(description="Page offset")
