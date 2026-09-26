"""Crawler orchestration application service."""

from __future__ import annotations

import logging
import time
import uuid

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.dtos import (
    CrawlExecutionResultDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterUnavailableError,
    CrawlerError,
    UnsupportedATSError,
)
from backend.application.job_discovery.ports import RuntimeSourceProvider
from backend.domain.crawl.enums import CrawlStatus

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Application service coordinating job discovery workflows across runtime sources.

    Coordinates source retrieval via RuntimeSourceProvider, adapter resolution
    via ATSAdapterRegistry, and sequential execution with error isolation.
    """

    def __init__(
        self,
        source_provider: RuntimeSourceProvider,
        adapter_registry: ATSAdapterRegistry,
    ) -> None:
        self._source_provider = source_provider
        self._adapter_registry = adapter_registry

    async def crawl_source(self, source_id: uuid.UUID) -> CrawlExecutionResultDTO:
        """Crawl an individual active source by its unique ID.

        Handles inactive or missing sources without throwing unhandled exceptions.
        """
        source = await self._source_provider.get_crawlable_source(source_id)
        if source is None:
            return CrawlExecutionResultDTO(
                source_id=source_id,
                source_name="Unknown",
                ats_type="unknown",
                status=CrawlStatus.FAILED,
                success=False,
                jobs_found=0,
                duration_ms=0.0,
                error_type="SOURCE_NOT_FOUND_OR_INACTIVE",
                error_message=(
                    f"Source '{source_id}' does not exist or is not active for "
                    "crawling."
                ),
            )

        start_time = time.perf_counter()

        # Resolve ATS adapter
        try:
            adapter = self._adapter_registry.get_adapter(source.ats_type)
        except (UnsupportedATSError, AdapterUnavailableError) as err:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "Adapter resolution failed for source '%s' (%s): %s",
                source.name,
                source.id,
                err.message,
            )
            return CrawlExecutionResultDTO(
                source_id=source.id,
                source_name=source.name,
                ats_type=source.ats_type,
                status=CrawlStatus.FAILED,
                success=False,
                jobs_found=0,
                duration_ms=duration_ms,
                error_type=err.code,
                error_message=err.message,
            )

        # Execute crawl with complete error isolation
        try:
            crawl_result = await adapter.crawl(source)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return CrawlExecutionResultDTO(
                source_id=source.id,
                source_name=source.name,
                ats_type=source.ats_type,
                status=CrawlStatus.COMPLETED,
                success=True,
                jobs_found=len(crawl_result.jobs),
                duration_ms=duration_ms,
                crawl_result=crawl_result,
            )
        except CrawlerError as err:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "Crawler error during execution for source '%s' (%s): %s",
                source.name,
                source.id,
                err.message,
            )
            return CrawlExecutionResultDTO(
                source_id=source.id,
                source_name=source.name,
                ats_type=source.ats_type,
                status=CrawlStatus.FAILED,
                success=False,
                jobs_found=0,
                duration_ms=duration_ms,
                error_type=err.code,
                error_message=err.message,
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Unexpected error during crawl execution for source '%s' (%s)",
                source.name,
                source.id,
            )
            return CrawlExecutionResultDTO(
                source_id=source.id,
                source_name=source.name,
                ats_type=source.ats_type,
                status=CrawlStatus.FAILED,
                success=False,
                jobs_found=0,
                duration_ms=duration_ms,
                error_type="UNEXPECTED_EXECUTION_ERROR",
                error_message=str(exc),
            )

    async def crawl_sources_by_ats_type(
        self,
        ats_type: str,
        limit: int | None = None,
    ) -> list[CrawlExecutionResultDTO]:
        """Crawl active sources for a given ATS platform sequentially."""
        sources = await self._source_provider.get_crawlable_sources(
            ats_type=ats_type,
            limit=limit,
        )
        results: list[CrawlExecutionResultDTO] = []
        for source in sources:
            result = await self.crawl_source(source.id)
            results.append(result)
        return results

    async def crawl_all_active_sources(
        self,
        limit: int | None = None,
    ) -> list[CrawlExecutionResultDTO]:
        """Crawl all active registered sources sequentially."""
        sources = await self._source_provider.get_crawlable_sources(limit=limit)
        results: list[CrawlExecutionResultDTO] = []
        for source in sources:
            result = await self.crawl_source(source.id)
            results.append(result)
        return results
