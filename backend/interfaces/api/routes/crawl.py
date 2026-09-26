"""FastAPI route handlers for crawl execution."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from backend.application.job_discovery.dtos import CrawlRunFilterDTO
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.interfaces.api.dependencies.crawler import (
    CrawlerOrchestratorDep,
    CrawlHistoryServiceDep,
)
from backend.interfaces.api.dependencies.sources import SourceRegistryDep
from backend.interfaces.api.schemas.crawl import (
    CrawlRunJobItemResponse,
    CrawlRunJobListResponse,
    CrawlRunListResponse,
    CrawlRunRequest,
    CrawlRunResponse,
    CrawlRunSummaryResponse,
    CrawlSourceResultResponse,
)

router = APIRouter(prefix="/crawl", tags=["Crawl"])


@router.post(
    "/run",
    response_model=CrawlRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger operational crawl run",
    description=(
        "Synchronously triggers job discovery and persistence for a single source, "
        "active sources filtered by ATS type, or all active registered sources. "
        "The optional limit parameter restricts the maximum number of sources crawled."
    ),
)
async def run_crawl(
    orchestrator: CrawlerOrchestratorDep,
    source_service: SourceRegistryDep,
    payload: CrawlRunRequest = Body(default_factory=CrawlRunRequest),
) -> CrawlRunResponse:
    """Execute operational crawl run."""
    # 1. Single source crawl
    if payload.source_id is not None:
        source = await source_service.get_source(payload.source_id)
        if source is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source with ID '{payload.source_id}' not found",
            )
        if not source.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Source with ID '{payload.source_id}' is inactive "
                    "and cannot be crawled."
                ),
            )

        exec_result = await orchestrator.crawl_source(payload.source_id)
        results = [exec_result]

    # 2. Filtered by ATS type
    elif payload.ats_type is not None:
        results = await orchestrator.crawl_sources_by_ats_type(
            ats_type=payload.ats_type,
            limit=payload.limit,
        )

    # 3. All active sources
    else:
        results = await orchestrator.crawl_all_active_sources(
            limit=payload.limit,
        )

    # Transform into API response format
    runs: list[CrawlSourceResultResponse] = []
    successful_count = 0
    failed_count = 0

    for res in results:
        status_str = getattr(res.status, "value", str(res.status))
        if res.success:
            successful_count += 1
        else:
            failed_count += 1

        runs.append(
            CrawlSourceResultResponse(
                crawl_run_id=res.crawl_run_id,
                source_id=res.source_id,
                source_name=res.source_name,
                ats_type=res.ats_type,
                status=status_str,
                jobs_found=res.jobs_found,
                jobs_created=res.jobs_created,
                jobs_updated=res.jobs_updated,
                jobs_unchanged=res.jobs_unchanged,
                jobs_closed=res.jobs_closed,
                error_count=res.error_count,
                duration_ms=res.duration_ms,
                error_type=res.error_type,
                error_message=res.error_message,
            )
        )

    return CrawlRunResponse(
        total_sources_crawled=len(results),
        successful_crawls=successful_count,
        failed_crawls=failed_count,
        runs=runs,
    )


@router.get(
    "/runs",
    response_model=CrawlRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical crawl runs",
    description=(
        "Retrieve historical crawl runs with optional filtering by source_id, "
        "status, ats_type, and date range with deterministic pagination."
    ),
)
async def list_crawl_runs(
    history_service: CrawlHistoryServiceDep,
    source_id: uuid.UUID | None = Query(
        default=None,
        description="Filter by source ID",
    ),
    crawl_status: CrawlStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by crawl status (RUNNING, COMPLETED, FAILED, PARTIAL)",
    ),
    ats_type: str | None = Query(
        default=None,
        description="Filter by ATS platform type (e.g. lever)",
    ),
    date_from: datetime | None = Query(
        default=None,
        description="Filter runs created on or after this timestamp (inclusive)",
    ),
    date_to: datetime | None = Query(
        default=None,
        description="Filter runs created before this timestamp (exclusive)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of runs to return (1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
) -> CrawlRunListResponse:
    """List historical crawl runs."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must not be later than date_to",
        )

    filter_dto = CrawlRunFilterDTO(
        source_id=source_id,
        status=crawl_status,
        ats_type=ats_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    items, total = await history_service.list_runs(filter_dto)
    return CrawlRunListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            CrawlRunSummaryResponse(
                id=run.id,
                source_id=run.source_id,
                source_name=run.source_name,
                ats_type=run.ats_type,
                status=getattr(run.status, "value", str(run.status)),
                started_at=run.started_at,
                finished_at=run.finished_at,
                duration_ms=run.duration_ms,
                jobs_found=run.jobs_found,
                jobs_created=run.jobs_created,
                jobs_updated=run.jobs_updated,
                jobs_unchanged=run.jobs_unchanged,
                jobs_closed=run.jobs_closed,
                error_count=run.error_count,
                created_at=run.created_at,
            )
            for run in items
        ],
    )


@router.get(
    "/runs/{crawl_run_id}",
    response_model=CrawlRunSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get crawl run details",
    description=(
        "Retrieve execution details and performance metrics for an "
        "individual crawl run."
    ),
)
async def get_crawl_run(
    history_service: CrawlHistoryServiceDep,
    crawl_run_id: uuid.UUID = Path(description="Unique crawl run ID"),
) -> CrawlRunSummaryResponse:
    """Retrieve details for an individual crawl run."""
    run = await history_service.get_run(crawl_run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CrawlRun with ID '{crawl_run_id}' not found",
        )
    return CrawlRunSummaryResponse(
        id=run.id,
        source_id=run.source_id,
        source_name=run.source_name,
        ats_type=run.ats_type,
        status=getattr(run.status, "value", str(run.status)),
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_ms=run.duration_ms,
        jobs_found=run.jobs_found,
        jobs_created=run.jobs_created,
        jobs_updated=run.jobs_updated,
        jobs_unchanged=run.jobs_unchanged,
        jobs_closed=run.jobs_closed,
        error_count=run.error_count,
        created_at=run.created_at,
    )


@router.get(
    "/runs/{crawl_run_id}/jobs",
    response_model=CrawlRunJobListResponse,
    status_code=status.HTTP_200_OK,
    summary="List job actions for a crawl run",
    description=(
        "Retrieve paginated list of job actions recorded during a specific crawl run."
    ),
)
async def list_crawl_run_jobs(
    history_service: CrawlHistoryServiceDep,
    crawl_run_id: uuid.UUID = Path(description="Unique crawl run ID"),
    action: CrawlJobAction | None = Query(
        default=None,
        description="Filter by action (CREATED, UPDATED, UNCHANGED, CLOSED)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
) -> CrawlRunJobListResponse:
    """Retrieve job actions recorded during a specific crawl run."""
    run = await history_service.get_run(crawl_run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CrawlRun with ID '{crawl_run_id}' not found",
        )
    items, total = await history_service.list_run_jobs(
        run_id=crawl_run_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return CrawlRunJobListResponse(
        crawl_run_id=crawl_run_id,
        total=total,
        limit=limit,
        offset=offset,
        items=[
            CrawlRunJobItemResponse(
                job_id=item.job_id,
                crawl_run_id=item.crawl_run_id,
                action=getattr(item.action, "value", str(item.action)),
                title=item.title,
                company=item.company,
                canonical_url=item.canonical_url,
                status=item.status,
                first_seen_at=item.first_seen_at,
                last_seen_at=item.last_seen_at,
            )
            for item in items
        ],
    )
