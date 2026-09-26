"""Integration tests for Greenhouse ATS Adapter with Crawler and Ingestion Pipeline."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    CrawlExecutionResultDTO,
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
)
from backend.application.job_discovery.ports import RuntimeSourceProvider
from backend.application.job_processing.extraction import RequirementExtractionService
from backend.application.job_processing.lifecycle import JobLifecycleService
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.entities import Job, JobRequirement, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import (
    JobRepository,
    JobRequirementRepository,
    RawJobRepository,
)
from backend.domain.source.entities import Source
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.ats.greenhouse import GreenhouseAdapter
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)
from tests.test_greenhouse_adapter import (
    SAMPLE_GREENHOUSE_POSTINGS,
    MockSafeHttpClient,
    make_greenhouse_source,
)

# ==============================================================================
# In-Memory Test Doubles
# ==============================================================================


class InMemoryRuntimeSourceProvider(RuntimeSourceProvider):
    """In-memory mock provider implementing RuntimeSourceProvider protocol."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self._sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_crawlable_source(
        self, source_id: uuid.UUID
    ) -> RuntimeSourceDTO | None:
        source = self._sources.get(source_id)
        if not source or not source.active:
            return None
        return RuntimeSourceDTO.from_domain(source)

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        res = [s for s in self._sources.values() if s.active]
        if ats_type is not None:
            res = [s for s in res if s.ats_type == ats_type]
        sliced = res[offset : offset + limit if limit else None]
        return [RuntimeSourceDTO.from_domain(s) for s in sliced]


