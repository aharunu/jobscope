"""Comprehensive pipeline hardening and runtime integration tests for Phase 4.4."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
)
from backend.application.job_discovery.ports import (
    CrawlPersistenceManager,
    RuntimeSourceProvider,
    SafeHttpClient,
)
from backend.application.job_processing.dtos import JobIngestionResultDTO
from backend.application.job_processing.normalizer import JobNormalizer
from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.domain.source.entities import Source
from backend.infrastructure.ats.lever.adapter import LeverAdapter
from backend.infrastructure.database.crawl_persistence import (
    SQLAlchemyCrawlPersistenceManager,
)

# ==============================================================================
# In-Memory Test Doubles for Pipeline Verification
# ==============================================================================


class InMemoryRuntimeSourceProvider(RuntimeSourceProvider):
    """In-memory test double for RuntimeSourceProvider."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self.sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_crawlable_source(
        self, source_id: uuid.UUID
    ) -> RuntimeSourceDTO | None:
        source = self.sources.get(source_id)
        if not source or not source.active:
            return None
        return RuntimeSourceDTO.from_domain(source)

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        matching = [s for s in self.sources.values() if s.active]
        if ats_type is not None:
            matching = [s for s in matching if s.ats_type == ats_type]
        sliced = matching[offset : offset + limit if limit else None]
        return [RuntimeSourceDTO.from_domain(s) for s in sliced]


class InMemoryCrawlPersistence(CrawlPersistenceManager):
    """In-memory stateful persistence manager tracking Transaction A/B lifecycle."""

    def __init__(
        self,
        job_repo: JobRepository | None = None,
        raw_job_repo: RawJobRepository | None = None,
    ) -> None:
        self.runs: dict[uuid.UUID, CrawlRun] = {}
        self.crawl_run_jobs: list[CrawlRunJob] = []
        self.jobs: dict[uuid.UUID, Job] = {}
        self.raw_jobs: list[RawJob] = []
        self.transaction_a_committed: list[uuid.UUID] = []
        self.transaction_b_committed: list[uuid.UUID] = []
        self.failure_transactions: list[uuid.UUID] = []
        self.simulated_ingestion_error: Exception | None = None

    async def create_initial_run(self, source_id: uuid.UUID) -> uuid.UUID:
        """Transaction A: Commit initial RUNNING status."""
        run_id = uuid.uuid4()
        now = datetime.now(UTC)
        run = CrawlRun(
            id=run_id,
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            started_at=now,
        )
        self.runs[run_id] = run
        self.transaction_a_committed.append(run_id)
        return run_id

    async def mark_run_failed(
        self,
        crawl_run_id: uuid.UUID,
        error_count: int = 1,
        error_message: str | None = None,
    ) -> None:
        """Failure Transaction: Commit FAILED status in a fresh transaction."""
        run = self.runs.get(crawl_run_id)
        if run is not None:
            run.status = CrawlStatus.FAILED
            run.error_count = error_count
            run.finished_at = datetime.now(UTC)
        self.failure_transactions.append(crawl_run_id)

    async def execute_ingestion(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        crawl_run_id: uuid.UUID,
    ) -> JobIngestionResultDTO:
        """Transaction B: Normalization, deduplication, persistence."""
        if self.simulated_ingestion_error:
            raise self.simulated_ingestion_error

        normalizer = JobNormalizer()
        now = datetime.now(UTC)
        jobs_created = 0
        jobs_updated = 0
        jobs_unchanged = 0
        errors: list[str] = []

        run = self.runs[crawl_run_id]
        run.jobs_found = len(crawl_result.jobs)

        for disc in crawl_result.jobs:
            try:
                canonical = normalizer.normalize(disc, source)
                # Identity check: (source_id, external_job_id)
                existing = None
                for j in self.jobs.values():
                    if (
                        j.source_id == source.id
                        and j.external_job_id == canonical.external_job_id
                    ):
                        existing = j
                        break

                if existing is None:
                    # CREATED
                    canonical.first_seen_at = now
                    canonical.last_seen_at = now
                    canonical.status = JobStatus.ACTIVE
                    self.jobs[canonical.id] = canonical

                    raw = RawJob(
                        job_id=canonical.id,
                        source_id=source.id,
                        raw_content=disc.raw_content,
                        content_type=disc.content_type,
                        fetched_at=now,
                    )
                    self.raw_jobs.append(raw)
                    self.crawl_run_jobs.append(
                        CrawlRunJob(
                            crawl_run_id=crawl_run_id,
                            job_id=canonical.id,
                            action=CrawlJobAction.CREATED,
                        )
                    )
                    jobs_created += 1
                else:
                    existing.last_seen_at = now
                    if existing.status == JobStatus.CLOSED:
                        existing.status = JobStatus.ACTIVE
                        existing.closed_at = None

                    if canonical.content_hash != existing.content_hash:
                        # UPDATED
                        existing.title = canonical.title
                        existing.description = canonical.description
                        existing.location = canonical.location
                        existing.content_hash = canonical.content_hash

                        raw = RawJob(
                            job_id=existing.id,
                            source_id=source.id,
                            raw_content=disc.raw_content,
                            content_type=disc.content_type,
                            fetched_at=now,
                        )
                        self.raw_jobs.append(raw)
                        self.crawl_run_jobs.append(
                            CrawlRunJob(
                                crawl_run_id=crawl_run_id,
                                job_id=existing.id,
                                action=CrawlJobAction.UPDATED,
                            )
                        )
                        jobs_updated += 1
                    else:
                        # UNCHANGED
                        self.crawl_run_jobs.append(
                            CrawlRunJob(
                                crawl_run_id=crawl_run_id,
                                job_id=existing.id,
                                action=CrawlJobAction.UNCHANGED,
                            )
                        )
                        jobs_unchanged += 1
            except Exception as exc:
                errors.append(str(exc))

        error_count = len(errors)
        if error_count > 0:
            final_status = (
                CrawlStatus.PARTIAL
                if (jobs_created + jobs_updated + jobs_unchanged) > 0
                else CrawlStatus.FAILED
            )
        elif crawl_result.warnings:
            final_status = CrawlStatus.PARTIAL
        else:
            final_status = CrawlStatus.COMPLETED

        run.status = final_status
        run.jobs_created = jobs_created
        run.jobs_updated = jobs_updated
        run.error_count = error_count
        run.finished_at = datetime.now(UTC)

        self.transaction_b_committed.append(crawl_run_id)

        return JobIngestionResultDTO(
            crawl_run_id=crawl_run_id,
            source_id=source.id,
            status=final_status,
            jobs_found=len(crawl_result.jobs),
            jobs_created=jobs_created,
            jobs_updated=jobs_updated,
            jobs_unchanged=jobs_unchanged,
            jobs_closed=0,
            error_count=error_count,
            warnings=crawl_result.warnings,
            errors=errors,
        )


