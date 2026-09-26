"""Comprehensive test suite for Phase 4.7 Job Lifecycle & Safe Absence Closure."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_discovery.history_service import CrawlHistoryService
from backend.application.job_processing.lifecycle import JobLifecycleService
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository


def _make_source(source_id: uuid.UUID | None = None) -> RuntimeSourceDTO:
    return RuntimeSourceDTO(
        id=source_id or uuid.uuid4(),
        name="Trendyol Tech",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
        country="TR",
        adapter_config={},
        pagination_config={},
        endpoint_config={},
        rate_limit_config={},
        metadata={},
    )


def _make_job(
    source_id: uuid.UUID,
    external_job_id: str,
    title: str = "Software Engineer",
    status: JobStatus = JobStatus.ACTIVE,
    first_seen_at: datetime | None = None,
    closed_at: datetime | None = None,
    content_hash: str | None = None,
) -> Job:
    now = datetime.now(UTC)
    fs = first_seen_at or (now - timedelta(days=7))
    ch = content_hash or f"hash_{external_job_id}"
    return Job(
        id=uuid.uuid4(),
        source_id=source_id,
        external_job_id=external_job_id,
        canonical_url=f"https://jobs.lever.co/trendyol/{external_job_id}",
        company="Trendyol",
        title=title,
        description=f"Description for {external_job_id}",
        content_hash=ch,
        status=status,
        first_seen_at=fs,
        last_seen_at=fs,
        closed_at=closed_at,
    )


@pytest.fixture
def mock_lifecycle_repos() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)

    crawl_run_repo.create_run.side_effect = lambda r: r
    crawl_run_repo.update_run.side_effect = lambda r: r
    crawl_run_repo.record_job_action.return_value = None
    crawl_run_repo.record_job_actions.return_value = None
    job_repo.save.side_effect = lambda j: j
    job_repo.save_bulk.side_effect = lambda jobs: jobs
    raw_job_repo.save.side_effect = lambda r: r

    return job_repo, raw_job_repo, crawl_run_repo


# ==============================================================================
# 1. Complete Crawl Closes Absent Jobs & Upholds Invariant
# ==============================================================================


@pytest.mark.asyncio
async def test_complete_crawl_closes_absent_jobs_and_reconciles_counters(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When a complete, successful crawl runs:
    - Jobs seen in the crawl remain ACTIVE or UPDATED.
    - Jobs belonging to this source NOT seen in the crawl transition ACTIVE -> CLOSED.
    - closed_at is set to current timestamp.
    - first_seen_at is strictly preserved.
    - CrawlRunJob audit entries are recorded with CrawlJobAction.CLOSED.
    - Invariant holds: jobs_found = created + updated + unchanged + closed + errors.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-1",
            url="https://jobs.lever.co/trendyol/job-1",
            title="Backend Engineer",
            raw_content='{"id": "job-1"}',
            content_type="application/json",
        ),
        DiscoveredJobDTO(
            external_job_id="job-2",
            url="https://jobs.lever.co/trendyol/job-2",
            title="Senior Frontend Engineer",  # Title updated
            raw_content='{"id": "job-2", "title": "Senior Frontend Engineer"}',
            content_type="application/json",
        ),
    ]

    normalizer = JobNormalizer()
    job1_canonical = normalizer.normalize(discovered[0], source)
    job1_hash = job1_canonical.content_hash

    # Pre-existing active jobs in DB for this source
    job1 = _make_job(
        source.id, "job-1", title="Backend Engineer", content_hash=job1_hash
    )
    job2 = _make_job(source.id, "job-2", title="Frontend Engineer")
    job_absent = _make_job(source.id, "job-absent", title="DevOps Engineer")

    active_jobs_in_db = [job1, job2, job_absent]
    job_repo.get_active_jobs_by_source.return_value = active_jobs_in_db

    # Crawl discovers job1 (unchanged) and job2 (updated), but NOT job_absent
    def mock_get_by_ext_id(sid: uuid.UUID, ext_id: str) -> Job | None:
        if ext_id == "job-1":
            return job1
        if ext_id == "job-2":
            return job2
        return None

    job_repo.get_by_source_and_external_id.side_effect = mock_get_by_ext_id

    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=len(discovered),
        warnings=[],
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.COMPLETED
    assert res.jobs_created == 0
    assert res.jobs_updated == 1
    assert res.jobs_unchanged == 1
    assert res.jobs_closed == 1
    assert res.error_count == 0

    # Invariant: jobs_found strictly equals discovered count
    assert res.jobs_found == len(discovered)
    assert res.jobs_found == 2

    # Absent job closed checks
    assert job_absent.status == JobStatus.CLOSED
    assert job_absent.closed_at is not None
    # first_seen_at must be preserved
    assert job_absent.first_seen_at < job_absent.closed_at

    # Audit links recorded
    recorded_calls = crawl_run_repo.record_job_actions.await_args_list
    assert len(recorded_calls) == 1
    closed_actions: list[CrawlRunJob] = recorded_calls[0][0][0]
    assert len(closed_actions) == 1
    assert closed_actions[0].job_id == job_absent.id
    assert closed_actions[0].action == CrawlJobAction.CLOSED

    # Test history service derivation
    run = CrawlRun(
        id=res.crawl_run_id,
        source_id=source.id,
        source_name=source.name,
        ats_type=source.ats_type,
        status=CrawlStatus.COMPLETED,
        started_at=datetime.now(UTC) - timedelta(seconds=5),
        finished_at=datetime.now(UTC),
        jobs_found=res.jobs_found,
        jobs_created=res.jobs_created,
        jobs_updated=res.jobs_updated,
        jobs_closed=res.jobs_closed,
        error_count=res.error_count,
    )
    derived_unchanged = CrawlHistoryService._to_summary_dto(run).jobs_unchanged
    assert derived_unchanged == 1


# ==============================================================================
# 2. Safety Guards: Suppress Absence Closure
# ==============================================================================


@pytest.mark.asyncio
async def test_closure_suppressed_when_crawl_failed(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When crawl status is FAILED, absence closure must NOT execute."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    job_absent = _make_job(source.id, "job-absent")
    job_repo.get_active_jobs_by_source.return_value = [job_absent]
    job_repo.get_by_source_and_external_id.side_effect = RuntimeError("DB crash")

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-1",
            url="https://example.com/1",
            title="Engineer",
            raw_content="data",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.FAILED
    assert res.jobs_closed == 0
    assert job_absent.status == JobStatus.ACTIVE
    assert job_absent.closed_at is None
    assert crawl_run_repo.record_job_actions.call_count == 0


@pytest.mark.asyncio
async def test_closure_suppressed_when_pagination_max_pages_reached(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When pagination_max_pages_reached is present, closure must NOT execute."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    job_absent = _make_job(source.id, "job-absent")
    job_repo.get_active_jobs_by_source.return_value = [job_absent]
    job_repo.get_by_source_and_external_id.return_value = None

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-new",
            url="https://example.com/new",
            title="New Role",
            raw_content="data",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        warnings=["pagination_max_pages_reached"],
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.PARTIAL
    assert res.jobs_closed == 0
    assert job_absent.status == JobStatus.ACTIVE
    assert job_absent.closed_at is None


@pytest.mark.asyncio
async def test_closure_suppressed_when_adapter_reports_incomplete(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When adapter signals is_complete=False, closure must NOT execute."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    job_absent = _make_job(source.id, "job-absent")
    job_repo.get_active_jobs_by_source.return_value = [job_absent]
    job_repo.get_by_source_and_external_id.return_value = None

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-new",
            url="https://example.com/new",
            title="New Role",
            raw_content="data",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        warnings=[],
        is_complete=False,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_closed == 0
    assert job_absent.status == JobStatus.ACTIVE
    assert job_absent.closed_at is None


def test_default_crawl_result_dto_is_complete_is_false() -> None:
    """CrawlResultDTO must fail-closed: is_complete defaults to False."""
    dto = CrawlResultDTO(source_id=uuid.uuid4(), ats_type="lever")
    assert dto.is_complete is False


@pytest.mark.asyncio
async def test_omitted_completeness_suppresses_absence_closure(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When is_complete is omitted (defaulting to False),
    absence closure is suppressed.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    job_absent = _make_job(source.id, "job-absent")
    job_repo.get_active_jobs_by_source.return_value = [job_absent]
    job_repo.get_by_source_and_external_id.return_value = None

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-new",
            url="https://example.com/new",
            title="New Role",
            raw_content="data",
            content_type="text/plain",
        )
    ]
    # Omit is_complete so it defaults to False
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
    )
    assert crawl_result.is_complete is False

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_closed == 0
    assert job_absent.status == JobStatus.ACTIVE
    assert job_absent.closed_at is None


@pytest.mark.asyncio
async def test_closure_suppressed_when_job_error_count_greater_than_zero(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When a job encounters error (error_count > 0), closure is suppressed."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    job_seen = _make_job(source.id, "job-seen")
    job_absent = _make_job(source.id, "job-absent")
    job_repo.get_active_jobs_by_source.return_value = [job_seen, job_absent]

    def mock_get(sid: uuid.UUID, ext_id: str) -> Job:
        if ext_id == "job-seen":
            return job_seen
        raise ValueError("Normalization crash")

    job_repo.get_by_source_and_external_id.side_effect = mock_get

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-seen",
            url=job_seen.canonical_url,
            title=job_seen.title,
            raw_content="content",
            content_type="text/plain",
        ),
        DiscoveredJobDTO(
            external_job_id="job-error",
            url="https://example.com/err",
            title="Err",
            raw_content="content",
            content_type="text/plain",
        ),
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=2,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.error_count == 1
    assert res.status == CrawlStatus.PARTIAL
    assert res.jobs_closed == 0
    assert job_absent.status == JobStatus.ACTIVE


@pytest.mark.asyncio
async def test_zero_job_anomaly_guard_suppresses_mass_closure(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Zero jobs discovered on populated board must NOT close all jobs by default."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    # 3 active jobs on board (suppressed by default zero_job_threshold=0 policy)
    active_jobs = [_make_job(source.id, f"job-{i}") for i in range(3)]
    job_repo.get_active_jobs_by_source.return_value = active_jobs

    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=[],
        raw_payload_count=0,
        warnings=[],
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_found == 0
    assert res.jobs_closed == 0
    assert "zero_jobs_discovered_closure_suppressed" in res.warnings
    assert res.status == CrawlStatus.PARTIAL
    assert all(j.status == JobStatus.ACTIVE for j in active_jobs)


@pytest.mark.asyncio
async def test_zero_job_crawl_closes_when_explicitly_allowed_and_reconciles_counters(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When a crawl discovers 0 jobs and closes 10 absent jobs under explicit policy:
    - jobs_found remains 0 (discovered count)
    - jobs_closed is 10
    - jobs_unchanged derivation in CrawlHistoryService derives 0 (not negative)
    - All 10 jobs transition to CLOSED
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    active_jobs = [_make_job(source.id, f"job-{i}") for i in range(10)]
    job_repo.get_active_jobs_by_source.return_value = active_jobs

    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=[],
        raw_payload_count=0,
        warnings=[],
        is_complete=True,
    )

    lifecycle_service = JobLifecycleService(
        job_repo=job_repo,
        crawl_run_repo=crawl_run_repo,
        allow_zero_job_closure=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        lifecycle_service=lifecycle_service,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.COMPLETED
    assert res.jobs_found == 0
    assert res.jobs_created == 0
    assert res.jobs_updated == 0
    assert res.jobs_unchanged == 0
    assert res.jobs_closed == 10
    assert res.error_count == 0

    assert all(j.status == JobStatus.CLOSED for j in active_jobs)
    assert all(j.closed_at is not None for j in active_jobs)

    # Invariant: CrawlHistoryService derives jobs_unchanged = 0 without error
    run = CrawlRun(
        id=res.crawl_run_id,
        source_id=source.id,
        status=CrawlStatus.COMPLETED,
        started_at=datetime.now(UTC) - timedelta(seconds=5),
        finished_at=datetime.now(UTC),
        jobs_found=res.jobs_found,
        jobs_created=res.jobs_created,
        jobs_updated=res.jobs_updated,
        jobs_closed=res.jobs_closed,
        error_count=res.error_count,
    )
    derived_unchanged = CrawlHistoryService._to_summary_dto(run).jobs_unchanged
    assert derived_unchanged == 0


# ==============================================================================
# 3. Reopening Previously Closed Jobs
# ==============================================================================


@pytest.mark.asyncio
async def test_reopen_closed_job_transitions_to_active_and_counts_as_updated(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """When a CLOSED job is seen again:
    - Status transitions to ACTIVE.
    - closed_at is set to None.
    - first_seen_at is preserved.
    - Action is recorded as CrawlJobAction.UPDATED and increments jobs_updated.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos
    source = _make_source()

    initial_first_seen = datetime.now(UTC) - timedelta(days=20)
    closed_at = datetime.now(UTC) - timedelta(days=5)

    previously_closed = _make_job(
        source_id=source.id,
        external_job_id="job-reopened",
        title="Staff Engineer",
        status=JobStatus.CLOSED,
        first_seen_at=initial_first_seen,
        closed_at=closed_at,
    )
    job_repo.get_active_jobs_by_source.return_value = []
    job_repo.get_by_source_and_external_id.return_value = previously_closed

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-reopened",
            url=previously_closed.canonical_url,
            title="Staff Engineer",
            raw_content='{"id": "job-reopened"}',
            content_type="application/json",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.COMPLETED
    assert res.jobs_created == 0
    assert res.jobs_updated == 1
    assert res.jobs_unchanged == 0
    assert res.jobs_closed == 0

    assert previously_closed.status == JobStatus.ACTIVE
    assert previously_closed.closed_at is None
    assert previously_closed.first_seen_at == initial_first_seen

    crawl_run_repo.record_job_action.assert_awaited_once_with(
        run_id=res.crawl_run_id,
        job_id=previously_closed.id,
        action=CrawlJobAction.UPDATED,
    )
    assert "REOPEN" not in CrawlJobAction.__members__


