"""API contract and endpoint integration tests for crawl history observability routes.

Endpoints under test:
- GET /api/crawl/runs
- GET /api/crawl/runs/{crawl_run_id}
- GET /api/crawl/runs/{crawl_run_id}/jobs
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.application.job_discovery.history_service import CrawlHistoryService
from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.interfaces.api.dependencies.crawler import get_crawl_history_service
from backend.interfaces.api.main import create_app


class InMemoryCrawlRunRepository(CrawlRunRepository):
    """In-memory test double for CrawlRunRepository."""

    def __init__(
        self,
        runs: list[CrawlRun] | None = None,
        jobs: list[CrawlRunJob] | None = None,
    ) -> None:
        self.runs: dict[uuid.UUID, CrawlRun] = {r.id: r for r in (runs or [])}
        self.jobs: list[CrawlRunJob] = list(jobs or [])

    async def create_run(self, run: CrawlRun) -> CrawlRun:
        self.runs[run.id] = run
        return run

    async def update_run(self, run: CrawlRun) -> CrawlRun:
        self.runs[run.id] = run
        return run

    async def get_by_id(self, run_id: uuid.UUID) -> CrawlRun | None:
        return self.runs.get(run_id)

    async def get_run_detail(self, run_id: uuid.UUID) -> CrawlRun | None:
        return self.runs.get(run_id)

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        matching = [r for r in self.runs.values() if r.source_id == source_id]
        if not matching:
            return None
        matching.sort(key=lambda r: r.started_at, reverse=True)
        return matching[0]

    async def list_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRun]:
        matching = list(self.runs.values())
        if source_id is not None:
            matching = [r for r in matching if r.source_id == source_id]
        if status is not None:
            matching = [r for r in matching if r.status == status]
        if ats_type is not None:
            matching = [r for r in matching if r.ats_type == ats_type]
        if date_from is not None:
            matching = [r for r in matching if r.created_at >= date_from]
        if date_to is not None:
            matching = [r for r in matching if r.created_at < date_to]

        matching.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        return matching[offset : offset + limit]

    async def count_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        runs = await self.list_runs(
            source_id=source_id,
            status=status,
            ats_type=ats_type,
            date_from=date_from,
            date_to=date_to,
            limit=999999,
            offset=0,
        )
        return len(runs)

    async def record_job_action(
        self,
        run_id: uuid.UUID,
        job_id: uuid.UUID,
        action: CrawlJobAction,
    ) -> None:
        self.jobs.append(CrawlRunJob(crawl_run_id=run_id, job_id=job_id, action=action))

    async def record_job_actions(self, links: list[CrawlRunJob]) -> None:
        self.jobs.extend(links)

    async def list_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRunJob]:
        matching = [j for j in self.jobs if j.crawl_run_id == run_id]
        if action is not None:
            matching = [j for j in matching if j.action == action]
        matching.sort(key=lambda j: (j.action.value, j.title or "", str(j.job_id)))
        return matching[offset : offset + limit]

    async def count_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
    ) -> int:
        jobs = await self.list_run_jobs(
            run_id=run_id, action=action, limit=999999, offset=0
        )
        return len(jobs)


@pytest.fixture
def run_fixture_data() -> tuple[
    list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID
]:
    source1_id = uuid.uuid4()
    source2_id = uuid.uuid4()

    now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)

    run1 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source1_id,
        status=CrawlStatus.COMPLETED,
        started_at=now - timedelta(minutes=5),
        finished_at=now - timedelta(minutes=4),
        created_at=now - timedelta(minutes=5),
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=1,
        error_count=0,
        source_name="Acme Corp Lever",
        ats_type="lever",
    )

    run2 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source1_id,
        status=CrawlStatus.RUNNING,
        started_at=now - timedelta(minutes=1),
        finished_at=None,
        created_at=now - timedelta(minutes=1),
        jobs_found=0,
        jobs_created=0,
        jobs_updated=0,
        jobs_closed=0,
        error_count=0,
        source_name="Acme Corp Lever",
        ats_type="lever",
    )

    run3 = CrawlRun(
        id=uuid.uuid4(),
        source_id=source2_id,
        status=CrawlStatus.FAILED,
        started_at=now - timedelta(days=2),
        finished_at=now - timedelta(days=2) + timedelta(seconds=12),
        created_at=now - timedelta(days=2),
        jobs_found=0,
        jobs_created=0,
        jobs_updated=0,
        jobs_closed=0,
        error_count=1,
        source_name="Beta Greenhouse",
        ats_type="greenhouse",
    )

    job1_id = uuid.uuid4()
    job2_id = uuid.uuid4()

    link1 = CrawlRunJob(
        crawl_run_id=run1.id,
        job_id=job1_id,
        action=CrawlJobAction.CREATED,
        canonical_url="https://jobs.lever.co/acme/1",
        title="Software Engineer",
        company="Acme Corp",
        location="Remote",
        job_status="ACTIVE",
        first_seen_at=now - timedelta(minutes=5),
        last_seen_at=now - timedelta(minutes=5),
    )

    link2 = CrawlRunJob(
        crawl_run_id=run1.id,
        job_id=job2_id,
        action=CrawlJobAction.UPDATED,
        canonical_url="https://jobs.lever.co/acme/2",
        title="Product Manager",
        company="Acme Corp",
        location="New York",
        job_status="ACTIVE",
        first_seen_at=now - timedelta(days=5),
        last_seen_at=now - timedelta(minutes=5),
    )

    return [run1, run2, run3], [link1, link2], source1_id, source2_id


@pytest.fixture
def repo(
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> InMemoryCrawlRunRepository:
    runs, jobs, _, _ = run_fixture_data
    return InMemoryCrawlRunRepository(runs=runs, jobs=jobs)


@pytest.fixture
def client(repo: InMemoryCrawlRunRepository) -> TestClient:
    app = create_app()
    service = CrawlHistoryService(repository=repo)
    app.dependency_overrides[get_crawl_history_service] = lambda: service
    return TestClient(app)


# ==============================================================================
# GET /api/crawl/runs Tests
# ==============================================================================


def test_list_runs_default(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify listing runs with default parameters returns paginated list."""
    runs, _, _, _ = run_fixture_data
    resp = client.get("/api/crawl/runs")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == len(runs)
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == len(runs)