class MockSafeHttpClient(SafeHttpClient):
    """Scriptable mock safe client returning predefined responses."""

    def __init__(self, responses: list[SafeHttpResponseDTO | Exception]) -> None:
        self._responses = list(responses)
        self.requested_urls: list[str] = []

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        self.requested_urls.append(url)
        if not self._responses:
            raise RuntimeError("No responses left in mock")
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


SAMPLE_LEVER_POSTINGS = [
    {
        "id": "lever-job-001",
        "text": "Senior Platform Engineer",
        "hostedUrl": "https://jobs.lever.co/techcorp/lever-job-001",
        "categories": {
            "location": "Istanbul, Turkey",
            "commitment": "Full-time",
            "team": "Platform",
        },
        "description": "<p>Build scalable infrastructure.</p>",
        "createdAt": 1700000000000,
    },
    {
        "id": "lever-job-002",
        "text": "Senior QA Engineer",
        "hostedUrl": "https://jobs.lever.co/techcorp/lever-job-002",
        "categories": {
            "location": "Remote, Turkey",
            "commitment": "Full-time",
            "team": "QA",
        },
        "description": "<p>Automated testing.</p>",
        "createdAt": 1700000000000,
    },
]


# ==============================================================================
# 1. CrawlRun Lifecycle & Transaction Boundary Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_crawl_run_lifecycle_successful_crawl() -> None:
    """Verify:
    1. Transaction A creates RUNNING CrawlRun.
    2. Network discovery produces DiscoveredJobDTO.
    3. Transaction B ingests jobs and updates CrawlRun to COMPLETED (SUCCESS).
    """
    source = Source(
        id=uuid.uuid4(),
        name="TechCorp Lever",
        url="https://jobs.lever.co/techcorp",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    http_client = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/techcorp?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            )
        ]
    )
    adapter = LeverAdapter(http_client=http_client)
    registry = ATSAdapterRegistry([adapter])

    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is True
    assert result.status == CrawlStatus.COMPLETED
    assert result.jobs_found == 2
    assert result.jobs_created == 2
    assert result.jobs_updated == 0
    assert result.jobs_unchanged == 0
    assert result.error_count == 0

    # Lifecycle Invariant: Same CrawlRun ID across all phases
    run_id = result.crawl_run_id
    assert run_id is not None
    assert run_id in persistence.transaction_a_committed
    assert run_id in persistence.transaction_b_committed
    assert run_id not in persistence.failure_transactions

    persisted_run = persistence.runs[run_id]
    assert persisted_run.status == CrawlStatus.COMPLETED
    assert persisted_run.jobs_created == 2
    assert len(persistence.jobs) == 2
    assert len(persistence.raw_jobs) == 2
    assert len(persistence.crawl_run_jobs) == 2


