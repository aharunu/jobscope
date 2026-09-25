"""FastAPI dependencies for the Source Registry."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.job_discovery.ports import CatalogParser
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source.repositories import SourceRepository
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)
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


def get_source_registry_service(
    repository: Annotated[SourceRepository, Depends(get_source_repository)],
    catalog_parser: CatalogParserDep,
) -> SourceRegistryService:
    """Yield a SourceRegistryService injected with dependencies."""
    settings = get_settings()

    return SourceRegistryService(
        repository=repository,
        catalog_parser=catalog_parser,
        default_catalog_path=settings.source_catalog_path,
    )


SourceRegistryDep = Annotated[
    SourceRegistryService, Depends(get_source_registry_service)
]

__all__ = [
    "CatalogParserDep",
    "SourceRegistryDep",
    "get_catalog_parser",
    "get_source_registry_service",
    "get_source_repository",
]
