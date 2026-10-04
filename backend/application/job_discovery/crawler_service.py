"""Crawler orchestration application service."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Callable
from contextlib import nullcontext

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.dtos import (
    CrawlExecutionResultDTO,
    CrawlResultDTO,
    RuntimeSourceDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    AdapterUnavailableError,
    CrawlerError,
    SourceBusyError,
    UnsupportedATSError,
)
from backend.application.job_discovery.ports import (
    ATSAdapter,
    CrawlAdmissionGuard,
    CrawlPersistenceManager,
    RuntimeSourceProvider,
)
from backend.domain.crawl.enums import CrawlStatus

logger = logging.getLogger(__name__)


class CrawlerOrchestrator:
    """Application service coordinating job discovery and ingestion workflows.

    Coordinates:
    - Transaction A: CrawlRun initialization (RUNNING) committed to DB.
    - Network Discovery: no ORM transaction; dedicated admission connection only.
    - Transaction B: Ingestion, deduplication, and CrawlRun finalization.
    - Failure Transaction: Marks CrawlRun FAILED upon network/adapter error.
    """

    def __init__(
        self,
        source_provider: RuntimeSourceProvider,
        adapter_registry: ATSAdapterRegistry,
        persistence_manager: CrawlPersistenceManager | None = None,
        admission_guard: CrawlAdmissionGuard | None = None,
        budget_factory: Callable[[], AcquisitionBudget] = AcquisitionBudget,
    ) -> None:
        self._source_provider = source_provider
        self._adapter_registry = adapter_registry
        self._persistence_manager = persistence_manager
        self._admission_guard = admission_guard
        self._budget_factory = budget_factory

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

        try:
            guard = (
                self._admission_guard.hold(source_id)
                if self._admission_guard
                else nullcontext()
            )
            async with guard:
                return await self._crawl_resolved_source(source)
        except SourceBusyError as err:
            return CrawlExecutionResultDTO(
                source_id=source.id,
                source_name=source.name,
                ats_type=source.ats_type,
                status=CrawlStatus.FAILED,
                success=False,
                jobs_found=0,
                duration_ms=0,
                error_type=err.code,
                error_message=err.message,
                error_count=1,
            )

    async def _acquire(
        self, adapter: ATSAdapter, source: RuntimeSourceDTO
    ) -> CrawlResultDTO:
        budget = self._budget_factory()
        with acquisition_scope(budget):
            try:
                async with asyncio.timeout(budget.remaining_seconds()):
                    result = await adapter.crawl(source)
                    budget.remaining_seconds()
            except TimeoutError as exc:
                raise AdapterExecutionError(
                    message="Source acquisition budget exhausted: duration",
                    code="ACQUISITION_BUDGET_EXHAUSTED",
                ) from exc
            result.metadata["acquisition_budget"] = {
                "requests": budget.requests,
                "bytes": budget.bytes_read,
            }
            if not result.is_complete and not result.warnings:
                result.warnings.append("acquisition_incomplete")
            return result

    async def _crawl_resolved_source(
        self, source: RuntimeSourceDTO
    ) -> CrawlExecutionResultDTO:
        start_time = time.perf_counter()

        # Transaction A: Create persistent CrawlRun with RUNNING status
        crawl_run_id: uuid.UUID | None = None
        if self._persistence_manager is not None:
            try:
                crawl_run_id = await self._persistence_manager.create_initial_run(
                    source.id
                )
            except Exception:
                duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.error(
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
                    error_message="Crawl execution failed; see safe server diagnostics",
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
            crawl_result = await self._acquire(adapter, source)
        except asyncio.CancelledError:
            if self._persistence_manager is not None and crawl_run_id is not None:
                await self._persistence_manager.mark_run_failed(
                    crawl_run_id, error_count=1, error_message="Acquisition cancelled"
                )
            raise
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
                    crawl_run_id,
                    error_count=1,
                    error_message="Crawl execution failed; see safe server diagnostics",
                )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "crawl_failed crawl_run_id=%s source_id=%s "
                "error_type=UNEXPECTED_EXECUTION_ERROR error_message=%s "
                "duration_ms=%.1f",
                crawl_run_id,
                source.id,
                type(exc).__name__,
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
                error_message="Crawl execution failed; see safe server diagnostics",
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
                    jobs_closed=ingest_res.jobs_closed,
                    error_count=ingest_res.error_count,
                )
            except asyncio.CancelledError:
                if crawl_run_id is not None:
                    await self._persistence_manager.mark_run_failed(
                        crawl_run_id, error_count=1, error_message="Ingestion cancelled"
                    )
                raise
            except Exception as exc:
                if crawl_run_id is not None:
                    await self._persistence_manager.mark_run_failed(
                        crawl_run_id,
                        error_count=1,
                        error_message="Crawl execution failed",
                    )
                total_duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                logger.error(
                    "crawl_failed crawl_run_id=%s source_id=%s "
                    "error_type=INGESTION_FAILURE error_message=%s duration_ms=%.1f",
                    crawl_run_id,
                    source.id,
                    type(exc).__name__,
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
                    error_message="Crawl execution failed; see safe server diagnostics",
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
            status=CrawlStatus.PARTIAL
            if crawl_result.warnings
            else CrawlStatus.COMPLETED,
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
