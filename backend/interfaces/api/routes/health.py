"""Health check endpoint router."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.application.system.health_service import HealthService
from backend.infrastructure.config.settings import Settings, get_settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response payload schema."""

    status: str
    app: str
    environment: str
    version: str


def get_health_service(
    settings: Settings = Depends(get_settings),
) -> HealthService:
    """Provide a HealthService instance populated from application settings."""
    return HealthService(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/health", response_model=HealthResponse, summary="Perform health check")
async def health_check(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Return the operational health status of the service."""
    status = service.get_health_status()
    return HealthResponse(**status)
