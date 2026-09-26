"""Integration tests for Job Requirement Extraction Pipeline."""

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
from backend.application.job_processing.extraction import (
    RequirementExtractionService,
    RequirementExtractor,
)
from backend.application.job_processing.lifecycle import JobLifecycleService
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import (
    JobRepository,
    JobRequirementRepository,
    RawJobRepository,
)
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)


class InMemoryJobRequirementRepository(JobRequirementRepository):
    """In-memory implementation of JobRequirementRepository for tests."""

    def __init__(self) -> None:
        self.requirements: dict[uuid.UUID, list[JobRequirement]] = {}

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[JobRequirement]:
        return list(self.requirements.get(job_id, []))

    async def save_requirements(
        self,
        job_id: uuid.UUID,
        requirements: list[JobRequirement],
    ) -> list[JobRequirement]:
        # Atomic replacement
        self.requirements[job_id] = list(requirements)
        return list(requirements)

    async def delete_by_job_id(self, job_id: uuid.UUID) -> int:
        removed = self.requirements.pop(job_id, [])
        return len(removed)


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
    title: str = "Senior Python Engineer",
    status: JobStatus = JobStatus.ACTIVE,
    first_seen_at: datetime | None = None,
    closed_at: datetime | None = None,
    location: str | None = "TR",
) -> Job:
    now = datetime.now(UTC)
    desc = "Core Python engineering"
    content_hash = JobNormalizer.compute_content_hash(
        title=title,
        description=desc,
        location=location,
    )
    return Job(
        id=uuid.uuid4(),
        source_id=source_id,
        external_job_id=external_job_id,
        canonical_url=f"https://jobs.lever.co/trendyol/{external_job_id}",
        company="Trendyol",
        title=title,
        description=desc,
        location=location,
        content_hash=content_hash,
        first_seen_at=first_seen_at or now,
        last_seen_at=now,
        closed_at=closed_at,
        status=status,
    )


