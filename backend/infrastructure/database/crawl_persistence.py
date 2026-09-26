"""SQLAlchemy implementation of the CrawlPersistenceManager port."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    RuntimeSourceDTO,
)
from backend.application.job_discovery.ports import CrawlPersistenceManager
from backend.application.job_processing.dtos import JobIngestionResultDTO
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlStatus
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)
from backend.infrastructure.database.session import get_session_factory

logger = logging.getLogger(__name__)


class SQLAlchemyCrawlPersistenceManager(CrawlPersistenceManager):
    """Coordinates transactional boundaries for CrawlRun and Job persistence.

    Enforces strict architectural boundaries:
    - Transaction A: Persists initial CrawlRun with RUNNING status and commits.
    - Transaction B: Atomic ingestion of canonical Jobs, RawJobs, CrawlRunJobs,
      and updates CrawlRun counters/status. Rolls back on error.
    - Failure Transaction: Independent fresh session to mark an existing CrawlRun
      as FAILED after discovery or ingestion failure.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()

    async def create_initial_run(self, source_id: uuid.UUID) -> uuid.UUID:
        """Transaction A: Persist initial CrawlRun with RUNNING status and commit."""
        crawl_run_id = uuid.uuid4()
        now = datetime.now(UTC)
        run = CrawlRun(
            id=crawl_run_id,
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            started_at=now,
        )
        async with self._session_factory() as session:
            try:
                repo = SQLAlchemyCrawlRunRepository(session)
                await repo.create_run(run)
                await session.commit()
                return crawl_run_id
            except Exception:
                await session.rollback()
                raise

    async def mark_run_failed(
        self,
        crawl_run_id: uuid.UUID,
        error_count: int = 1,
        error_message: str | None = None,
    ) -> None:
        """Failure Transaction: Update existing CrawlRun to FAILED in fresh tx."""
        try:
            async with self._session_factory() as session:
                try:
                    repo = SQLAlchemyCrawlRunRepository(session)
                    run = await repo.get_by_id(crawl_run_id)
                    if run is not None:
                        run.status = CrawlStatus.FAILED
                        run.error_count = error_count
                        run.finished_at = datetime.now(UTC)
                        await repo.update_run(run)
                        await session.commit()
                except Exception:
                    await session.rollback()
                    raise
        except Exception as exc:
            logger.warning(
                "Failed to update CrawlRun '%s' to FAILED: %s", crawl_run_id, exc
            )

    async def execute_ingestion(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        crawl_run_id: uuid.UUID,
    ) -> JobIngestionResultDTO:
        """Transaction B: Ingest crawl result and finalize CrawlRun atomically."""
        async with self._session_factory() as session:
            try:
                job_repo = SQLAlchemyJobRepository(session)
                raw_job_repo = SQLAlchemyRawJobRepository(session)
                crawl_run_repo = SQLAlchemyCrawlRunRepository(session)
                ingestion_service = JobIngestionService(
                    job_repo=job_repo,
                    raw_job_repo=raw_job_repo,
                    crawl_run_repo=crawl_run_repo,
                    normalizer=JobNormalizer(),
                )
                result = await ingestion_service.ingest_crawl_result(
                    source=source,
                    crawl_result=crawl_result,
                    crawl_run_id=crawl_run_id,
                )
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