def test_list_runs_empty(client: TestClient, repo: InMemoryCrawlRunRepository) -> None:
    """Verify empty run store returns empty list with 200 OK."""
    repo.runs.clear()
    resp = client.get("/api/crawl/runs")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_runs_filter_by_source_id(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify source_id filtering."""
    _, _, source1_id, _ = run_fixture_data
    resp = client.get(f"/api/crawl/runs?source_id={source1_id}")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["source_id"] == str(source1_id)


def test_list_runs_filter_by_status(client: TestClient) -> None:
    """Verify status filtering."""
    resp = client.get("/api/crawl/runs?status=COMPLETED")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "COMPLETED"


def test_list_runs_filter_by_ats_type(client: TestClient) -> None:
    """Verify ats_type filtering."""
    resp = client.get("/api/crawl/runs?ats_type=greenhouse")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["ats_type"] == "greenhouse"


def test_list_runs_filter_by_date_range(client: TestClient) -> None:
    """Verify date_from and date_to filtering."""
    d_from = "2026-09-26T00:00:00Z"
    d_to = "2026-09-26T23:59:59Z"
    resp = client.get(f"/api/crawl/runs?date_from={d_from}&date_to={d_to}")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    # run1 and run2 were created on 2026-09-26, run3 was 2 days prior
    assert data["total"] == 2


def test_list_runs_duration_and_jobs_unchanged(client: TestClient) -> None:
    """Verify duration derivation and jobs_unchanged calculation."""
    resp = client.get("/api/crawl/runs?status=COMPLETED")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    run = data["items"][0]
    # started 5m ago, finished 4m ago -> 1m = 60,000 ms
    assert run["duration_ms"] == 60000
    # 10 jobs found - 6 created - 2 updated - 0 error = 2
    # Note: jobs_closed is not subtracted from jobs_unchanged
    assert run["jobs_unchanged"] == 2


def test_list_runs_jobs_unchanged_subtracts_error_count(
    client: TestClient, repo: InMemoryCrawlRunRepository
) -> None:
    """Verify jobs_unchanged derivation subtracts error_count."""
    now = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)
    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        status=CrawlStatus.PARTIAL,
        started_at=now - timedelta(minutes=5),
        finished_at=now,
        created_at=now - timedelta(minutes=5),
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=0,
        error_count=1,
        source_name="Partial Error Co",
        ats_type="lever",
    )
    repo.runs[run.id] = run
    resp = client.get(f"/api/crawl/runs/{run.id}")
    assert resp.status_code == status.HTTP_200_OK
    # 10 - 6 - 2 - 0 - 1 = 1
    assert resp.json()["jobs_unchanged"] == 1


def test_list_runs_duration_is_null_for_running(client: TestClient) -> None:
    """Verify duration is None for RUNNING run."""
    resp = client.get("/api/crawl/runs?status=RUNNING")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    run = data["items"][0]
    assert run["status"] == "RUNNING"
    assert run["duration_ms"] is None


def test_list_runs_rejects_limit_over_100(client: TestClient) -> None:
    """Verify limit > 100 is rejected with 422."""
    resp = client.get("/api/crawl/runs?limit=101")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_runs_rejects_limit_under_1(client: TestClient) -> None:
    """Verify limit < 1 is rejected with 422."""
    resp = client.get("/api/crawl/runs?limit=0")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_runs_rejects_negative_offset(client: TestClient) -> None:
    """Verify offset < 0 is rejected with 422."""
    resp = client.get("/api/crawl/runs?offset=-1")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_runs_rejects_invalid_date_range(client: TestClient) -> None:
    """Verify date_from > date_to returns 422."""
    d_from = "2026-09-28T00:00:00Z"
    d_to = "2026-09-25T00:00:00Z"
    resp = client.get(f"/api/crawl/runs?date_from={d_from}&date_to={d_to}")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert "date_from must not be later than date_to" in resp.json()["detail"]


# ==============================================================================
# GET /api/crawl/runs/{crawl_run_id} Tests
# ==============================================================================


def test_get_run_detail_found(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify getting single run returns 200 and complete summary."""
    runs, _, _, _ = run_fixture_data
    target = runs[0]

    resp = client.get(f"/api/crawl/runs/{target.id}")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["id"] == str(target.id)
    assert data["source_id"] == str(target.source_id)
    assert data["source_name"] == target.source_name
    assert data["ats_type"] == target.ats_type
    assert data["status"] == "COMPLETED"
    assert data["jobs_found"] == 10
    assert data["jobs_created"] == 6
    assert data["jobs_updated"] == 2
    assert data["jobs_unchanged"] == 2
    assert data["jobs_closed"] == 1
    assert data["duration_ms"] == 60000


def test_get_run_detail_not_found(client: TestClient) -> None:
    """Verify getting non-existent run returns 404."""
    random_id = uuid.uuid4()
    resp = client.get(f"/api/crawl/runs/{random_id}")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert f"CrawlRun with ID '{random_id}' not found" in resp.json()["detail"]


def test_get_run_detail_invalid_uuid(client: TestClient) -> None:
    """Verify malformed UUID returns 422."""
    resp = client.get("/api/crawl/runs/not-a-valid-uuid")
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# GET /api/crawl/runs/{crawl_run_id}/jobs Tests
# ==============================================================================


def test_list_run_jobs_success(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify listing job actions for an existing run."""
    runs, jobs, _, _ = run_fixture_data
    target = runs[0]

    resp = client.get(f"/api/crawl/runs/{target.id}/jobs")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 2
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == 2

    actions = [item["action"] for item in data["items"]]
    assert "CREATED" in actions
    assert "UPDATED" in actions


def test_list_run_jobs_filter_by_action(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify action filtering for run jobs."""
    runs, _, _, _ = run_fixture_data
    target = runs[0]

    resp = client.get(f"/api/crawl/runs/{target.id}/jobs?action=CREATED")
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["action"] == "CREATED"
    assert data["items"][0]["title"] == "Software Engineer"


def test_list_run_jobs_not_found(client: TestClient) -> None:
    """Verify listing jobs for non-existent run returns 404."""
    random_id = uuid.uuid4()
    resp = client.get(f"/api/crawl/runs/{random_id}/jobs")
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert f"CrawlRun with ID '{random_id}' not found" in resp.json()["detail"]


def test_list_run_jobs_rejects_limit_bounds(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify pagination validation on run jobs endpoint."""
    runs, _, _, _ = run_fixture_data
    target = runs[0]

    resp1 = client.get(f"/api/crawl/runs/{target.id}/jobs?limit=101")
    assert resp1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    resp2 = client.get(f"/api/crawl/runs/{target.id}/jobs?limit=0")
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    resp3 = client.get(f"/api/crawl/runs/{target.id}/jobs?offset=-1")
    assert resp3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ==============================================================================
# Security & Secret Hygiene Verification
# ==============================================================================


def test_no_sensitive_configs_leaked_in_responses(
    client: TestClient,
    run_fixture_data: tuple[list[CrawlRun], list[CrawlRunJob], uuid.UUID, uuid.UUID],
) -> None:
    """Verify that runs and job responses contain zero secret source configurations."""
    runs, _, _, _ = run_fixture_data
    target = runs[0]

    forbidden_substrings = [
        "adapter_config",
        "endpoint_config",
        "rate_limit_config",
        "metadata",
        "api_key",
        "password",
        "secret",
        "token",
    ]

    # Test list runs
    resp_list = client.get("/api/crawl/runs")
    text_list = resp_list.text.lower()
    for forbidden in forbidden_substrings:
        assert forbidden not in text_list, (
            f"Forbidden string '{forbidden}' found in list runs"
        )

    # Test get run detail
    resp_detail = client.get(f"/api/crawl/runs/{target.id}")
    text_detail = resp_detail.text.lower()
    for forbidden in forbidden_substrings:
        assert forbidden not in text_detail, (
            f"Forbidden string '{forbidden}' found in run detail"
        )

    # Test list run jobs
    resp_jobs = client.get(f"/api/crawl/runs/{target.id}/jobs")
    text_jobs = resp_jobs.text.lower()
    for forbidden in forbidden_substrings:
        assert forbidden not in text_jobs, (
            f"Forbidden string '{forbidden}' found in run jobs"
        )