# 19. Canonical Job ingestion followed by requirement extraction
@pytest.mark.asyncio
async def test_canonical_job_ingestion_followed_by_requirement_extraction() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    job_repo.get_by_source_and_external_id.return_value = None
    job_repo.save.side_effect = lambda j: j
    job_repo.get_active_jobs_by_source.return_value = []

    crawl_run_repo.create_run.side_effect = lambda r: r

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-py-1",
            url="https://jobs.lever.co/trendyol/job-py-1",
            title="Backend Engineer",
            raw_content="dummy",
            content_type="text/plain",
            metadata={
                "description": (
                    "Requirements:\n"
                    "- 3+ years experience with Python and FastAPI.\n"
                    "- Knowledge of PostgreSQL and Docker.\n"
                    "- Bachelor's degree in Computer Science."
                )
            },
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    extractor = DeterministicRequirementExtractor()
    req_service = RequirementExtractionService(
        requirement_repo=req_repo,
        extractor=extractor,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        job_requirement_repo=req_repo,
        requirement_service=req_service,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.status == CrawlStatus.COMPLETED
    assert res.jobs_created == 1
    assert res.jobs_updated == 0

    # Verify requirements were persisted for the new job
    saved_jobs = [call.args[0] for call in job_repo.save.call_args_list]
    saved_job = saved_jobs[0]
    extracted = await req_repo.get_by_job_id(saved_job.id)

    skills = {r.normalized_skill for r in extracted}
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PostgreSQL" in skills
    assert "Docker" in skills
    assert "Bachelor's Degree" in skills
    assert "Computer Science" in skills


# 20. Extraction failure follows established warning/error semantics
@pytest.mark.asyncio
async def test_extraction_failure_follows_warning_error_semantics() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    job_repo.get_by_source_and_external_id.return_value = None
    job_repo.save.side_effect = lambda j: j
    job_repo.get_active_jobs_by_source.return_value = []
    crawl_run_repo.create_run.side_effect = lambda r: r

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-fail-1",
            url="https://jobs.lever.co/trendyol/job-fail-1",
            title="Backend Engineer",
            raw_content="dummy",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    # Faulty extractor that raises an unexpected exception
    faulty_extractor = AsyncMock(spec=RequirementExtractor)
    faulty_extractor.extract.side_effect = RuntimeError("Parser internal error")

    req_service = RequirementExtractionService(
        requirement_repo=req_repo,
        extractor=faulty_extractor,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        requirement_service=req_service,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    # Invariant: Job is successfully created;
    # extraction failure surfaces as warning -> PARTIAL
    assert res.jobs_created == 1
    assert res.error_count == 0
    assert res.status == CrawlStatus.PARTIAL
    assert any("requirement_extraction_failed" in w for w in res.warnings)


# 21. Existing Job lifecycle behavior remains unchanged
@pytest.mark.asyncio
async def test_job_lifecycle_remains_unchanged_with_extraction() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    existing_active = _make_job(source.id, "job-unchanged")
    job_repo.get_by_source_and_external_id.return_value = existing_active
    job_repo.save.side_effect = lambda j: j
    job_repo.get_active_jobs_by_source.return_value = [existing_active]
    crawl_run_repo.create_run.side_effect = lambda r: r

    # Discovered job matches existing hash -> UNCHANGED
    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-unchanged",
            url=existing_active.canonical_url,
            title=existing_active.title,
            raw_content="dummy",
            content_type="text/plain",
            metadata={"description": existing_active.description},
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        job_requirement_repo=req_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_unchanged == 1
    assert res.jobs_created == 0
    assert res.jobs_updated == 0
    assert res.jobs_closed == 0


# 22. CrawlRun counters remain semantically correct
@pytest.mark.asyncio
async def test_crawl_run_counters_with_requirements() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    job_repo.get_by_source_and_external_id.return_value = None
    job_repo.save.side_effect = lambda j: j
    job_repo.get_active_jobs_by_source.return_value = []
    crawl_run_repo.create_run.side_effect = lambda r: r

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-1",
            url="https://jobs.lever.co/trendyol/job-1",
            title="Python Dev",
            raw_content="dummy",
            content_type="text/plain",
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        job_requirement_repo=req_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_found == 1
    assert res.jobs_created == 1
    assert res.jobs_updated == 0
    assert res.jobs_unchanged == 0
    assert res.jobs_closed == 0
    assert res.error_count == 0

    run = CrawlRun(
        id=res.crawl_run_id,
        source_id=source.id,
        status=res.status,
        started_at=datetime.now(UTC),
        jobs_found=res.jobs_found,
        jobs_created=res.jobs_created,
        jobs_updated=res.jobs_updated,
        jobs_closed=res.jobs_closed,
        error_count=res.error_count,
    )
    derived = CrawlHistoryService._to_summary_dto(run)
    assert derived.jobs_unchanged == 0


# 23. CLOSED -> ACTIVE reopening behavior remains unchanged with requirements
@pytest.mark.asyncio
async def test_reopen_closed_job_extracts_updated_requirements() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    initial_first_seen = datetime.now(UTC) - timedelta(days=30)
    closed_at = datetime.now(UTC) - timedelta(days=10)

    closed_job = _make_job(
        source_id=source.id,
        external_job_id="job-reopen-1",
        title="Python Engineer",
        status=JobStatus.CLOSED,
        first_seen_at=initial_first_seen,
        closed_at=closed_at,
    )
    job_repo.get_by_source_and_external_id.return_value = closed_job
    job_repo.save.side_effect = lambda j: j
    job_repo.get_active_jobs_by_source.return_value = []
    crawl_run_repo.create_run.side_effect = lambda r: r

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-reopen-1",
            url=closed_job.canonical_url,
            title="Senior Python & Rust Engineer",
            raw_content="dummy",
            content_type="text/plain",
            metadata={"description": "Requirements: Python, Rust, Docker."},
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        job_requirement_repo=req_repo,
        requirement_extractor=DeterministicRequirementExtractor(),
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_updated == 1
    assert closed_job.status == JobStatus.ACTIVE
    assert closed_job.closed_at is None
    assert closed_job.first_seen_at == initial_first_seen

    # Verifies requirements were extracted upon reopening
    extracted = await req_repo.get_by_job_id(closed_job.id)
    skills = {r.normalized_skill for r in extracted}
    assert "Python" in skills
    assert "Rust" in skills
    assert "Docker" in skills


# 24. Existing Phase 4.7 absence closure behavior remains unchanged
@pytest.mark.asyncio
async def test_absence_closure_remains_functional_with_requirements() -> None:
    job_repo = AsyncMock(spec=JobRepository)
    raw_job_repo = AsyncMock(spec=RawJobRepository)
    crawl_run_repo = AsyncMock(spec=CrawlRunRepository)
    req_repo = InMemoryJobRequirementRepository()

    source = _make_source()
    active_job_1 = _make_job(source.id, "job-present")
    active_job_2 = _make_job(source.id, "job-absent")

    job_repo.get_active_jobs_by_source.return_value = [active_job_1, active_job_2]

    def mock_get(sid: uuid.UUID, ext: str) -> Job | None:
        if ext == "job-present":
            return active_job_1
        return None

    job_repo.get_by_source_and_external_id.side_effect = mock_get
    job_repo.save.side_effect = lambda j: j
    job_repo.save_bulk.side_effect = lambda jobs: jobs
    crawl_run_repo.create_run.side_effect = lambda r: r
    crawl_run_repo.update_run.side_effect = lambda r: r
    crawl_run_repo.record_job_actions.return_value = None

    discovered = [
        DiscoveredJobDTO(
            external_job_id="job-present",
            url=active_job_1.canonical_url,
            title=active_job_1.title,
            raw_content="dummy",
            content_type="text/plain",
            metadata={"description": active_job_1.description},
        )
    ]
    crawl_result = CrawlResultDTO(
        source_id=source.id,
        ats_type=source.ats_type,
        jobs=discovered,
        raw_payload_count=1,
        is_complete=True,
    )

    lifecycle = JobLifecycleService(
        job_repo=job_repo,
        crawl_run_repo=crawl_run_repo,
    )
    service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        lifecycle_service=lifecycle,
        job_requirement_repo=req_repo,
    )

    res = await service.ingest_crawl_result(source, crawl_result)

    assert res.jobs_found == 1
    assert res.jobs_unchanged == 1
    assert res.jobs_closed == 1
    assert active_job_2.status == JobStatus.CLOSED
    assert active_job_2.closed_at is not None
