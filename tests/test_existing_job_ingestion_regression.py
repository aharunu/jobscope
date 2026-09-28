"""Regression tests for SQLAlchemy async existing job ingestion.

Guarantees:
- Newly created Job succeeds on INSERT.
- Existing Job update/unchanged succeeds without MissingGreenlet on UPDATE.
- Server-generated updated_at is accessible immediately after flush.
- first_seen_at is preserved while last_seen_at is touched.
- CrawlRunJob is recorded with action=UNCHANGED.
- error_count remains 0 across consecutive crawls.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.entities import CrawlRun
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.crawl_run import CrawlRunJobModel
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)


@pytest.fixture
async def pg_session():
    """Yield an isolated transactional PostgreSQL session that is always rolled back."""
    engine = create_database_engine()
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    try:
        async with factory() as session:
            # Verify connectivity
            await session.execute(select(1))
            yield session
            await session.rollback()
    except Exception as exc:
        pytest.skip(f"PostgreSQL integration database unavailable: {exc}")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_job_model_eager_defaults_configured() -> None:
    """Verify JobModel inherits eager_defaults=True from TimestampMixin."""
    assert JobModel.__mapper__.eager_defaults is True


@pytest.mark.asyncio
async def test_job_repository_save_update_without_missing_greenlet(
    pg_session: AsyncSession,
) -> None:
    """Verify SQLAlchemyJobRepository.save updates an existing job
    without raising MissingGreenlet.
    """
    source_id = uuid.uuid4()
    source_orm = SourceModel(
        id=source_id,
        name="Regression Test Source",
        company="Regression Co",
        url="https://example.com/regression",
        ats_type="greenhouse",
        active=True,
    )
    pg_session.add(source_orm)
    await pg_session.flush()

    job_repo = SQLAlchemyJobRepository(pg_session)

    # 1. Initial INSERT
    job_id = uuid.uuid4()
    ext_id = f"ext-{uuid.uuid4().hex[:8]}"
    initial_job = Job(
        id=job_id,
        source_id=source_id,
        external_job_id=ext_id,
        canonical_url=f"https://example.com/jobs/{ext_id}",
        company="Regression Co",
        title="Software Engineer",
        description="Initial description",
        content_hash="hash123",
        status=JobStatus.ACTIVE,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
    )

    created_job = await job_repo.save(initial_job)
    assert created_job.id == job_id
    assert created_job.created_at is not None
    assert created_job.updated_at is not None

    # 2. Subsequent UPDATE (simulating touching last_seen_at)
    new_seen_time = datetime.now(UTC) + timedelta(minutes=5)
    created_job.last_seen_at = new_seen_time
    created_job.description = "Updated description"

    # This call previously raised MissingGreenlet because updated_at was expired
    updated_job = await job_repo.save(created_job)

    assert updated_job.id == job_id
    assert updated_job.last_seen_at == new_seen_time
    assert updated_job.updated_at is not None
    assert isinstance(updated_job.updated_at, datetime)


@pytest.mark.asyncio
async def test_consecutive_identical_crawl_pipeline_ingestion(
    pg_session: AsyncSession,
) -> None:
    """End-to-end regression test for consecutive identical Greenhouse crawls.

    Guarantees:
    - Run 1: creates 1 job, 0 unchanged, 0 errors, 1 CrawlRunJob (CREATED).
    - Run 2: finds 1 job, 0 created, 1 unchanged, 0 errors, 1 CrawlRunJob (UNCHANGED).
    - first_seen_at is preserved; last_seen_at is updated.
    - No MissingGreenlet exception occurs.
    """
    source_id = uuid.uuid4()
    source_domain = Source(
        id=source_id,
        name="Good Job Games Regression",
        company="Good Job Games",
        url="https://job-boards.greenhouse.io/goodjobgames",
        ats_type="greenhouse",
        active=True,
    )
    source_orm = SourceModel.from_domain(source_domain)
    pg_session.add(source_orm)
    await pg_session.flush()

    runtime_source = RuntimeSourceDTO.from_domain(source_domain)

    job_repo = SQLAlchemyJobRepository(pg_session)
    raw_job_repo = SQLAlchemyRawJobRepository(pg_session)
    crawl_run_repo = SQLAlchemyCrawlRunRepository(pg_session)

    ingestion_service = JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        normalizer=JobNormalizer(),
    )

    ext_job_id = f"gh-{uuid.uuid4().hex[:8]}"
    discovered = DiscoveredJobDTO(
        external_job_id=ext_job_id,
        url=f"https://job-boards.greenhouse.io/goodjobgames/jobs/{ext_job_id}",
        title="2D Artist, Marketing",
        raw_content="<p>Full job posting html</p>",
        content_type="text/html",
        metadata={
            "company": "Good Job Games",
            "location": "Istanbul, Turkey",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "description": "Full job posting html",
        },
    )

    # --------------------------------------------------------------------------
    # FIRST CRAWL: Initial discovery (CREATED)
    # --------------------------------------------------------------------------
    run_1_id = uuid.uuid4()
    await crawl_run_repo.create_run(
        CrawlRun(
            id=run_1_id,
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
    )

    crawl_1_result = CrawlResultDTO(
        source_id=source_id,
        ats_type="greenhouse",
        jobs=[discovered],
        is_complete=True,
    )

    res_1 = await ingestion_service.ingest_crawl_result(
        source=runtime_source,
        crawl_result=crawl_1_result,
        crawl_run_id=run_1_id,
    )

    assert res_1.status == CrawlStatus.COMPLETED
    assert res_1.jobs_found == 1
    assert res_1.jobs_created == 1
    assert res_1.jobs_updated == 0
    assert res_1.jobs_unchanged == 0
    assert res_1.error_count == 0
    assert len(res_1.errors) == 0

    # Verify CrawlRunJob for run 1
    crj_stmt_1 = select(CrawlRunJobModel).where(
        CrawlRunJobModel.crawl_run_id == run_1_id
    )
    links_1 = (await pg_session.execute(crj_stmt_1)).scalars().all()
    assert len(links_1) == 1
    assert links_1[0].action == CrawlJobAction.CREATED

    # Fetch persisted canonical job
    saved_job = await job_repo.get_by_source_and_external_id(source_id, ext_job_id)
    assert saved_job is not None
    first_seen_at_1 = saved_job.first_seen_at
    last_seen_at_1 = saved_job.last_seen_at
    assert first_seen_at_1 is not None
    assert last_seen_at_1 is not None

    # --------------------------------------------------------------------------
    # SECOND CRAWL: Identical crawl against existing job (UNCHANGED)
    # --------------------------------------------------------------------------
    run_2_id = uuid.uuid4()
    await crawl_run_repo.create_run(
        CrawlRun(
            id=run_2_id,
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
    )

    crawl_2_result = CrawlResultDTO(
        source_id=source_id,
        ats_type="greenhouse",
        jobs=[discovered],
        is_complete=True,
    )

    res_2 = await ingestion_service.ingest_crawl_result(
        source=runtime_source,
        crawl_result=crawl_2_result,
        crawl_run_id=run_2_id,
    )

    # Invariants verification:
    assert res_2.status == CrawlStatus.COMPLETED
    assert res_2.jobs_found == 1
    assert res_2.jobs_created == 0
    assert res_2.jobs_updated == 0
    assert res_2.jobs_unchanged == 1
    assert res_2.jobs_closed == 0
    assert res_2.error_count == 0
    assert len(res_2.errors) == 0

    # Verify CrawlRunJob for run 2
    crj_stmt_2 = select(CrawlRunJobModel).where(
        CrawlRunJobModel.crawl_run_id == run_2_id
    )
    links_2 = (await pg_session.execute(crj_stmt_2)).scalars().all()
    assert len(links_2) == 1
    assert links_2[0].action == CrawlJobAction.UNCHANGED
    assert links_2[0].job_id == saved_job.id

    # Verify timestamp semantics on the Job
    job_after_crawl_2 = await job_repo.get_by_source_and_external_id(
        source_id, ext_job_id
    )
    assert job_after_crawl_2 is not None
    assert job_after_crawl_2.first_seen_at == first_seen_at_1
    assert job_after_crawl_2.last_seen_at >= last_seen_at_1
    assert job_after_crawl_2.updated_at is not None

    # --------------------------------------------------------------------------
    # THIRD CRAWL: Content changed on existing job (UPDATED)
    # --------------------------------------------------------------------------
    discovered_updated = DiscoveredJobDTO(
        external_job_id=ext_job_id,
        url=f"https://job-boards.greenhouse.io/goodjobgames/jobs/{ext_job_id}",
        title="2D Artist, Marketing (Lead)",  # Changed title
        raw_content="<p>Updated content</p>",
        content_type="text/html",
        metadata={
            "company": "Good Job Games",
            "location": "Istanbul, Turkey",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "description": "Updated content",
        },
    )

    run_3_id = uuid.uuid4()
    await crawl_run_repo.create_run(
        CrawlRun(
            id=run_3_id,
            source_id=source_id,
            status=CrawlStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
    )

    crawl_3_result = CrawlResultDTO(
        source_id=source_id,
        ats_type="greenhouse",
        jobs=[discovered_updated],
        is_complete=True,
    )

    res_3 = await ingestion_service.ingest_crawl_result(
        source=runtime_source,
        crawl_result=crawl_3_result,
        crawl_run_id=run_3_id,
    )

    assert res_3.status == CrawlStatus.COMPLETED
    assert res_3.jobs_found == 1
    assert res_3.jobs_created == 0
    assert res_3.jobs_updated == 1
    assert res_3.jobs_unchanged == 0
    assert res_3.jobs_closed == 0
    assert res_3.error_count == 0

    crj_stmt_3 = select(CrawlRunJobModel).where(
        CrawlRunJobModel.crawl_run_id == run_3_id
    )
    links_3 = (await pg_session.execute(crj_stmt_3)).scalars().all()
    assert len(links_3) == 1
    assert links_3[0].action == CrawlJobAction.UPDATED
    assert links_3[0].job_id == saved_job.id