class InMemoryJobRepository(JobRepository):
    """In-memory Job repository for pipeline integration tests."""

    def __init__(self) -> None:
        self.jobs: dict[uuid.UUID, Job] = {}

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    async def get_by_source_and_external_id(
        self, source_id: uuid.UUID, external_job_id: str
    ) -> Job | None:
        for job in self.jobs.values():
            if job.source_id == source_id and job.external_job_id == external_job_id:
                return job
        return None

    async def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        for job in self.jobs.values():
            if job.canonical_url == canonical_url:
                return job
        return None

    async def get_active_jobs_by_source(self, source_id: uuid.UUID) -> list[Job]:
        return [
            j
            for j in self.jobs.values()
            if j.source_id == source_id and j.status == JobStatus.ACTIVE
        ]

    async def save(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    async def save_bulk(self, jobs: list[Job]) -> list[Job]:
        for job in jobs:
            self.jobs[job.id] = job
        return jobs

    async def save_all(self, jobs: list[Job]) -> list[Job]:
        for job in jobs:
            self.jobs[job.id] = job
        return jobs

    async def list_jobs(self, **kwargs: Any) -> tuple[list[Job], int]:
        items = list(self.jobs.values())
        return items, len(items)


class InMemoryRawJobRepository(RawJobRepository):
    """In-memory RawJob repository for pipeline integration tests."""

    def __init__(self) -> None:
        self.raw_jobs: list[RawJob] = []

    async def save(self, raw_job: RawJob) -> RawJob:
        self.raw_jobs.append(raw_job)
        return raw_job

    async def save_all(self, raw_jobs: list[RawJob]) -> list[RawJob]:
        self.raw_jobs.extend(raw_jobs)
        return raw_jobs

    async def get_by_id(self, raw_job_id: uuid.UUID) -> RawJob | None:
        for r in self.raw_jobs:
            if r.id == raw_job_id:
                return r
        return None

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[RawJob]:
        return [r for r in self.raw_jobs if r.job_id == job_id]


class InMemoryJobRequirementRepository(JobRequirementRepository):
    """In-memory JobRequirement repository."""

    def __init__(self) -> None:
        self.requirements: dict[uuid.UUID, list[JobRequirement]] = {}

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[JobRequirement]:
        return list(self.requirements.get(job_id, []))

    async def save_requirements(
        self, job_id: uuid.UUID, requirements: list[JobRequirement]
    ) -> list[JobRequirement]:
        self.requirements[job_id] = list(requirements)
        return list(requirements)

    async def delete_by_job_id(self, job_id: uuid.UUID) -> int:
        removed = self.requirements.pop(job_id, [])
        return len(removed)


class InMemoryCrawlRunRepository(CrawlRunRepository):
    """In-memory CrawlRun repository."""

    def __init__(self) -> None:
        self.runs: dict[uuid.UUID, CrawlRun] = {}
        self.run_jobs: list[CrawlRunJob] = []

    async def create_run(self, run: CrawlRun) -> CrawlRun:
        self.runs[run.id] = run
        return run

    async def update_run(self, run: CrawlRun) -> CrawlRun:
        self.runs[run.id] = run
        return run

    async def get_by_id(self, run_id: uuid.UUID) -> CrawlRun | None:
        return self.runs.get(run_id)

    async def save(self, run: CrawlRun) -> CrawlRun:
        self.runs[run.id] = run
        return run

    async def save_all(self, runs: list[CrawlRun]) -> list[CrawlRun]:
        for r in runs:
            self.runs[r.id] = r
        return runs

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        matching = [r for r in self.runs.values() if r.source_id == source_id]
        if not matching:
            return None
        return max(
            matching, key=lambda r: r.started_at or datetime.min.replace(tzinfo=UTC)
        )

    async def list_runs(self, **kwargs: Any) -> tuple[list[CrawlRun], int]:
        items = list(self.runs.values())
        return items, len(items)

    async def record_job_actions(self, links: list[CrawlRunJob]) -> None:
        self.run_jobs.extend(links)

    async def record_job_action(
        self, run_id: uuid.UUID, job_id: uuid.UUID, action: Any
    ) -> None:
        self.run_jobs.append(
            CrawlRunJob(crawl_run_id=run_id, job_id=job_id, action=action)
        )

    async def save_run_job(self, run_job: CrawlRunJob) -> CrawlRunJob:
        self.run_jobs.append(run_job)
        return run_job

    async def save_run_jobs(self, run_jobs: list[CrawlRunJob]) -> list[CrawlRunJob]:
        self.run_jobs.extend(run_jobs)
        return run_jobs

    async def list_run_jobs(self, **kwargs: Any) -> tuple[list[CrawlRunJob], int]:
        return list(self.run_jobs), len(self.run_jobs)


# ==============================================================================
# Registry & Factory Tests
# ==============================================================================


def test_registry_resolves_greenhouse_adapter() -> None:
    """Verify create_adapter_registry registers GreenhouseAdapter
    alongside LeverAdapter.
    """
    mock_http = MockSafeHttpClient()
    registry = create_adapter_registry(http_client=mock_http)

    assert registry.is_supported("greenhouse") is True
    assert registry.is_supported("lever") is True
    assert registry.is_supported("workday") is False

    adapter = registry.get_adapter("greenhouse")
    assert isinstance(adapter, GreenhouseAdapter)
    assert adapter.ats_type == "greenhouse"

    # Case-insensitivity & whitespace trimming
    assert registry.get_adapter("GREENHOUSE") is adapter
    assert registry.get_adapter("  greenhouse  ") is adapter
    assert registry.list_supported_types() == ["greenhouse", "lever"]


# ==============================================================================
# Orchestrator Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_crawler_orchestrator_crawls_greenhouse_source() -> None:
    """Verify orchestrator coordinates discovery for a Greenhouse source."""
    source = Source(
        id=uuid.uuid4(),
        name="Gram Games Careers",
        url="https://boards.greenhouse.io/gramgamescareers",
        ats_type="greenhouse",
        company="Gram Games",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs",
                text=json.dumps({"jobs": SAMPLE_GREENHOUSE_POSTINGS}),
            )
        ]
    )
    registry = create_adapter_registry(http_client=mock_http)

    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
    )

    result = await orchestrator.crawl_source(source.id)

    assert isinstance(result, CrawlExecutionResultDTO)
    assert result.success is True
    assert result.status == CrawlStatus.COMPLETED
    assert result.source_id == source.id
    assert result.source_name == "Gram Games Careers"
    assert result.ats_type == "greenhouse"
    assert result.jobs_found == 2
    assert result.error_type is None
    assert result.crawl_result is not None
    assert len(result.crawl_result.jobs) == 2

    job1 = result.crawl_result.jobs[0]
    assert job1.external_job_id == "4829101"
    assert job1.title == "Senior Backend Engineer - Python"
    assert job1.metadata["company"] == "Gram Games"


