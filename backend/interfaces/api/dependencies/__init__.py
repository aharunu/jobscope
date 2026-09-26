"""API dependencies package."""

from backend.interfaces.api.dependencies.crawler import (
    ATSAdapterRegistryDep,
    CrawlerOrchestratorDep,
    SafeHttpClientDep,
    get_adapter_registry,
    get_crawler_orchestrator,
    get_safe_http_client,
)
from backend.interfaces.api.dependencies.database import DbSession, get_db_session
from backend.interfaces.api.dependencies.job_processing import (
    CrawlRunRepositoryDep,
    JobIngestionServiceDep,
    JobNormalizerDep,
    JobRepositoryDep,
    RawJobRepositoryDep,
    get_crawl_run_repository,
    get_job_ingestion_service,
    get_job_normalizer,
    get_job_repository,
    get_raw_job_repository,
)
from backend.interfaces.api.dependencies.sources import (
    CatalogParserDep,
    SourceHealthProbeDep,
    SourceRegistryDep,
    get_catalog_parser,
    get_source_health_probe,
    get_source_registry_service,
    get_source_repository,
)

__all__ = [
    "ATSAdapterRegistryDep",
    "CatalogParserDep",
    "CrawlRunRepositoryDep",
    "CrawlerOrchestratorDep",
    "DbSession",
    "JobIngestionServiceDep",
    "JobNormalizerDep",
    "JobRepositoryDep",
    "RawJobRepositoryDep",
    "SafeHttpClientDep",
    "SourceHealthProbeDep",
    "SourceRegistryDep",
    "get_adapter_registry",
    "get_catalog_parser",
    "get_crawl_run_repository",
    "get_crawler_orchestrator",
    "get_db_session",
    "get_job_ingestion_service",
    "get_job_normalizer",
    "get_job_repository",
    "get_raw_job_repository",
    "get_safe_http_client",
    "get_source_health_probe",
    "get_source_registry_service",
    "get_source_repository",
]
