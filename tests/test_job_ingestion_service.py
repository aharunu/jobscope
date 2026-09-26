"""Integration and unit tests for JobIngestionService."""

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
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository


def _make_source(source_id: uuid.UUID | None = None) -> RuntimeSourceDTO:
    return RuntimeSourceDTO(
        id=source_id or uuid.uuid4(),
        name="Trendyol Lever",
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


def _make_crawl_result(
    source_id: uuid.UUID,
    jobs: list[DiscoveredJobDTO],
    warnings: list[str] | None = None,
) -> CrawlResultDTO:
    return CrawlResultDTO(
        source_id=source_id,
        ats_type="lever",
        jobs=jobs,
        raw_payload_count=len(jobs),
        warnings=warnings or [],
    )


@pytest.fixture
def mock_repos() -> tuple[AsyncMock, AsyncMock, AsyncMock]:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)

    # Default behaviors
    crawl_run_repo.create_run.side_effect = lambda r: r
    crawl_run_repo.update_run.side_effect = lambda r: r
    job_repo.save.side_effect = lambda j: j
    raw_job_repo.save.side_effect = lambda r: r

    return job_repo, raw_job_repo, crawl_run_repo


@pytest.mark.asyncio
async def test_ingest_all_new_jobs(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Verify newly discovered jobs are created and audit links recorded."""
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-1",
            url="https://jobs.lever.co/trendyol/job-1",
            title="Senior Backend Go Engineer",
            raw_content='{"id": "job-1"}',
            content_type="application/json",
            metadata={"location": "Istanbul"},
        ),
        DiscoveredJobDTO(
            external_job_id="job-2",
            url="https://jobs.lever.co/trendyol/job-2",
            title="Senior QA Engineer",
            raw_content='{"id": "job-2"}',
            content_type="application/json",
            metadata={"location": "Izmir"},
        ),
    ]

    job_repo.get_by_source_and_external_id.return_value = None

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.status == CrawlStatus.COMPLETED
    assert result.jobs_found == 2
    assert result.jobs_created == 2
    assert result.jobs_updated == 0
    assert result.jobs_unchanged == 0
    assert result.jobs_closed == 0
    assert result.error_count == 0

    assert job_repo.save.call_count == 2
    assert raw_job_repo.save.call_count == 2
    assert crawl_run_repo.record_job_action.call_count == 2

    # Check that first_seen_at and last_seen_at are populated
    saved_jobs: list[Job] = [call.args[0] for call in job_repo.save.call_args_list]
    for saved in saved_jobs:
        assert saved.first_seen_at is not None
        assert saved.last_seen_at is not None
        assert saved.status == JobStatus.ACTIVE


@pytest.mark.asyncio
async def test_deduplication_by_external_id_never_falls_back(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 1: When external_job_id exists, lookup MUST use only
    (source_id, external_job_id) and NEVER query canonical_url.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-abc",
            url="https://jobs.lever.co/trendyol/job-abc",
            title="Frontend Dev",
            raw_content='{"id": "job-abc"}',
            content_type="application/json",
        )
    ]
    job_repo.get_by_source_and_external_id.return_value = None

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    await service.ingest_crawl_result(source, crawl_result)

    job_repo.get_by_source_and_external_id.assert_awaited_once_with(
        source.id, "job-abc"
    )
    assert job_repo.get_by_canonical_url.call_count == 0


@pytest.mark.asyncio
async def test_deduplication_by_canonical_url_when_external_id_missing(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 1: Query canonical_url ONLY when external_id is None."""
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id=None,
            url="https://jobs.lever.co/trendyol/custom-page",
            title="Recruiter",
            raw_content="Recruiter role",
            content_type="text/plain",
        )
    ]
    job_repo.get_by_canonical_url.return_value = None

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    await service.ingest_crawl_result(source, crawl_result)

    assert job_repo.get_by_source_and_external_id.call_count == 0
    job_repo.get_by_canonical_url.assert_awaited_once_with(
        "https://jobs.lever.co/trendyol/custom-page"
    )


