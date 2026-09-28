"""Regression tests for Job Detail API requirements projection.

Validates:
A. Repository integration: get_job_detail() eager loads Job.requirements from DB.
B. Query service: _to_detail_dto() correctly maps Job.requirements into DTO dicts.
C. API: GET /api/jobs/{job_id} returns populated requirements list in JSON.
D. Existing behavior: Jobs without requirements continue to return requirements=[].
E. Regression: Source metadata projection (source_name, ats_type) is preserved.
F. Async safety: Accessing requirements after session close avoids MissingGreenlet.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.job_processing.query_service import JobQueryService
from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import JobStatus, RequirementLevel, RequirementType
from backend.domain.job.repositories import JobRepository
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
)
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)
from backend.interfaces.api.dependencies.job_processing import (
    get_job_query_service,
)
from backend.interfaces.api.main import create_app

# ==============================================================================
# In-Memory Test Double for API Unit Tests
# ==============================================================================


class _InMemoryJobRepo(JobRepository):
    def __init__(self, jobs: list[Job]) -> None:
        self.jobs: dict[uuid.UUID, Job] = {j.id: j for j in jobs}

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    async def get_by_source_and_external_id(
        self, source_id: uuid.UUID, external_job_id: str
    ) -> Job | None:
        return None

    async def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        return None

    async def save(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    async def save_bulk(self, jobs: list[Job]) -> list[Job]:
        for j in jobs:
            self.jobs[j.id] = j
        return jobs

    async def count(
        self,
        source_id: uuid.UUID | None = None,
        status: JobStatus | None = None,
    ) -> int:
        return len(self.jobs)

    async def get_job_detail(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    async def list_jobs(
        self,
        status: JobStatus | None = None,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
        company: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        search_query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Job]:
        return list(self.jobs.values())[offset : offset + limit]

    async def count_jobs(
        self,
        status: JobStatus | None = None,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
        company: str | None = None,
        location: str | None = None,
        work_mode: str | None = None,
        employment_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        return len(self.jobs)

    async def get_active_jobs_by_source(self, source_id: uuid.UUID) -> list[Job]:
        return [
            j
            for j in self.jobs.values()
            if j.source_id == source_id and j.status == JobStatus.ACTIVE
        ]


# ==============================================================================
# Unit Tests (Query Service & API)
# ==============================================================================


def test_query_service_to_detail_dto_maps_requirements() -> None:
    """Requirement B: Verify _to_detail_dto populates DTO requirements."""
    job_id = uuid.uuid4()
    req1 = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EDUCATION,
        description="B.S. in Computer Science or Mathematics",
        normalized_skill="Computer Science",
        required_level=RequirementLevel.REQUIRED,
        importance="HIGH",
        criticality="BLOCKER",
        evidence="Degree required for this engineering role.",
    )
    req2 = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EXPERIENCE,
        description="5+ years of Python distributed systems experience",
        normalized_skill="5+ years experience",
        required_level=RequirementLevel.REQUIRED,
        importance="HIGH",
        criticality="NORMAL",
        evidence="5+ years experience building cloud services.",
    )
    job = Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/jobs/1",
        company="TechCorp",
        title="Senior Python Backend Engineer",
        description="Job description here",
        content_hash="contenthash123",
        source_name="TechCorp Careers",
        ats_type="greenhouse",
        source_url="https://boards.greenhouse.io/techcorp",
        requirements=[req1, req2],
    )

    dto = JobQueryService._to_detail_dto(job)

    assert len(dto.requirements) == 2
    assert dto.requirements[0]["id"] == str(req1.id)
    assert dto.requirements[0]["type"] == "EDUCATION"
    assert dto.requirements[0]["normalized_skill"] == "Computer Science"
    assert dto.requirements[0]["required_level"] == "REQUIRED"
    assert dto.requirements[0]["importance"] == "HIGH"
    assert dto.requirements[0]["criticality"] == "BLOCKER"

    assert dto.requirements[1]["id"] == str(req2.id)
    assert dto.requirements[1]["type"] == "EXPERIENCE"
    assert dto.requirements[1]["normalized_skill"] == "5+ years experience"


def test_api_get_job_detail_returns_requirements_json() -> None:
    """Requirements C, D, E: Verify GET /api/jobs/{id} serializes requirements
    and preserves source projection, while empty requirements return [].
    """
    job_with_reqs_id = uuid.uuid4()
    job_empty_id = uuid.uuid4()
    source_id = uuid.uuid4()

    req = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_with_reqs_id,
        type=RequirementType.LANGUAGE,
        description="Fluent written and verbal English",
        normalized_skill="English",
        required_level=RequirementLevel.REQUIRED,
        importance="HIGH",
        criticality="NORMAL",
        evidence="English is the working language.",
    )
    job1 = Job(
        id=job_with_reqs_id,
        source_id=source_id,
        canonical_url="https://example.com/jobs/101",
        company="GlobalInc",
        title="Lead Platform Architect",
        description="Platform architect description",
        content_hash="hash101",
        source_name="Global Careers",
        ats_type="lever",
        source_url="https://jobs.lever.co/global",
        requirements=[req],
    )
    job2 = Job(
        id=job_empty_id,
        source_id=source_id,
        canonical_url="https://example.com/jobs/102",
        company="GlobalInc",
        title="Associate Analyst",
        description="Analyst description",
        content_hash="hash102",
        source_name="Global Careers",
        ats_type="lever",
        source_url="https://jobs.lever.co/global",
        requirements=[],
    )

    repo = _InMemoryJobRepo([job1, job2])
    query_service = JobQueryService(job_repo=repo)

    app = create_app()
    app.dependency_overrides[get_job_query_service] = lambda: query_service

    with TestClient(app) as client:
        # C & E: Verify Job with requirements
        resp1 = client.get(f"/api/jobs/{job_with_reqs_id}")
        assert resp1.status_code == status.HTTP_200_OK
        data1 = resp1.json()
        assert data1["id"] == str(job_with_reqs_id)
        assert data1["source_name"] == "Global Careers"
        assert data1["ats_type"] == "lever"
        assert data1["source_url"] == "https://jobs.lever.co/global"
        assert len(data1["requirements"]) == 1
        assert data1["requirements"][0]["type"] == "LANGUAGE"
        assert data1["requirements"][0]["normalized_skill"] == "English"
        assert data1["requirements"][0]["required_level"] == "REQUIRED"

        # D: Verify Job without requirements returns requirements=[]
        resp2 = client.get(f"/api/jobs/{job_empty_id}")
        assert resp2.status_code == status.HTTP_200_OK
        data2 = resp2.json()
        assert data2["id"] == str(job_empty_id)
        assert data2["requirements"] == []


# ==============================================================================
# Real PostgreSQL Integration Tests (Requirements A & F)
# ==============================================================================


@pytest.fixture
async def pg_session_factory():
    """Yield a PostgreSQL async sessionmaker, cleaning up test data."""
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

    yield factory, created_source_ids

    # Cleanup test created sources, jobs, and requirements
    if created_source_ids:
        async with factory() as session:
            for sid in created_source_ids:
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
                    SourceModel.__table__.delete().where(SourceModel.id == sid)
                )
            await session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_repository_get_job_detail_eager_loads_requirements_postgres(
    pg_session_factory,
) -> None:
    """Requirements A & F: Real PostgreSQL integration test verifying
    get_job_detail eager loads Job.requirements and does not raise
    MissingGreenlet outside session.
    """
    factory, created_source_ids = pg_session_factory
    source_id = uuid.uuid4()
    job_id = uuid.uuid4()
    req1_id = uuid.uuid4()
    req2_id = uuid.uuid4()
    created_source_ids.append(source_id)

    # 1. Insert Source, Job, and 2 JobRequirements in PostgreSQL
    async with factory() as session:
        src = SourceModel(
            id=source_id,
            name="Integration Test Board",
            url="https://boards.greenhouse.io/itest",
            ats_type="greenhouse",
            company="TestCorp",
            country="US",
            active=True,
        )
        session.add(src)
        await session.flush()

        job = JobModel(
            id=job_id,
            source_id=source_id,
            canonical_url=f"https://example.com/jobs/{job_id}",
            company="TestCorp",
            title="Senior Backend Engineer",
            description="Integration test job description",
            content_hash="testhash999",
            status=JobStatus.ACTIVE,
            first_seen_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        session.add(job)
        await session.flush()

        req1 = JobRequirementModel(
            id=req1_id,
            job_id=job_id,
            type=RequirementType.EDUCATION,
            description="B.S. in Computer Science or Mathematics",
            normalized_skill="Computer Science",
            required_level=RequirementLevel.REQUIRED,
            importance="HIGH",
            criticality="BLOCKER",
            evidence="Degree required.",
        )
        req2 = JobRequirementModel(
            id=req2_id,
            job_id=job_id,
            type=RequirementType.EXPERIENCE,
            description="5+ years experience with distributed systems",
            normalized_skill="5+ years experience",
            required_level=RequirementLevel.REQUIRED,
            importance="HIGH",
            criticality="NORMAL",
            evidence="5+ years experience.",
        )
        session.add_all([req1, req2])
        await session.commit()

    # 2. Retrieve job via SQLAlchemyJobRepository.get_job_detail in a fresh session
    async with factory() as session:
        repo = SQLAlchemyJobRepository(session)
        domain_job = await repo.get_job_detail(job_id)

    # 3. Assertions (verified AFTER session exit to guarantee Async Safety)
    assert domain_job is not None
    assert domain_job.id == job_id
    assert domain_job.source_name == "Integration Test Board"
    assert domain_job.ats_type == "greenhouse"
    assert domain_job.source_url == "https://boards.greenhouse.io/itest"

    # Verify requirements are eager loaded and properly mapped to domain entities
    assert len(domain_job.requirements) == 2
    req_skills = {r.normalized_skill for r in domain_job.requirements}
    assert "Computer Science" in req_skills
    assert "5+ years experience" in req_skills

    req_types = {r.type for r in domain_job.requirements}
    assert RequirementType.EDUCATION in req_types
    assert RequirementType.EXPERIENCE in req_types
