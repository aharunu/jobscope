"""FastAPI dependencies for the application tracking subsystem."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.application_tracking.services import (
    ApplicationTrackingService,
)
from backend.domain.application.repositories import ApplicationRepository
from backend.infrastructure.database.repositories.application_repository import (
    SQLAlchemyApplicationRepository,
)
from backend.interfaces.api.dependencies.database import DbSession
from backend.interfaces.api.dependencies.job_processing import (
    JobRepositoryDep,
)


def get_application_repository(session: DbSession) -> ApplicationRepository:
    """Provide an ApplicationRepository instance bound to the request session."""
    return SQLAlchemyApplicationRepository(session)


ApplicationRepositoryDep = Annotated[
    ApplicationRepository, Depends(get_application_repository)
]


def get_application_tracking_service(
    app_repo: ApplicationRepositoryDep,
    job_repo: JobRepositoryDep,
) -> ApplicationTrackingService:
    """Provide a configured ApplicationTrackingService instance."""
    return ApplicationTrackingService(
        app_repo=app_repo,
        job_repo=job_repo,
    )


ApplicationTrackingServiceDep = Annotated[
    ApplicationTrackingService, Depends(get_application_tracking_service)
]
