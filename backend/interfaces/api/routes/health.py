"""Health and readiness check endpoint router."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from backend.application.system.health_service import HealthService
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.health import check_database_health

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Liveness health check response payload schema."""

    status: str
    app: str
    environment: str
    version: str


class ReadinessResponse(BaseModel):
    """Database readiness probe response payload schema."""

    status: str
    database: str


def get_health_service(
    settings: Settings = Depends(get_settings),
) -> HealthService:
    """Provide a HealthService instance populated from application settings."""
    return HealthService(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
    )


def get_db_health_checker() -> Callable[[], Awaitable[dict[str, Any]]]:
    """Provide the database health check callable for dependency injection."""
    return check_database_health


@router.get("/health", response_model=HealthResponse, summary="Perform health check")
async def health_check(
    service: HealthService = Depends(get_health_service),
) -> HealthResponse:
    """Return the operational process liveness status of the service."""
    status_data = service.get_health_status()
    return HealthResponse(**status_data)


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Perform database readiness check",
    responses={
        status.HTTP_200_OK: {
            "description": "Database is connected and ready.",
            "model": ReadinessResponse,
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "Database is disconnected or unreachable.",
            "model": ReadinessResponse,
        },
    },
)
async def database_readiness_check(
    response: Response,
    service: HealthService = Depends(get_health_service),
    checker: Callable[[], Awaitable[dict[str, Any]]] = Depends(get_db_health_checker),
) -> ReadinessResponse:
    """Return the database operational readiness status."""
    is_ready, data = await service.get_database_readiness(checker)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(**data)