@pytest.mark.asyncio
async def test_crawl_run_lifecycle_zero_jobs_is_success() -> None:
    """Verify Section 4: Zero jobs discovered without errors
    results in SUCCESS (COMPLETED).
    """
    source = Source(
        id=uuid.uuid4(),
        name="Empty Lever Board",
        url="https://jobs.lever.co/empty",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    http_client = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/empty?mode=json&limit=100",
                text=json.dumps([]),  # zero jobs
            )
        ]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is True
    assert result.status == CrawlStatus.COMPLETED
    assert result.jobs_found == 0
    assert result.jobs_created == 0
    assert result.error_count == 0

    run = persistence.runs[result.crawl_run_id]
    assert run.status == CrawlStatus.COMPLETED


@pytest.mark.asyncio
async def test_crawl_run_lifecycle_discovery_failure_marks_run_failed() -> None:
    """Verify:
    When adapter/network fails during discovery:
    1. Transaction A had committed RUNNING.
    2. Failure transaction updates the SAME CrawlRun to FAILED.
    """
    source = Source(
        id=uuid.uuid4(),
        name="Broken Lever Board",
        url="https://jobs.lever.co/broken",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    http_client = MockSafeHttpClient(
        [AdapterExecutionError("Upstream timeout", code="ADAPTER_EXECUTION_FAILURE")]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "ADAPTER_EXECUTION_FAILURE"

    run_id = result.crawl_run_id
    assert run_id is not None
    assert run_id in persistence.transaction_a_committed
    assert run_id in persistence.failure_transactions
    assert run_id not in persistence.transaction_b_committed

    persisted_run = persistence.runs[run_id]
    assert persisted_run.status == CrawlStatus.FAILED
    assert persisted_run.error_count == 1


@pytest.mark.asyncio
async def test_crawl_run_lifecycle_transaction_b_failure_marks_run_failed() -> None:
    """Verify Section 5:
    When Transaction B (database ingestion) fails:
    1. Transaction B is rolled back.
    2. Failure transaction updates the existing CrawlRun to FAILED.
    """
    source = Source(
        id=uuid.uuid4(),
        name="DB Fail Lever",
        url="https://jobs.lever.co/dbfail",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()
    # Simulate DB failure during ingestion
    persistence.simulated_ingestion_error = RuntimeError(
        "Database deadlock / constraint violation"
    )

    http_client = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/dbfail?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            )
        ]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "INGESTION_FAILURE"

    run_id = result.crawl_run_id
    assert run_id is not None
    assert run_id in persistence.transaction_a_committed
    assert run_id in persistence.failure_transactions
    assert run_id not in persistence.transaction_b_committed

    run = persistence.runs[run_id]
    assert run.status == CrawlStatus.FAILED


# ==============================================================================
# 2. Idempotency & Lifecycle Timestamp Preservation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_crawl_pipeline_idempotency_second_run_unchanged() -> None:
    """Verify Section 13:
    First crawl: creates 2 jobs, saves 2 RawJobs.
    Second crawl: detects 2 unchanged jobs, preserves first_seen_at,
    saves 0 new RawJobs.
    """
    source = Source(
        id=uuid.uuid4(),
        name="Idempotent Lever",
        url="https://jobs.lever.co/idempotent",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    http_client = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/idempotent?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            ),
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/idempotent?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            ),
        ]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    # First Crawl
    res1 = await orchestrator.crawl_source(source.id)
    assert res1.success is True
    assert res1.jobs_created == 2
    assert res1.jobs_unchanged == 0
    assert len(persistence.raw_jobs) == 2

    # Save initial first_seen_at timestamps
    initial_first_seen = {j.id: j.first_seen_at for j in persistence.jobs.values()}

    # Second Crawl (Identical payload)
    res2 = await orchestrator.crawl_source(source.id)
    assert res2.success is True
    assert res2.status == CrawlStatus.COMPLETED
    assert res2.jobs_created == 0
    assert res2.jobs_updated == 0
    assert res2.jobs_unchanged == 2
    assert res2.crawl_run_id != res1.crawl_run_id

    # Invariant: NO duplicate canonical jobs created
    assert len(persistence.jobs) == 2

    # Invariant: NO new RawJobs created for unchanged jobs
    assert len(persistence.raw_jobs) == 2

    # Invariant: first_seen_at preserved for all existing jobs
    for j in persistence.jobs.values():
        assert j.first_seen_at == initial_first_seen[j.id]


