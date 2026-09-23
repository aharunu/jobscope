"""FastAPI routes for registered job discovery sources."""

from __future__ import annotations

from fastapi import APIRouter, Query, status

from backend.application.job_discovery.dtos import SourceFilterDTO
from backend.interfaces.api.dependencies.sources import SourceRegistryDep
from backend.interfaces.api.schemas.source import SourceListResponse, SourceResponse

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get(
    "",
    response_model=SourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List registered job discovery sources",
    description=(
        "Retrieve registered job sources with optional active status "
        "and ATS type filtering."
    ),
)
async def list_sources(
    service: SourceRegistryDep,
    active_only: bool = Query(
        default=False,
        description="Filter to retrieve only active sources",
    ),
    ats_type: str | None = Query(
        default=None,
        description="Filter by ATS type (e.g. greenhouse, lever, workday, ashby)",
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
        ats_type=ats_type,
        limit=limit,
        offset=offset,
    )
    sources = await service.list_sources(filter_dto)
    total = await service.count_sources(
        active_only=active_only,
        ats_type=ats_type,
    )

    items = [SourceResponse.model_validate(s) for s in sources]
    return SourceListResponse(items=items, total=total)
