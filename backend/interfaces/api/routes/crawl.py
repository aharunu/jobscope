"""FastAPI route handlers for crawl execution."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, status

from backend.interfaces.api.dependencies.crawler import CrawlerOrchestratorDep
from backend.interfaces.api.dependencies.sources import SourceRegistryDep
from backend.interfaces.api.schemas.crawl import (
    CrawlRunRequest,
    CrawlRunResponse,
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
