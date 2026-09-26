"""API contract and endpoint integration tests for canonical Job routes.

Endpoints under test:
- GET /api/jobs
- GET /api/jobs/{job_id}
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.application.job_processing.query_service import JobQueryService
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository
from backend.interfaces.api.dependencies.job_processing import get_job_query_service
from backend.interfaces.api.main import create_app


class InMemoryJobRepository(JobRepository):
    """In-memory test double for JobRepository."""

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self.jobs: dict[uuid.UUID, Job] = {j.id: j for j in (jobs or [])}

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
        return len(
            [
                j
                for j in self.jobs.values()
                if (source_id is None or j.source_id == source_id)
                and (status is None or j.status == status)
            ]
        )

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
        matching = list(self.jobs.values())
        if status is not None:
            matching = [j for j in matching if j.status == status]
        if source_id is not None:
            matching = [j for j in matching if j.source_id == source_id]
        if ats_type is not None:
            matching = [j for j in matching if j.ats_type == ats_type]
        if company is not None:
            matching = [j for j in matching if j.company == company]
        if location is not None:
            matching = [j for j in matching if j.location == location]
        if work_mode is not None:
            matching = [j for j in matching if j.work_mode == work_mode]
        if employment_type is not None:
            matching = [j for j in matching if j.employment_type == employment_type]
        if search_query is not None:
            q_lower = search_query.lower()
            matching = [
                j
                for j in matching
                if q_lower in j.title.lower() or q_lower in j.company.lower()
            ]

        epoch = datetime(1970, 1, 1, tzinfo=UTC)
        matching.sort(
            key=lambda j: (j.first_seen_at or epoch, j.id),
            reverse=True,
        )
        return matching[offset : offset + limit]

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
        jobs = await self.list_jobs(
            status=status,
            source_id=source_id,
            ats_type=ats_type,
            company=company,
            location=location,
            work_mode=work_mode,
            employment_type=employment_type,
            search_query=search_query,
            limit=999999,
            offset=0,
        )
        return len(jobs)


@pytest.fixture
def job_fixture_data() -> tuple[list[Job], uuid.UUID, uuid.UUID]:
    source1_id = uuid.uuid4()
    source2_id = uuid.uuid4()
    now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)

    job1 = Job(
        id=uuid.uuid4(),
        source_id=source1_id,
        external_job_id="lever-001",
        canonical_url="https://jobs.lever.co/acme/001",
        company="Acme Corp",
        title="Senior Python Backend Engineer",
        description="Build high-performance Python services.",
        responsibilities="Design APIs and optimize SQL queries.",
        location="Remote",
        work_mode="Remote",
        employment_type="Full-time",
        salary="$160,000 - $180,000",
        published_at=now - timedelta(days=2),
        first_seen_at=now - timedelta(days=2),
        last_seen_at=now,
        closed_at=None,
        status=JobStatus.ACTIVE,
        content_hash="hash_001",
        created_at=now - timedelta(days=2),
        updated_at=now,
        source_name="Acme Lever Board",
        ats_type="lever",
        source_url="https://jobs.lever.co/acme",
    )

    job2 = Job(
        id=uuid.uuid4(),
        source_id=source1_id,
        external_job_id="lever-002",
        canonical_url="https://jobs.lever.co/acme/002",
        company="Acme Corp",
        title="Frontend React Specialist",
        description="Craft modern user interfaces.",
        responsibilities="Build component libraries.",
        location="San Francisco, CA",
        work_mode="Hybrid",
        employment_type="Full-time",
        salary="$140,000 - $160,000",
        published_at=now - timedelta(days=5),
        first_seen_at=now - timedelta(days=5),
        last_seen_at=now - timedelta(days=1),
        closed_at=now - timedelta(days=1),
        status=JobStatus.CLOSED,
        content_hash="hash_002",
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=1),
        source_name="Acme Lever Board",
        ats_type="lever",
        source_url="https://jobs.lever.co/acme",
    )

    job3 = Job(
        id=uuid.uuid4(),
        source_id=source2_id,
        external_job_id="green-101",
        canonical_url="https://boards.greenhouse.io/globex/101",
        company="Globex Corporation",
        title="Data Engineer",
        description="Design data pipelines with Spark and Airflow.",
        responsibilities="Maintain warehouse infrastructure.",
        location="Berlin, Germany",
        work_mode="On-site",
        employment_type="Contract",
        salary="EUR 80,000 - 95,000",
        published_at=now - timedelta(hours=12),
        first_seen_at=now - timedelta(hours=12),
        last_seen_at=now,
        closed_at=None,
        status=JobStatus.ACTIVE,
        content_hash="hash_003",
        created_at=now - timedelta(hours=12),
        updated_at=now,
        source_name="Globex Greenhouse Board",
        ats_type="greenhouse",
        source_url="https://boards.greenhouse.io/globex",
    )

    return [job1, job2, job3], source1_id, source2_id


@pytest.fixture
def repo(
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> InMemoryJobRepository:
    jobs, _, _ = job_fixture_data
    return InMemoryJobRepository(jobs=jobs)


@pytest.fixture
def client(repo: InMemoryJobRepository) -> TestClient:
    app = create_app()
    service = JobQueryService(job_repo=repo)
    app.dependency_overrides[get_job_query_service] = lambda: service
    return TestClient(app)


# ==============================================================================
# GET /api/jobs Endpoint Tests
# ==============================================================================


def test_list_jobs_default_success(
    client: TestClient,
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> None:
    """Verify listing jobs returns 200 OK with jobs, total, limit, offset."""
    jobs, _, _ = job_fixture_data
    resp = client.get("/api/jobs")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert "jobs" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == len(jobs)
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["jobs"]) == len(jobs)


def test_list_jobs_status_filter(client: TestClient) -> None:
    """Verify filtering by status=ACTIVE and status=CLOSED."""
    resp_active = client.get("/api/jobs?status=ACTIVE")
    assert resp_active.status_code == status.HTTP_200_OK
    data_active = resp_active.json()
    assert data_active["total"] == 2
    for j in data_active["jobs"]:
        assert j["status"] == "ACTIVE"

    resp_closed = client.get("/api/jobs?status=CLOSED")
    assert resp_closed.status_code == status.HTTP_200_OK
    data_closed = resp_closed.json()
    assert data_closed["total"] == 1
    assert data_closed["jobs"][0]["status"] == "CLOSED"


def test_list_jobs_source_id_filter(
    client: TestClient,
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> None:
    """Verify filtering by source_id."""
    _, source1_id, source2_id = job_fixture_data
    resp = client.get(f"/api/jobs?source_id={source1_id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 2
    for j in data["jobs"]:
        assert j["source_id"] == str(source1_id)

    resp2 = client.get(f"/api/jobs?source_id={source2_id}")
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["total"] == 1


def test_list_jobs_ats_type_filter(client: TestClient) -> None:
    """Verify filtering by ATS platform type."""
    resp = client.get("/api/jobs?ats_type=lever")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 2
    for j in data["jobs"]:
        assert j["ats_type"] == "lever"


def test_list_jobs_company_filter(client: TestClient) -> None:
    """Verify filtering by company name."""
    resp = client.get("/api/jobs?company=Globex Corporation")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["company"] == "Globex Corporation"


def test_list_jobs_location_filter(client: TestClient) -> None:
    """Verify filtering by location."""
    resp = client.get("/api/jobs?location=Berlin, Germany")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["location"] == "Berlin, Germany"


def test_list_jobs_work_mode_filter(client: TestClient) -> None:
    """Verify filtering by work_mode."""
    resp = client.get("/api/jobs?work_mode=Remote")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["work_mode"] == "Remote"


def test_list_jobs_employment_type_filter(client: TestClient) -> None:
    """Verify filtering by employment_type."""
    resp = client.get("/api/jobs?employment_type=Contract")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["employment_type"] == "Contract"


def test_list_jobs_search_query_title(client: TestClient) -> None:
    """Verify substring search matching in title."""
    resp = client.get("/api/jobs?q=Python")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert "Python" in data["jobs"][0]["title"]


def test_list_jobs_search_query_company(client: TestClient) -> None:
    """Verify substring search matching in company."""
    resp = client.get("/api/jobs?q=globex")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["company"] == "Globex Corporation"


def test_list_jobs_combined_filters(
    client: TestClient,
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> None:
    """Verify combining multiple filters together."""
    _, source1_id, _ = job_fixture_data
    resp = client.get(
        f"/api/jobs?source_id={source1_id}&status=ACTIVE&work_mode=Remote&q=Senior"
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["total"] == 1
    assert data["jobs"][0]["title"] == "Senior Python Backend Engineer"


def test_list_jobs_pagination_bounds(client: TestClient) -> None:
    """Verify valid limit and offset pagination."""
    resp = client.get("/api/jobs?limit=1&offset=1")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert len(data["jobs"]) == 1


@pytest.mark.parametrize("invalid_limit", [0, 101, -1])
def test_list_jobs_invalid_limit_returns_422(
    client: TestClient, invalid_limit: int
) -> None:
    """Verify limit < 1 or limit > 100 returns HTTP 422."""
    resp = client.get(f"/api/jobs?limit={invalid_limit}")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_jobs_invalid_offset_returns_422(client: TestClient) -> None:
    """Verify offset < 0 returns HTTP 422."""
    resp = client.get("/api/jobs?offset=-1")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# GET /api/jobs/{job_id} Endpoint Tests
# ==============================================================================


def test_get_job_detail_success(
    client: TestClient,
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> None:
    """Verify retrieving an individual job by ID returns 200 OK with full detail."""
    jobs, _, _ = job_fixture_data
    target = jobs[0]
    resp = client.get(f"/api/jobs/{target.id}")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["id"] == str(target.id)
    assert data["title"] == target.title
    assert data["company"] == target.company
    assert data["description"] == target.description
    assert data["responsibilities"] == target.responsibilities
    assert data["content_hash"] == target.content_hash
    assert data["source_name"] == "Acme Lever Board"
    assert data["ats_type"] == "lever"
    assert data["source_url"] == "https://jobs.lever.co/acme"
    assert "requirements" in data


def test_get_job_detail_not_found(client: TestClient) -> None:
    """Verify valid but nonexistent UUID returns 404."""
    nonexistent_id = uuid.uuid4()
    resp = client.get(f"/api/jobs/{nonexistent_id}")
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_get_job_detail_malformed_uuid(client: TestClient) -> None:
    """Verify malformed UUID string returns 422."""
    resp = client.get("/api/jobs/not-a-valid-uuid")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# Security & Hygiene Tests: Zero Source Configuration Leakage
# ==============================================================================

FORBIDDEN_SOURCE_CONFIG_KEYS = [
    "adapter_config",
    "pagination_config",
    "endpoint_config",
    "rate_limit_config",
    "metadata",
]


def test_security_zero_source_configuration_leakage_in_list(
    client: TestClient,
) -> None:
    """Verify GET /api/jobs never leaks internal/secret Source configuration."""
    resp = client.get("/api/jobs")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    for job in data["jobs"]:
        for forbidden in FORBIDDEN_SOURCE_CONFIG_KEYS:
            assert forbidden not in job, (
                f"Security leakage: '{forbidden}' found in job summary response!"
            )


def test_security_zero_source_configuration_leakage_in_detail(
    client: TestClient,
    job_fixture_data: tuple[list[Job], uuid.UUID, uuid.UUID],
) -> None:
    """Verify GET /api/jobs/{id} never leaks internal/secret Source configuration."""
    jobs, _, _ = job_fixture_data
    target = jobs[0]
    resp = client.get(f"/api/jobs/{target.id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    for forbidden in FORBIDDEN_SOURCE_CONFIG_KEYS:
        assert forbidden not in data, (
            f"Security leakage: '{forbidden}' found in job detail response!"
        )