@pytest.mark.asyncio
async def test_crawler_orchestrator_crawls_sources_by_ats_type_greenhouse() -> None:
    """Verify crawl_sources_by_ats_type('greenhouse') crawls only Greenhouse sources."""
    gh_source_1 = Source(
        id=uuid.uuid4(),
        name="Gram Games",
        url="https://boards.greenhouse.io/gramgamescareers",
        ats_type="greenhouse",
        company="Gram Games",
        active=True,
    )
    gh_source_2 = Source(
        id=uuid.uuid4(),
        name="Oliver Agency",
        url="https://job-boards.greenhouse.io/oliver",
        ats_type="greenhouse",
        company="Oliver Agency",
        active=True,
    )
    lever_source = Source(
        id=uuid.uuid4(),
        name="Trendyol",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([gh_source_1, gh_source_2, lever_source])

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": SAMPLE_GREENHOUSE_POSTINGS}),
            ),
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": []}),
            ),
        ]
    )
    registry = create_adapter_registry(http_client=mock_http)
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
    )

    results = await orchestrator.crawl_sources_by_ats_type("greenhouse")

    assert len(results) == 2
    assert {r.source_id for r in results} == {gh_source_1.id, gh_source_2.id}
    assert all(r.ats_type == "greenhouse" for r in results)
    assert all(r.success is True for r in results)


# ==============================================================================
# Full Pipeline: Discovery -> Normalization -> Ingestion -> Requirements
# ==============================================================================


