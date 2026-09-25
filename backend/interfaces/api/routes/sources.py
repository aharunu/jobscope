"""FastAPI routes for registered job discovery sources."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Path, Query, status

from backend.application.job_discovery.dtos import (
    SourceFilterDTO,
    SourceUpdateDTO,
)
from backend.interfaces.api.dependencies.sources import SourceRegistryDep
from backend.interfaces.api.schemas.source import (
    SourceBatchProbeResponse,
    SourceListResponse,
    SourceProbeResponse,
    SourceResponse,
    SourceStatsResponse,
    SourceStatusUpdateRequest,
    SourceSyncResponse,
    SourceUpdateRequest,
)

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get(
    "",
    response_model=SourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered job discovery sources",
    description=(
        "Retrieve registered job sources with optional active status, "
        "ATS type filtering, and text search."
    ),
)
async def list_sources(
    service: SourceRegistryDep,
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true/false/omitted for all)",
    ),
    active_only: bool = Query(
        default=False,
        description="Legacy filter: true to retrieve only active sources",
    ),
    ats_type: str | None = Query(
        default=None,
        description="Filter by ATS type (e.g. greenhouse, lever, workday, ashby)",
    ),
    search: str | None = Query(
        default=None,
        description="Search term matching source name, company, or URL",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of sources to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip for pagination",
    ),
) -> SourceListResponse:
    """List registered job sources."""
    filter_dto = SourceFilterDTO(
        active_only=active_only,
        is_active=is_active,
        ats_type=ats_type,
        search_query=search,
        limit=limit,
        offset=offset,
    )
    sources = await service.list_sources(filter_dto)
    total = await service.count_sources(
        active_only=active_only,
        is_active=is_active,
        ats_type=ats_type,
        search_query=search,
    )

    items = [SourceResponse.model_validate(s) for s in sources]
    return SourceListResponse(items=items, total=total)


@router.post(
    "/sync",
    response_model=SourceSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Synchronize sources from Markdown catalog",
    description=(
        "Imports and synchronizes job sources from data/turkish-job-sources.md "
        "into the PostgreSQL source registry."
    ),
)
async def sync_sources(
    service: SourceRegistryDep,
) -> SourceSyncResponse:
    """Synchronize source registry with canonical catalog."""
    result = await service.sync_from_catalog()
    return SourceSyncResponse(
        total_scanned=result.total_scanned,
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


@router.post(
    "/probe",
    response_model=SourceBatchProbeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch probe registered job sources",
    description=(
        "Concurrently probes registered sources for HTTP reachability "
        "and latency under bounded concurrency. Does not mutate database state."
    ),
)
async def probe_sources_batch(
    service: SourceRegistryDep,
    active_only: bool = Query(
        default=False,
        description="Probe only active sources",
    ),
    ats_type: str | None = Query(
        default=None,
        description="Filter by ATS type to probe",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of sources to probe",
    ),
    max_concurrency: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Maximum concurrent HTTP probe requests",
    ),
) -> SourceBatchProbeResponse:
    """Execute batch reachability probe across registered sources."""
    filter_dto = SourceFilterDTO(
        active_only=active_only,
        ats_type=ats_type,
        limit=limit,
    )
    result = await service.probe_sources_batch(
        filter_=filter_dto,
        max_concurrency=max_concurrency,
    )
    return SourceBatchProbeResponse.model_validate(result)


@router.get(
    "/stats",
    response_model=SourceStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get operational source statistics",
    description=(
        "Returns aggregated metrics across registered job sources including "
        "total, active, and inactive counts, plus breakdowns by ATS type and country."
    ),
)
async def get_source_statistics(
    service: SourceRegistryDep,
) -> SourceStatsResponse:
    """Retrieve aggregated operational source metrics."""
    stats = await service.get_source_statistics()
    return SourceStatsResponse.model_validate(stats)


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get source details by ID",
    description="Retrieve full details for an individual registered source.",
)
async def get_source(
    service: SourceRegistryDep,
    source_id: uuid.UUID = Path(description="Unique ID of the source"),
) -> SourceResponse:
    """Retrieve an individual source entity."""
    source = await service.get_source(source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found",
        )
    return SourceResponse.model_validate(source)


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update source operational configuration",
    description=(
        "Partially update source operational configuration (name, adapter_config, "
        "pagination_config, endpoint_config, rate_limit_config, metadata). "
        "Does NOT update active status (use /status endpoint)."
    ),
)
async def update_source(
    service: SourceRegistryDep,
    payload: SourceUpdateRequest,
    source_id: uuid.UUID = Path(description="Unique ID of the source to update"),
) -> SourceResponse:
    """Update source operational configuration."""
    dto = SourceUpdateDTO(
        name=payload.name,
        adapter_config=payload.adapter_config,
        pagination_config=payload.pagination_config,
        endpoint_config=payload.endpoint_config,
        rate_limit_config=payload.rate_limit_config,
        metadata=payload.metadata,
    )
    updated = await service.update_source(source_id, dto)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found",
        )
    return SourceResponse.model_validate(updated)


@router.patch(
    "/{source_id}/status",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update source active status",
    description=(
        "Explicitly activate or deactivate a registered source. "
        "Sole endpoint permitted to mutate Source.active."
    ),
)
async def set_source_status(
    service: SourceRegistryDep,
    payload: SourceStatusUpdateRequest,
    source_id: uuid.UUID = Path(description="Unique ID of the source to update status"),
) -> SourceResponse:
    """Update source active discovery status."""
    updated = await service.set_source_status(source_id, payload.active)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found",
        )
    return SourceResponse.model_validate(updated)


@router.post(
    "/{source_id}/probe",
    response_model=SourceProbeResponse,
    status_code=status.HTTP_200_OK,
    summary="Probe an individual job source",
    description=(
        "Checks HTTP reachability, status code, and latency for a single "
        "registered source. Does not modify source active status."
    ),
)
async def probe_source(
    service: SourceRegistryDep,
    source_id: uuid.UUID = Path(description="Unique ID of the source to probe"),
) -> SourceProbeResponse:
    """Probe an individual source by ID."""
    result = await service.probe_source(source_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source with ID '{source_id}' not found",
        )
    return SourceProbeResponse.model_validate(result)
