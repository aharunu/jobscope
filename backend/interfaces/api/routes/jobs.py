"""API routes for canonical job exploration, retrieval, and search."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.application.job_processing.dtos import JobFilterDTO
from backend.domain.job.enums import JobStatus
from backend.interfaces.api.dependencies import JobQueryServiceDep
from backend.interfaces.api.schemas.job import (
    JobDetailResponse,
    JobListResponse,
    JobSummaryResponse,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=JobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List canonical jobs",
    description=(
        "Retrieve canonical jobs matching optional search and filter criteria "
        "with bounded pagination and deterministic ordering."
    ),
)
async def list_jobs(
    query_service: JobQueryServiceDep,
    job_status: JobStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by job status (ACTIVE, CLOSED)",
    ),
    source_id: uuid.UUID | None = Query(
        default=None,
        description="Filter by originating source ID",
    ),
    ats_type: str | None = Query(
        default=None,
        description="Filter by ATS platform type (e.g. lever)",
    ),
    company: str | None = Query(
        default=None,
        description="Filter by company name",
    ),
    location: str | None = Query(
        default=None,
        description="Filter by location string",
    ),
    work_mode: str | None = Query(
        default=None,
        description="Filter by work mode (e.g. Remote, Hybrid, On-site)",
    ),
    employment_type: str | None = Query(
        default=None,
        description="Filter by employment type (e.g. Full-time, Contract)",
    ),
    q: str | None = Query(
        default=None,
        description="Case-insensitive substring search across title and company",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of jobs to return (1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
) -> JobListResponse:
    """List canonical jobs with multi-attribute filtering and pagination."""
    filter_dto = JobFilterDTO(
        status=job_status,
        source_id=source_id,
        ats_type=ats_type,
        company=company,
        location=location,
        work_mode=work_mode,
        employment_type=employment_type,
        q=q,
        limit=limit,
        offset=offset,
    )
    items, total = await query_service.list_jobs(filter_dto)
    return JobListResponse(
        jobs=[JobSummaryResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get canonical job details",
    description="Retrieve full canonical job detail by its unique identifier.",
)
async def get_job(
    query_service: JobQueryServiceDep,
    job_id: uuid.UUID = Path(description="Unique canonical job ID"),
) -> JobDetailResponse:
    """Retrieve details for an individual canonical job."""
    job = await query_service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found",
        )
    return JobDetailResponse.model_validate(job)
