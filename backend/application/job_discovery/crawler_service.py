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
from backend.application.job_discovery.ports import (
    CrawlPersistenceManager,
    RuntimeSourceProvider,
)
from backend.domain.crawl.enums import CrawlStatus

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Application service coordinating job discovery and ingestion workflows.

    Coordinates:
    - Transaction A: CrawlRun initialization (RUNNING) committed to DB.
    - Network Discovery: Remote HTTP crawling with zero DB connection held.
    - Transaction B: Ingestion, deduplication, and CrawlRun finalization.
    - Failure Transaction: Marks CrawlRun FAILED upon network/adapter error.
    """

    def __init__(
        self,
        source_provider: RuntimeSourceProvider,
        adapter_registry: ATSAdapterRegistry,
        persistence_manager: CrawlPersistenceManager | None = None,
    ) -> None:
        self._source_provider = source_provider
        self._adapter_registry = adapter_registry
        self._persistence_manager = persistence_manager

    async def crawl_source(self, source_id: uuid.UUID) -> CrawlExecutionResultDTO:
        """Crawl an individual active source end-to-end.

        Coordinates Transaction A -> Network Discovery -> Transaction B.
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
                    f"Source '{source_id}' does not exist "
                    "or is not active for crawling."
                ),
            )

        start_time = time.perf_counter()

        # Transaction A: Create persistent CrawlRun with RUNNING status
        crawl_run_id: uuid.UUID | None = None
        if self._persistence_manager is not None:
            try:
                crawl_run_id = await self._persistence_manager.create_initial_run(
                    source.id
                )
            except Exception as exc:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.exception(
                    "Failed to create initial CrawlRun record for source '%s'",
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
                    error_type="DATABASE_TRANSACTION_FAILURE",
                    error_message=str(exc),
                )
        else:
            crawl_run_id = uuid.uuid4()

        logger.info(
            "crawl_started crawl_run_id=%s source_id=%s source_name=%s ats_type=%s",
            crawl_run_id,
            source.id,
            source.name,
            source.ats_type,
        )

        # 1. Resolve ATS adapter
        try:
            adapter = self._adapter_registry.get_adapter(source.ats_type)
        except (UnsupportedATSError, AdapterUnavailableError) as err:
            if self._persistence_manager is not None and crawl_run_id is not None:
                await self._persistence_manager.mark_run_failed(
                    crawl_run_id, error_count=1, error_message=err.message
                )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "crawl_failed crawl_run_id=%s source_id=%s error_type=%s "
                "error_message=%s duration_ms=%.1f",
                crawl_run_id,
                source.id,
                err.code,
                err.message,
                duration_ms,
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
                crawl_run_id=crawl_run_id,
                error_count=1,
            )

        # 2. Network Discovery Phase (zero DB transaction held)
        logger.info(
            "crawl_discovery_started crawl_run_id=%s source_id=%s ats_type=%s",
            crawl_run_id,
            source.id,
            source.ats_type,
        )
        try:
            crawl_result = await adapter.crawl(source)
        except CrawlerError as err:
            if self._persistence_manager is not None and crawl_run_id is not None:
                await self._persistence_manager.mark_run_failed(
                    crawl_run_id, error_count=1, error_message=err.message
                )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "crawl_failed crawl_run_id=%s source_id=%s error_type=%s "
                "error_message=%s duration_ms=%.1f",
                crawl_run_id,
                source.id,
                err.code,
                err.message,
                duration_ms,
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
                crawl_run_id=crawl_run_id,
                error_count=1,
            )
        except Exception as exc:
            if self._persistence_manager is not None and crawl_run_id is not None:
                await self._persistence_manager.mark_run_failed(
                    crawl_run_id, error_count=1, error_message=str(exc)
                )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "crawl_failed crawl_run_id=%s source_id=%s "
                "error_type=UNEXPECTED_EXECUTION_ERROR error_message=%s "
                "duration_ms=%.1f",
                crawl_run_id,
                source.id,
                str(exc),
                duration_ms,
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
                crawl_run_id=crawl_run_id,
                error_count=1,
            )

        discovery_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "crawl_discovery_finished crawl_run_id=%s source_id=%s "
            "jobs_discovered=%d duration_ms=%.1f",
            crawl_run_id,
            source.id,
            len(crawl_result.jobs),
            discovery_duration_ms,
        )

        # 3. Transaction B: Ingestion & Status Finalization
        if self._persistence_manager is not None:
            try:
                ingest_res = await self._persistence_manager.execute_ingestion(
                    source=source,
                    crawl_result=crawl_result,
                    crawl_run_id=crawl_run_id,
                )
                total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.info(
                    "crawl_completed crawl_run_id=%s source_id=%s status=%s "
                    "jobs_discovered=%d jobs_created=%d jobs_updated=%d "
                    "jobs_unchanged=%d jobs_failed=%d duration_ms=%.1f",
                    crawl_run_id,
                    source.id,
                    ingest_res.status,
                    ingest_res.jobs_found,
                    ingest_res.jobs_created,
                    ingest_res.jobs_updated,
                    ingest_res.jobs_unchanged,
                    ingest_res.error_count,
                    total_duration_ms,
                )
                return CrawlExecutionResultDTO(
                    source_id=source.id,
                    source_name=source.name,
                    ats_type=source.ats_type,
                    status=ingest_res.status,
                    success=(ingest_res.status != CrawlStatus.FAILED),
                    jobs_found=ingest_res.jobs_found,
                    duration_ms=total_duration_ms,
                    crawl_result=crawl_result,
                    crawl_run_id=crawl_run_id,
                    jobs_created=ingest_res.jobs_created,
                    jobs_updated=ingest_res.jobs_updated,
                    jobs_unchanged=ingest_res.jobs_unchanged,
                    error_count=ingest_res.error_count,
                )
            except Exception as exc:
                if crawl_run_id is not None:
                    await self._persistence_manager.mark_run_failed(
                        crawl_run_id, error_count=1, error_message=str(exc)
                    )
                total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.exception(
                    "crawl_failed crawl_run_id=%s source_id=%s "
                    "error_type=INGESTION_FAILURE error_message=%s duration_ms=%.1f",
                    crawl_run_id,
                    source.id,
                    str(exc),
                    total_duration_ms,
                )
                return CrawlExecutionResultDTO(
                    source_id=source.id,
                    source_name=source.name,
                    ats_type=source.ats_type,
                    status=CrawlStatus.FAILED,
                    success=False,
                    jobs_found=len(crawl_result.jobs),
                    duration_ms=total_duration_ms,
                    error_type="INGESTION_FAILURE",
                    error_message=str(exc),
                    crawl_result=crawl_result,
                    crawl_run_id=crawl_run_id,
                    error_count=1,
                )

        # Fallback when no persistence manager provided (pure unit testing)
        total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return CrawlExecutionResultDTO(
            source_id=source.id,
            source_name=source.name,
            ats_type=source.ats_type,
            status=CrawlStatus.COMPLETED,
            success=True,
            jobs_found=len(crawl_result.jobs),
            duration_ms=total_duration_ms,
            crawl_result=crawl_result,
            crawl_run_id=crawl_run_id,
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
