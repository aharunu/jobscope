"""FastAPI dependencies for the Source Registry."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source.repositories import SourceRepository
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)
from backend.interfaces.api.dependencies.database import DbSession


def get_source_repository(session: DbSession) -> SourceRepository:
    """Yield a SQLAlchemySourceRepository bound to the current database session."""
    return SQLAlchemySourceRepository(session)


def get_source_registry_service(
    repository: Annotated[SourceRepository, Depends(get_source_repository)],
) -> SourceRegistryService:
    """Yield a SourceRegistryService injected with the SourceRepository."""
    return SourceRegistryService(repository)


SourceRegistryDep = Annotated[
    SourceRegistryService, Depends(get_source_registry_service)
]

__all__ = [
    "SourceRegistryDep",
    "get_source_registry_service",
    "get_source_repository",
]