@pytest.mark.asyncio
async def test_ingest_unchanged_job(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 4: When content_hash matches, job is UNCHANGED:
    - first_seen_at is preserved
    - last_seen_at is touched
    - no new RawJob is saved
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    normalizer = JobNormalizer()
    content_hash = normalizer.compute_content_hash(
        title="Data Engineer",
        description='{"id": "job-de"}',
        location="Remote",
        work_mode=None,
    )

    original_first_seen = datetime.now(UTC) - timedelta(days=10)
    existing_job = Job(
        source_id=source.id,
        external_job_id="job-de",
        canonical_url="https://jobs.lever.co/trendyol/job-de",
        company="Trendyol",
        title="Data Engineer",
        description='{"id": "job-de"}',
        location="Remote",
        content_hash=content_hash,
        first_seen_at=original_first_seen,
        last_seen_at=original_first_seen,
        status=JobStatus.ACTIVE,
    )
    job_repo.get_by_source_and_external_id.return_value = existing_job

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-de",
            url="https://jobs.lever.co/trendyol/job-de",
            title="Data Engineer",
            raw_content='{"id": "job-de"}',
            content_type="application/json",
            metadata={"location": "Remote"},
        )
    ]

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        normalizer=normalizer,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.jobs_created == 0
    assert result.jobs_updated == 0
    assert result.jobs_unchanged == 1
    assert result.error_count == 0

    # first_seen_at must be strictly preserved
    assert existing_job.first_seen_at == original_first_seen
    # last_seen_at must be updated
    assert existing_job.last_seen_at > original_first_seen

    # No new raw job created for unchanged content
    assert raw_job_repo.save.call_count == 0

    # Recorded as UNCHANGED
    crawl_run_repo.record_job_action.assert_awaited_once_with(
        run_id=result.crawl_run_id,
        job_id=existing_job.id,
        action=CrawlJobAction.UNCHANGED,
    )


@pytest.mark.asyncio
async def test_ingest_updated_job(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 4: When content_hash differs, job is UPDATED:
    - first_seen_at is preserved
    - last_seen_at is updated
    - mutable fields updated
    - new RawJob is saved
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    original_first_seen = datetime.now(UTC) - timedelta(days=5)
    existing_job = Job(
        source_id=source.id,
        external_job_id="job-up",
        canonical_url="https://jobs.lever.co/trendyol/job-up",
        company="Trendyol",
        title="Mid Backend Engineer",
        description="Old description",
        location="Istanbul",
        content_hash="old_hash_1234",
        first_seen_at=original_first_seen,
        last_seen_at=original_first_seen,
        status=JobStatus.ACTIVE,
    )
    job_repo.get_by_source_and_external_id.return_value = existing_job

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-up",
            url="https://jobs.lever.co/trendyol/job-up",
            title="Senior Backend Engineer",  # Promoted title
            raw_content='{"id": "job-up", "text": "Senior Backend Engineer"}',
            content_type="application/json",
            metadata={"location": "Berlin", "salary": "90k"},
        )
    ]

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.jobs_created == 0
    assert result.jobs_updated == 1
    assert result.jobs_unchanged == 0

    assert existing_job.first_seen_at == original_first_seen
    assert existing_job.last_seen_at > original_first_seen
    assert existing_job.title == "Senior Backend Engineer"
    assert existing_job.location == "Berlin"
    assert existing_job.salary == "90k"

    # New RawJob must be saved for updated job
    assert raw_job_repo.save.call_count == 1
    crawl_run_repo.record_job_action.assert_awaited_once_with(
        run_id=result.crawl_run_id,
        job_id=existing_job.id,
        action=CrawlJobAction.UPDATED,
    )


