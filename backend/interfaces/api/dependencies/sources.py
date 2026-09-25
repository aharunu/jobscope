"""FastAPI dependencies for the Source Registry."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.job_discovery.ports import (
    CatalogParser,
    SourceHealthProbe,
)
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source.repositories import SourceRepository
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)
from backend.infrastructure.http.source_probe import HttpSourceHealthProbe
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
)
from backend.interfaces.api.dependencies.database import DbSession


def get_source_repository(session: DbSession) -> SourceRepository:
    """Yield a SQLAlchemySourceRepository bound to the current database session."""
    return SQLAlchemySourceRepository(session)


def get_catalog_parser() -> CatalogParser:
    """Provide a MarkdownSourceParser instance implementing the CatalogParser port."""
    return MarkdownSourceParser()


CatalogParserDep = Annotated[CatalogParser, Depends(get_catalog_parser)]


def get_source_health_probe() -> SourceHealthProbe:
    """Provide an HttpSourceHealthProbe instance implementing SourceHealthProbe port."""
    settings = get_settings()
    return HttpSourceHealthProbe(
        timeout_seconds=settings.source_probe_timeout_seconds,
        user_agent=settings.source_probe_user_agent,
    )


SourceHealthProbeDep = Annotated[SourceHealthProbe, Depends(get_source_health_probe)]


def get_source_registry_service(
    repository: Annotated[SourceRepository, Depends(get_source_repository)],
    catalog_parser: CatalogParserDep,
    health_probe: SourceHealthProbeDep,
) -> SourceRegistryService:
    """Yield a SourceRegistryService injected with dependencies."""
    settings = get_settings()

    return SourceRegistryService(
        repository=repository,
        catalog_parser=catalog_parser,
        health_probe=health_probe,
        default_catalog_path=settings.source_catalog_path,
    )


SourceRegistryDep = Annotated[
    SourceRegistryService, Depends(get_source_registry_service)
]

__all__ = [
    "CatalogParserDep",
    "SourceHealthProbeDep",
    "SourceRegistryDep",
    "get_catalog_parser",
    "get_source_health_probe",
    "get_source_registry_service",
    "get_source_repository",
]
