"""API dependencies package."""

from backend.interfaces.api.dependencies.database import DbSession, get_db_session
from backend.interfaces.api.dependencies.sources import (
    CatalogParserDep,
    SourceRegistryDep,
    get_catalog_parser,
    get_source_registry_service,
    get_source_repository,
)

__all__ = [
    "CatalogParserDep",
    "DbSession",
    "SourceRegistryDep",
    "get_catalog_parser",
    "get_db_session",
    "get_source_registry_service",
    "get_source_repository",
]