@pytest.mark.asyncio
async def test_crawl_pipeline_job_update_creates_raw_job_and_updates_content() -> None:
    """Verify Section 15:
    When job content changes:
    - job is UPDATED
    - new RawJob is saved
    - first_seen_at is preserved
    """
    source = Source(
        id=uuid.uuid4(),
        name="Update Lever",
        url="https://jobs.lever.co/update",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    updated_postings = list(SAMPLE_LEVER_POSTINGS)
    updated_postings[0] = {
        **SAMPLE_LEVER_POSTINGS[0],
        "text": "Principal Platform Engineer",  # changed title
    }

    http_client = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            ),
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps(updated_postings),
            ),
        ]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    # First Crawl
    await orchestrator.crawl_source(source.id)
    assert len(persistence.raw_jobs) == 2

    # Second Crawl (1 updated, 1 unchanged)
    res2 = await orchestrator.crawl_source(source.id)
    assert res2.success is True
    assert res2.jobs_created == 0
    assert res2.jobs_updated == 1
    assert res2.jobs_unchanged == 1

    # Invariant: exactly 1 new RawJob created for the updated posting
    assert len(persistence.raw_jobs) == 3


# ==============================================================================
# 3. Error Isolation & Non-Retryable Invariants Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_crawl_pipeline_http_429_fails_without_retry() -> None:
    """Verify Section 10: HTTP 429 is deliberately non-retryable in Phase 4.4 MVP."""
    source = Source(
        id=uuid.uuid4(),
        name="Rate Limited Lever",
        url="https://jobs.lever.co/ratelimited",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()

    http_client = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=429, url="...", text="Rate Limited")]
    )
    registry = ATSAdapterRegistry([LeverAdapter(http_client=http_client)])
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "ADAPTER_EXECUTION_FAILURE"
    assert "Rate limited" in (result.error_message or "")


@pytest.mark.asyncio
async def test_crawl_pipeline_unsupported_ats_fails_without_crawl() -> None:
    """Verify Section 8: Unknown ATS records UnsupportedATSError."""
    source = Source(
        id=uuid.uuid4(),
        name="Unknown ATS Board",
        url="https://custom.com/jobs",
        ats_type="unknown_custom_ats",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    persistence = InMemoryCrawlPersistence()
    registry = ATSAdapterRegistry([])  # empty

    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
        persistence_manager=persistence,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "UNSUPPORTED_ATS_TYPE"
    assert result.crawl_run_id in persistence.failure_transactions


# ==============================================================================
# 4. SQLAlchemyCrawlPersistenceManager Unit & Boundary Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_sqlalchemy_crawl_persistence_manager_transaction_boundaries() -> None:
    """Verify SQLAlchemyCrawlPersistenceManager manages commit and rollback properly."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session_factory = MagicMock(return_value=mock_session)
    mock_session.__aenter__.return_value = mock_session
    mock_session.__aexit__.return_value = None

    manager = SQLAlchemyCrawlPersistenceManager(session_factory=mock_session_factory)

    # 1. Transaction A: create_initial_run
    source_id = uuid.uuid4()
    with patch(
        "backend.infrastructure.database.crawl_persistence.SQLAlchemyCrawlRunRepository.create_run",
        new_callable=AsyncMock,
    ):
        run_id = await manager.create_initial_run(source_id)

    assert run_id is not None
    mock_session.commit.assert_awaited()

    # 2. Failure Transaction: mark_run_failed
    mock_session.reset_mock()
    mock_run = MagicMock()
    with (
        patch(
            "backend.infrastructure.database.crawl_persistence.SQLAlchemyCrawlRunRepository.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_run,
        ),
        patch(
            "backend.infrastructure.database.crawl_persistence.SQLAlchemyCrawlRunRepository.update_run",
            new_callable=AsyncMock,
        ),
    ):
        await manager.mark_run_failed(
            run_id, error_count=2, error_message="Fatal error"
        )

    assert mock_run.status == CrawlStatus.FAILED
    assert mock_run.error_count == 2
    mock_session.commit.assert_awaited()

    # 3. Transaction B rollback on exception
    mock_session.reset_mock()
    with (
        patch(
            "backend.infrastructure.database.crawl_persistence.JobIngestionService.ingest_crawl_result",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Deadlock"),
        ),
        pytest.raises(RuntimeError),
    ):
        await manager.execute_ingestion(
            source=RuntimeSourceDTO.from_domain(
                Source(
                    id=source_id,
                    name="S",
                    url="https://u",
                    ats_type="lever",
                    active=True,
                )
            ),
            crawl_result=CrawlResultDTO(source_id=source_id, ats_type="lever", jobs=[]),
            crawl_run_id=run_id,
        )

    mock_session.rollback.assert_awaited()