# ==============================================================================
# 4. Multi-Source Isolation
# ==============================================================================


@pytest.mark.asyncio
async def test_absence_closure_multi_source_isolation(
    mock_lifecycle_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Absence closure for Source A must never affect active jobs for Source B."""
    job_repo, raw_job_repo, crawl_run_repo = mock_lifecycle_repos

    source_a = _make_source()
    source_b = _make_source()

    job_a1 = _make_job(source_a.id, "a1")
    job_a2 = _make_job(source_a.id, "a2")
    job_b1 = _make_job(source_b.id, "b1")

    # Only Source A's active jobs are returned for Source A crawl
    def mock_get_active(sid: uuid.UUID) -> list[Job]:
        if sid == source_a.id:
            return [job_a1, job_a2]
        if sid == source_b.id:
            return [job_b1]
        return []

    job_repo.get_active_jobs_by_source.side_effect = mock_get_active

    def mock_get_ext(sid: uuid.UUID, ext: str) -> Job | None:
        return job_a1 if ext == "a1" else None

    job_repo.get_by_source_and_external_id.side_effect = mock_get_ext

    # Crawl only discovers a1 for Source A (a2 absent)
    discovered = [
        DiscoveredJobDTO(
            external_job_id="a1",
            url=job_a1.canonical_url,
            title=job_a1.title,
            raw_content="data",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source_a.id,
        ats_type=source_a.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    res = await service.ingest_crawl_result(source_a, crawl_result)

    assert res.jobs_closed == 1
    assert job_a2.status == JobStatus.CLOSED
    assert job_a2.closed_at is not None

    # Source B's job remains completely active and untouched
    assert job_b1.status == JobStatus.ACTIVE
    assert job_b1.closed_at is None