@pytest.mark.asyncio
async def test_full_greenhouse_pipeline_ingestion_and_requirement_extraction() -> None:
    """Verify full end-to-end pipeline:
    GreenhouseAdapter -> DiscoveredJobDTO -> JobNormalizer -> JobIngestionService
    -> Job -> RequirementExtractionService -> JobRequirement saved.
    """
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs",
                text=json.dumps({"jobs": SAMPLE_GREENHOUSE_POSTINGS}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    crawl_result = await adapter.crawl(source)
    assert crawl_result.is_complete is True
    assert len(crawl_result.jobs) == 2

    # Ingestion setup
    job_repo = InMemoryJobRepository()
    raw_job_repo = InMemoryRawJobRepository()
    crawl_run_repo = InMemoryCrawlRunRepository()
    req_repo = InMemoryJobRequirementRepository()

    extraction_service = RequirementExtractionService(
        requirement_repo=req_repo,
        extractor=DeterministicRequirementExtractor(),
    )
    lifecycle_service = JobLifecycleService(
        job_repo=job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    ingestion_service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        lifecycle_service=lifecycle_service,
        requirement_service=extraction_service,
    )

    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    await crawl_run_repo.save(run)

    summary = await ingestion_service.ingest_crawl_result(
        source, crawl_result, crawl_run_id=run.id
    )

    # 1. Verify CrawlRun summary counters
    assert summary.jobs_found == 2
    assert summary.jobs_created == 2
    assert summary.jobs_updated == 0
    assert summary.jobs_unchanged == 0
    assert summary.jobs_closed == 0
    assert summary.error_count == 0

    # Invariant:
    # jobs_found == created + updated + unchanged + closed + error_count
    assert (
        summary.jobs_found
        == summary.jobs_created
        + summary.jobs_updated
        + summary.jobs_unchanged
        + summary.jobs_closed
        + summary.error_count
    )

    # 2. Verify Canonical Jobs persisted
    persisted_jobs = await job_repo.get_active_jobs_by_source(source.id)
    assert len(persisted_jobs) == 2
    job_map = {j.external_job_id: j for j in persisted_jobs}

    assert "4829101" in job_map
    assert "4829102" in job_map
    job1 = job_map["4829101"]
    assert job1.title == "Senior Backend Engineer - Python"
    assert job1.company == "Gram Games"
    assert job1.status == JobStatus.ACTIVE

    # 3. Verify Phase 4.8 Requirement Extraction
    reqs_job1 = await req_repo.get_by_job_id(job1.id)
    assert len(reqs_job1) > 0
    skill_names_job1 = [
        r.normalized_skill.lower() for r in reqs_job1 if r.normalized_skill
    ]
    assert "python" in skill_names_job1
    assert "fastapi" in skill_names_job1

    job2 = job_map["4829102"]
    reqs_job2 = await req_repo.get_by_job_id(job2.id)
    assert len(reqs_job2) > 0
    skill_names_job2 = [
        r.normalized_skill.lower() for r in reqs_job2 if r.normalized_skill
    ]
    assert "sql" in skill_names_job2
    assert "python" in skill_names_job2


# ==============================================================================
# Phase 4.7 Absence Closure & Zero-Job Safety Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_phase_4_7_absence_closure() -> None:
    """Verify Phase 4.7 absence closure works deterministically
    for Greenhouse crawls.
    """
    job_repo = InMemoryJobRepository()
    raw_job_repo = InMemoryRawJobRepository()
    crawl_run_repo = InMemoryCrawlRunRepository()
    lifecycle_service = JobLifecycleService(
        job_repo=job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    ingestion_service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        lifecycle_service=lifecycle_service,
    )
    source = make_greenhouse_source()

    # --- Run 1: Complete crawl with jobs A and B ---
    crawl_result_1 = CrawlResultDTO(
        source_id=source.id,
        ats_type="greenhouse",
        jobs=[
            DiscoveredJobDTO(
                external_job_id="A",
                url="https://boards.greenhouse.io/gramgamescareers/jobs/A",
                title="Job A",
                raw_content="{}",
                content_type="application/json",
                metadata={"company": "Gram Games"},
            ),
            DiscoveredJobDTO(
                external_job_id="B",
                url="https://boards.greenhouse.io/gramgamescareers/jobs/B",
                title="Job B",
                raw_content="{}",
                content_type="application/json",
                metadata={"company": "Gram Games"},
            ),
        ],
        raw_payload_count=2,
        warnings=[],
        metadata={},
        is_complete=True,
    )
    run1 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    await crawl_run_repo.save(run1)

    summary1 = await ingestion_service.ingest_crawl_result(
        source, crawl_result_1, crawl_run_id=run1.id
    )
    assert summary1.jobs_created == 2
    assert summary1.jobs_closed == 0

    active_jobs = await job_repo.get_active_jobs_by_source(source.id)
    assert len(active_jobs) == 2

    # --- Run 2: Authoritative crawl with ONLY job A -> Job B absent -> CLOSED ---
    crawl_result_2 = CrawlResultDTO(
        source_id=source.id,
        ats_type="greenhouse",
        jobs=[
            DiscoveredJobDTO(
                external_job_id="A",
                url="https://boards.greenhouse.io/gramgamescareers/jobs/A",
                title="Job A",
                raw_content="{}",
                content_type="application/json",
                metadata={"company": "Gram Games"},
            ),
        ],
        raw_payload_count=1,
        warnings=[],
        metadata={},
        is_complete=True,
    )
    run2 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    await crawl_run_repo.save(run2)

    summary2 = await ingestion_service.ingest_crawl_result(
        source, crawl_result_2, crawl_run_id=run2.id
    )
    assert summary2.jobs_found == 1
    assert summary2.jobs_unchanged == 1
    assert summary2.jobs_closed == 1

    active_jobs_after = await job_repo.get_active_jobs_by_source(source.id)
    assert len(active_jobs_after) == 1
    assert active_jobs_after[0].external_job_id == "A"

    job_b = await job_repo.get_by_source_and_external_id(source.id, "B")
    assert job_b is not None
    assert job_b.status == JobStatus.CLOSED

    # --- Run 3: Incomplete crawl (is_complete=False) -> suppresses absence closure ---
    # Reactivate job B for testing suppression
    job_b.status = JobStatus.ACTIVE
    await job_repo.save(job_b)

    crawl_result_3 = CrawlResultDTO(
        source_id=source.id,
        ats_type="greenhouse",
        jobs=[
            DiscoveredJobDTO(
                external_job_id="A",
                url="https://boards.greenhouse.io/gramgamescareers/jobs/A",
                title="Job A",
                raw_content="{}",
                content_type="application/json",
                metadata={"company": "Gram Games"},
            ),
        ],
        raw_payload_count=1,
        warnings=["pagination_max_pages_reached"],
        metadata={},
        is_complete=False,  # Truncated crawl!
    )
    run3 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    await crawl_run_repo.save(run3)

    summary3 = await ingestion_service.ingest_crawl_result(
        source, crawl_result_3, crawl_run_id=run3.id
    )
    # Because is_complete=False, absence closure MUST NOT run
    assert summary3.jobs_closed == 0
    job_b_check = await job_repo.get_by_source_and_external_id(source.id, "B")
    assert job_b_check is not None
    assert job_b_check.status == JobStatus.ACTIVE  # Remains active!


@pytest.mark.asyncio
async def test_greenhouse_zero_job_safety_guard() -> None:
    """A complete crawl discovering 0 jobs must NOT close active jobs
    (zero-job safety guard).
    """
    job_repo = InMemoryJobRepository()
    raw_job_repo = InMemoryRawJobRepository()
    crawl_run_repo = InMemoryCrawlRunRepository()
    lifecycle_service = JobLifecycleService(
        job_repo=job_repo,
        crawl_run_repo=crawl_run_repo,
    )

    ingestion_service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        lifecycle_service=lifecycle_service,
    )
    source = make_greenhouse_source()

    # Pre-populate active job
    normalizer = JobNormalizer()
    existing_job = normalizer.normalize(
        DiscoveredJobDTO(
            external_job_id="EXISTING",
            url="https://boards.greenhouse.io/gramgamescareers/jobs/EXISTING",
            title="Existing Job",
            raw_content="{}",
            content_type="application/json",
            metadata={"company": "Gram Games"},
        ),
        source,
    )
    await job_repo.save(existing_job)

    # Crawl with 0 jobs returned
    crawl_result_empty = CrawlResultDTO(
        source_id=source.id,
        ats_type="greenhouse",
        jobs=[],
        raw_payload_count=0,
        warnings=[],
        metadata={},
        is_complete=True,
    )
    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=source.id,
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    await crawl_run_repo.save(run)

    summary = await ingestion_service.ingest_crawl_result(
        source, crawl_result_empty, crawl_run_id=run.id
    )
    assert summary.jobs_found == 0
    assert summary.jobs_closed == 0

    active_jobs = await job_repo.get_active_jobs_by_source(source.id)
    assert len(active_jobs) == 1
    assert active_jobs[0].external_job_id == "EXISTING"
    assert active_jobs[0].status == JobStatus.ACTIVE


def test_crawler_orchestrator_contains_no_greenhouse_specific_branches() -> None:
    """Verify CrawlerOrchestrator remains ATS-agnostic with zero greenhouse branches."""
    from pathlib import Path

    orchestrator_path = Path("backend/application/job_discovery/crawler_service.py")
    assert orchestrator_path.exists()

    with open(orchestrator_path, encoding="utf-8") as f:
        content = f.read()

    # Orchestrator must not have "greenhouse" specific branches or mentions
    assert "greenhouse" not in content.lower(), (
        "CrawlerOrchestrator must remain completely ATS-agnostic"
    )