@pytest.mark.asyncio
async def test_reopen_closed_job(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 4: Re-opening sets status=ACTIVE, clears closed_at=None,
    and preserves first_seen_at.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    normalizer = JobNormalizer()
    content_hash = normalizer.compute_content_hash(
        title="Reopened Position",
        description='{"id": "job-reopen"}',
        location=None,
        work_mode=None,
    )

    original_first_seen = datetime.now(UTC) - timedelta(days=30)
    existing_job = Job(
        source_id=source.id,
        external_job_id="job-reopen",
        canonical_url="https://jobs.lever.co/trendyol/job-reopen",
        company="Trendyol",
        title="Reopened Position",
        description='{"id": "job-reopen"}',
        content_hash=content_hash,
        first_seen_at=original_first_seen,
        last_seen_at=original_first_seen,
        status=JobStatus.CLOSED,
        closed_at=datetime.now(UTC) - timedelta(days=2),
    )
    job_repo.get_by_source_and_external_id.return_value = existing_job

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-reopen",
            url="https://jobs.lever.co/trendyol/job-reopen",
            title="Reopened Position",
            raw_content='{"id": "job-reopen"}',
            content_type="application/json",
        )
    ]

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        normalizer=normalizer,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.status == CrawlStatus.COMPLETED
    assert existing_job.status == JobStatus.ACTIVE
    assert existing_job.closed_at is None
    assert existing_job.first_seen_at == original_first_seen


@pytest.mark.asyncio
async def test_warnings_set_partial_status_without_error_count(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Mandatory Correction 6: CrawlResultDTO.warnings
    sets CrawlStatus.PARTIAL without falsely incrementing error_count.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-p1",
            url="https://jobs.lever.co/trendyol/job-p1",
            title="Engineer",
            raw_content='{"id": "job-p1"}',
            content_type="application/json",
        )
    ]
    job_repo.get_by_source_and_external_id.return_value = None

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(
        source.id,
        discovered,
        warnings=["pagination_max_pages_reached"],
    )
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.status == CrawlStatus.PARTIAL
    assert result.error_count == 0
    assert result.jobs_created == 1
    assert "pagination_max_pages_reached" in result.warnings


@pytest.mark.asyncio
async def test_item_processing_error_handling(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Verify single corrupt item error doesn't abort batch, error_count is incremented,
    and status becomes PARTIAL.
    """
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="bad-item",
            url="https://jobs.lever.co/trendyol/bad-item",
            title="Bad Item",
            raw_content="corrupt",
            content_type="text/plain",
        ),
        DiscoveredJobDTO(
            external_job_id="good-item",
            url="https://jobs.lever.co/trendyol/good-item",
            title="Good Item",
            raw_content="valid",
            content_type="text/plain",
        ),
    ]

    job_repo.get_by_source_and_external_id.return_value = None
    # Simulate DB error on first job save only
    job_repo.save.side_effect = [
        RuntimeError("DB constraint violation"),
        Job(
            source_id=source.id,
            canonical_url="https://jobs.lever.co/trendyol/good-item",
            company="Trendyol",
            title="Good Item",
            description="valid",
            content_hash="goodhash",
        ),
    ]

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.jobs_created == 1
    assert result.error_count == 1
    assert result.status == CrawlStatus.PARTIAL
    assert len(result.errors) == 1
    assert "DB constraint violation" in result.errors[0]


@pytest.mark.asyncio
async def test_all_items_failed_sets_status_failed(
    mock_repos: tuple[AsyncMock, AsyncMock, AsyncMock],
) -> None:
    """Verify when all items encounter errors, status is FAILED."""
    job_repo, raw_job_repo, crawl_run_repo = mock_repos
    source = _make_source()

    discovered = [
        DiscoveredJobDTO(
            external_job_id="item-1",
            url="https://jobs.lever.co/trendyol/item-1",
            title="Item 1",
            raw_content="content",
            content_type="text/plain",
        )
    ]
    job_repo.get_by_source_and_external_id.return_value = None
    job_repo.save.side_effect = RuntimeError("Fatal DB failure")

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    crawl_result = _make_crawl_result(source.id, discovered)
    result = await service.ingest_crawl_result(source, crawl_result)

    assert result.jobs_created == 0
    assert result.error_count == 1
    assert result.status == CrawlStatus.FAILED
