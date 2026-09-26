"""Job discovery application package."""

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    CrawlExecutionResultDTO,
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
    SourceBatchProbeResultDTO,
    SourceCreateDTO,
    SourceFilterDTO,
    SourceProbeResultDTO,
    SourceStatsDTO,
    SourceUpdateDTO,
    SyncResultDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    AdapterUnavailableError,
    CrawlerError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
    UnsupportedATSError,
)
from backend.application.job_discovery.ports import (
    ATSAdapter,
    CatalogParser,
    CrawlPersistenceManager,
    RuntimeSourceProvider,
    SafeHttpClient,
    SourceHealthProbe,
)
from backend.application.job_discovery.services import SourceRegistryService

__all__ = [
    "ATSAdapter",
    "ATSAdapterRegistry",
    "AdapterExecutionError",
    "AdapterUnavailableError",
    "CatalogParser",
    "CrawlExecutionResultDTO",
    "CrawlPersistenceManager",
    "CrawlResultDTO",
    "CrawlerError",
    "CrawlerOrchestrator",
    "DiscoveredJobDTO",
    "InvalidSourceConfigurationError",
    "MalformedAdapterResultError",
    "RuntimeSourceDTO",
    "RuntimeSourceProvider",
    "SafeHttpClient",
    "SafeHttpResponseDTO",
    "SourceBatchProbeResultDTO",
    "SourceCreateDTO",
    "SourceFilterDTO",
    "SourceHealthProbe",
    "SourceProbeResultDTO",
    "SourceRegistryService",
    "SourceStatsDTO",
    "SourceUpdateDTO",
    "SyncResultDTO",
    "UnsupportedATSError",
]
