"""Regression tests for production requirement extraction wiring and HTML parsing.

Guarantees:
1. DeterministicRequirementExtractor parses complex Greenhouse/OKX-style HTML
   descriptions without regex failure.
2. SQLAlchemyCrawlPersistenceManager.execute_ingestion wires requirement
   extraction into the production transaction.
3. Newly CREATED jobs persist structured job_requirements atomically to PostgreSQL.
4. UPDATED jobs atomically replace job_requirements in PostgreSQL.
5. UNCHANGED jobs preserve existing job_requirements without re-extracting.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus, RequirementLevel, RequirementType
from backend.infrastructure.database.crawl_persistence import (
    SQLAlchemyCrawlPersistenceManager,
)
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.crawl_run import CrawlRunModel
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
)
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)


@pytest.fixture
async def pg_persistence_manager():
    """Yield a real PostgreSQL-backed SQLAlchemyCrawlPersistenceManager,
    cleaning up any test-created sources/jobs on completion.
    """
    engine = create_database_engine()
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    created_source_ids: list[uuid.UUID] = []

    try:
        async with factory() as session:
            await session.execute(select(1))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"PostgreSQL database unavailable: {exc}")

    manager = SQLAlchemyCrawlPersistenceManager(session_factory=factory)
    yield manager, factory, created_source_ids

    # Cleanup created sources and cascaded crawl_runs/jobs/requirements
    if created_source_ids:
        async with factory() as session:
            for sid in created_source_ids:
                # Delete jobs manually or via cascade
                j_stmt = select(JobModel.id).where(JobModel.source_id == sid)
                job_ids = (await session.execute(j_stmt)).scalars().all()
                if job_ids:
                    await session.execute(
                        JobRequirementModel.__table__.delete().where(
                            JobRequirementModel.job_id.in_(job_ids)
                        )
                    )
                    await session.execute(
                        JobModel.__table__.delete().where(JobModel.id.in_(job_ids))
                    )
                await session.execute(
                    CrawlRunModel.__table__.delete().where(
                        CrawlRunModel.source_id == sid
                    )
                )
                await session.execute(
                    SourceModel.__table__.delete().where(SourceModel.id == sid)
                )
            await session.commit()

    await engine.dispose()


# ==============================================================================
# 1. Real-World Greenhouse HTML Extraction (Unit Test - No DB)
# ==============================================================================


def test_real_world_okx_greenhouse_html_extraction() -> None:
    """Verify DeterministicRequirementExtractor parses complex nested HTML
    content structure matching real Greenhouse postings (such as OKX).
    """
    okx_html = """
    <div class="ace-line ace-line old-record-id-doxuseysYUio6Qia64JLLAwE7dh">
      <div data-page-id="doxusokjWsaOkSCIjzixAfRM3sd">
        <h2>About the Team</h2>
        <p>We are looking for product leaders to drive trading.</p>
        <h2>What You'll Need</h2>
        <div class="ace-line">
          • A technical, engineering, finance, or mathematics background.
        </div>
        <div class="ace-line">
          • 5-7+ years of product management experience, complex products.
        </div>
        <div class="ace-line">
          • Excellent written and spoken English. Working language English.
        </div>
        <h2>Nice to Have</h2>
        <div class="ace-line">
          • Experience with Python, SQL, and big data architectures.
        </div>
      </div>
    </div>
    """
    job = Job(
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/okx/1",
        company="OKX",
        title="Senior/Lead Product Manager - Professional Trading Tools & Experience",
        description=okx_html,
        content_hash="testhash123",
        status=JobStatus.ACTIVE,
    )

    extractor = DeterministicRequirementExtractor()
    requirements = extractor.extract(job)

    skills = {r.normalized_skill for r in requirements}
    types = {r.type for r in requirements}

    assert RequirementType.EDUCATION in types
    assert RequirementType.EXPERIENCE in types
    assert RequirementType.LANGUAGE in types

    assert "Mathematics" in skills
    assert "English" in skills
    assert "5-7+ years experience" in skills

    # Verify requirements in "What You'll Need" section are marked REQUIRED
    math_req = next(r for r in requirements if r.normalized_skill == "Mathematics")
    assert math_req.required_level == RequirementLevel.REQUIRED
    assert math_req.importance == "HIGH"

    eng_req = next(r for r in requirements if r.normalized_skill == "English")
    assert eng_req.required_level == RequirementLevel.REQUIRED


# ==============================================================================
# 2. Production Runtime Wiring: CREATED Job Persistence
# ==============================================================================


@pytest.mark.asyncio
async def test_execute_ingestion_created_job_persists_requirements(
    pg_persistence_manager,
) -> None:
    """Verify SQLAlchemyCrawlPersistenceManager.execute_ingestion persists
    structured job_requirements to PostgreSQL for newly CREATED jobs.
    """
    manager, factory, created_source_ids = pg_persistence_manager

    source_id = uuid.uuid4()
    created_source_ids.append(source_id)

    async with factory() as session:
        src = SourceModel(
            id=source_id,
            name="OKX Production Ingestion Test",
            company="OKX",
            url="https://job-boards.greenhouse.io/okx",
            ats_type="greenhouse",
            active=True,
        )
        session.add(src)
        await session.commit()

    run_id = await manager.create_initial_run(source_id)
    runtime_source = RuntimeSourceDTO(
        id=source_id,
        name="OKX Production Ingestion Test",
        url="https://job-boards.greenhouse.io/okx",
        ats_type="greenhouse",
        company="OKX",
        country="US",
        adapter_config={},
        pagination_config={},
        endpoint_config={},
        rate_limit_config={},
        metadata={},
    )

    ext_job_id = f"okx-{uuid.uuid4().hex[:8]}"
    discovered = DiscoveredJobDTO(
        external_job_id=ext_job_id,
        url=f"https://job-boards.greenhouse.io/okx/jobs/{ext_job_id}",
        title="Senior Backend Engineer",
        raw_content="<p>Full raw posting</p>",
        content_type="text/html",
        metadata={
            "company": "OKX",
            "description": (
                "<div><h2>Requirements</h2>"
                "<ul>"
                "<li>5+ years experience building distributed systems in Python.</li>"
                "<li>Strong knowledge of PostgreSQL and Docker.</li>"
                "<li>Bachelor's degree in Computer Science.</li>"
                "</ul></div>"
            ),
        },
    )

    crawl_result = CrawlResultDTO(
        source_id=source_id,
        ats_type="greenhouse",
        jobs=[discovered],
        is_complete=True,
    )

    # Execute production ingestion
    res = await manager.execute_ingestion(
        source=runtime_source,
        crawl_result=crawl_result,
        crawl_run_id=run_id,
    )

    assert res.status == CrawlStatus.COMPLETED
    assert res.jobs_created == 1
    assert res.error_count == 0

    # Query PostgreSQL to verify requirements were committed
    async with factory() as session:
        job_stmt = select(JobModel).where(
            JobModel.source_id == source_id,
            JobModel.external_job_id == ext_job_id,
        )
        job_orm = (await session.execute(job_stmt)).scalars().first()
        assert job_orm is not None

        req_stmt = select(JobRequirementModel).where(
            JobRequirementModel.job_id == job_orm.id
        )
        req_rows = (await session.execute(req_stmt)).scalars().all()

        assert len(req_rows) >= 3
        skills = {r.normalized_skill for r in req_rows}
        assert "Python" in skills
        assert "PostgreSQL" in skills
        assert "Computer Science" in skills


# ==============================================================================
# 3. Production Runtime Wiring: UPDATED & UNCHANGED Job Persistence
# ==============================================================================


@pytest.mark.asyncio
async def test_execute_ingestion_updated_and_unchanged_requirements(
    pg_persistence_manager,
) -> None:
    """Verify:
    1. UPDATED jobs re-extract and atomically replace job_requirements.
    2. UNCHANGED jobs preserve requirements without modifying them.
    """
    manager, factory, created_source_ids = pg_persistence_manager

    source_id = uuid.uuid4()
    created_source_ids.append(source_id)

    async with factory() as session:
        src = SourceModel(
            id=source_id,
            name="OKX Lifecycle Re-extraction Test",
            company="OKX",
            url="https://job-boards.greenhouse.io/okx",
            ats_type="greenhouse",
            active=True,
        )
        session.add(src)
        await session.commit()

    runtime_source = RuntimeSourceDTO(
        id=source_id,
        name="OKX Lifecycle Re-extraction Test",
        url="https://job-boards.greenhouse.io/okx",
        ats_type="greenhouse",
        company="OKX",
        country="US",
        adapter_config={},
        pagination_config={},
        endpoint_config={},
        rate_limit_config={},
        metadata={},
    )

    ext_job_id = f"okx-lifecycle-{uuid.uuid4().hex[:8]}"

    # --- Step 1: Initial Crawl ---
    run_1_id = await manager.create_initial_run(source_id)
    job_v1 = DiscoveredJobDTO(
        external_job_id=ext_job_id,
        url=f"https://job-boards.greenhouse.io/okx/jobs/{ext_job_id}",
        title="Software Engineer",
        raw_content="<p>v1</p>",
        content_type="text/html",
        metadata={
            "description": (
                "<h2>Requirements</h2><p>Must have 3+ years experience with Python.</p>"
            ),
        },
    )
    res_1 = await manager.execute_ingestion(
        source=runtime_source,
        crawl_result=CrawlResultDTO(
            source_id=source_id, ats_type="greenhouse", jobs=[job_v1]
        ),
        crawl_run_id=run_1_id,
    )
    assert res_1.jobs_created == 1

    async with factory() as session:
        job_orm = (
            await session.execute(
                select(JobModel).where(
                    JobModel.source_id == source_id,
                    JobModel.external_job_id == ext_job_id,
                )
            )
        ).scalar_one()
        v1_reqs = (
            (
                await session.execute(
                    select(JobRequirementModel).where(
                        JobRequirementModel.job_id == job_orm.id
                    )
                )
            )
            .scalars()
            .all()
        )
        v1_skills = {r.normalized_skill for r in v1_reqs}
        assert "Python" in v1_skills
        assert "Go" not in v1_skills

    # --- Step 2: Identical Crawl (UNCHANGED) ---
    run_2_id = await manager.create_initial_run(source_id)
    res_2 = await manager.execute_ingestion(
        source=runtime_source,
        crawl_result=CrawlResultDTO(
            source_id=source_id, ats_type="greenhouse", jobs=[job_v1]
        ),
        crawl_run_id=run_2_id,
    )
    assert res_2.jobs_unchanged == 1
    assert res_2.jobs_updated == 0

    # Ensure requirements were untouched
    async with factory() as session:
        v2_reqs = (
            (
                await session.execute(
                    select(JobRequirementModel).where(
                        JobRequirementModel.job_id == job_orm.id
                    )
                )
            )
            .scalars()
            .all()
        )
        v2_ids = {r.id for r in v2_reqs}
        v1_ids = {r.id for r in v1_reqs}
        assert v2_ids == v1_ids  # IDs preserved without deletion/re-insertion

    # --- Step 3: Content Change Crawl (UPDATED) ---
    run_3_id = await manager.create_initial_run(source_id)
    job_v3 = DiscoveredJobDTO(
        external_job_id=ext_job_id,
        url=f"https://job-boards.greenhouse.io/okx/jobs/{ext_job_id}",
        title="Lead Software Engineer",  # Changed title
        raw_content="<p>v3</p>",
        content_type="text/html",
        metadata={
            "description": (
                "<h2>Requirements</h2>"
                "<p>Must have 5+ years experience with Docker and Kubernetes.</p>"
            ),
        },
    )
    res_3 = await manager.execute_ingestion(
        source=runtime_source,
        crawl_result=CrawlResultDTO(
            source_id=source_id, ats_type="greenhouse", jobs=[job_v3]
        ),
        crawl_run_id=run_3_id,
    )
    assert res_3.jobs_updated == 1

    # Ensure requirements were re-extracted and atomically replaced
    async with factory() as session:
        v3_reqs = (
            (
                await session.execute(
                    select(JobRequirementModel).where(
                        JobRequirementModel.job_id == job_orm.id
                    )
                )
            )
            .scalars()
            .all()
        )
        v3_skills = {r.normalized_skill for r in v3_reqs}
        assert "Docker" in v3_skills
        assert "Kubernetes" in v3_skills
        assert "Python" not in v3_skills
