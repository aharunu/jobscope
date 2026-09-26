"""API contract and endpoint integration tests for POST /api/crawl/run."""

from __future__ import annotations

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_discovery.ports import (
    ATSAdapter,
    CrawlPersistenceManager,
)
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.source.entities import Source
from backend.domain.source.repositories import SourceRepository
from backend.interfaces.api.dependencies.crawler import (
    get_adapter_registry,
    get_crawl_persistence_manager,
    get_crawler_orchestrator,
)
from backend.interfaces.api.dependencies.sources import (
    get_source_registry_service,
    get_source_repository,
)
from backend.interfaces.api.main import create_app


class MockATSAdapter(ATSAdapter):
    """Test double for ATSAdapter."""

    def __init__(
        self, ats_type: str = "lever", jobs: list[DiscoveredJobDTO] | None = None
    ) -> None:
        self._ats_type = ats_type
        self._jobs = jobs or []

    @property
    def ats_type(self) -> str:
        return self._ats_type

    async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
        return CrawlResultDTO(
            source_id=source.id,
            ats_type=self.ats_type,
            jobs=self._jobs,
            raw_payload_count=len(self._jobs),
        )


class InMemorySourceRepo(SourceRepository):
    """In-memory source repository for API route testing."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self._sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        return self._sources.get(source_id)

    async def get_by_url(self, url: str) -> Source | None:
        for s in self._sources.values():
            if s.url == url:
                return s
        return None

    async def list_all(
        self,
        active_only: bool = False,
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        res = list(self._sources.values())
        if is_active is not None:
            res = [s for s in res if s.active is is_active]
        elif active_only:
            res = [s for s in res if s.active]

        if ats_type is not None:
            res = [s for s in res if s.ats_type == ats_type]

        res.sort(key=lambda s: s.name)
        if offset:
            res = res[offset:]
        if limit is not None:
            res = res[:limit]
        return res

    async def save(self, source: Source) -> Source:
        self._sources[source.id] = source
        return source

    async def count(
        self,
        active_only: bool = False,
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        sources = await self.list_all(
            active_only=active_only,
            is_active=is_active,
            ats_type=ats_type,
            search_query=search_query,
        )
        return len(sources)

    async def count_by_ats_type(self) -> dict[str, int]:
        return {}

    async def count_by_country(self) -> dict[str, int]:
        return {}


class MockCrawlPersistenceManager(CrawlPersistenceManager):
    """Test double for CrawlPersistenceManager."""

    def __init__(self) -> None:
        self.created_runs: list[uuid.UUID] = []
        self.failed_runs: list[uuid.UUID] = []

    async def create_initial_run(self, source_id: uuid.UUID) -> uuid.UUID:
        run_id = uuid.uuid4()
        self.created_runs.append(run_id)
        return run_id

    async def mark_run_failed(
        self,
        crawl_run_id: uuid.UUID,
        error_count: int = 1,
        error_message: str | None = None,
    ) -> None:
        self.failed_runs.append(crawl_run_id)

    async def execute_ingestion(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        crawl_run_id: uuid.UUID,
    ):
        from backend.application.job_processing.dtos import JobIngestionResultDTO

        return JobIngestionResultDTO(
            crawl_run_id=crawl_run_id,
            source_id=source.id,
            status=CrawlStatus.COMPLETED,
            jobs_found=len(crawl_result.jobs),
            jobs_created=len(crawl_result.jobs),
            jobs_updated=0,
            jobs_unchanged=0,
            jobs_closed=0,
            error_count=0,
        )


@pytest.fixture
def source_repo() -> InMemorySourceRepo:
    s1 = Source(
        id=uuid.uuid4(),
        name="Trendyol Lever",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
        active=True,
    )
    s2 = Source(
        id=uuid.uuid4(),
        name="Getir Lever",
        url="https://jobs.lever.co/getir",
        ats_type="lever",
        company="Getir",
        active=True,
    )
    s_inactive = Source(
        id=uuid.uuid4(),
        name="Inactive Board",
        url="https://jobs.lever.co/inactive",
        ats_type="lever",
        company="OldCo",
        active=False,
    )
    s_greenhouse = Source(
        id=uuid.uuid4(),
        name="Insider Greenhouse",
        url="https://boards.greenhouse.io/insider",
        ats_type="greenhouse",
        company="Insider",
        active=True,
    )
    return InMemorySourceRepo([s1, s2, s_inactive, s_greenhouse])


@pytest.fixture
def client(source_repo: InMemorySourceRepo) -> TestClient:
    app = create_app()

    source_service = SourceRegistryService(repository=source_repo)
    lever_adapter = MockATSAdapter(
        ats_type="lever",
        jobs=[
            DiscoveredJobDTO(
                external_job_id="job-101",
                url="https://jobs.lever.co/trendyol/101",
                title="Staff Engineer",
                raw_content='{"id": "101"}',
                content_type="application/json",
            )
        ],
    )
    registry = ATSAdapterRegistry([lever_adapter])
    persistence_mgr = MockCrawlPersistenceManager()
    orchestrator = CrawlerOrchestrator(
        source_provider=source_service,
        adapter_registry=registry,
        persistence_manager=persistence_mgr,
    )

    app.dependency_overrides[get_source_repository] = lambda: source_repo
    app.dependency_overrides[get_source_registry_service] = lambda: source_service
    app.dependency_overrides[get_adapter_registry] = lambda: registry
    app.dependency_overrides[get_crawl_persistence_manager] = lambda: persistence_mgr
    app.dependency_overrides[get_crawler_orchestrator] = lambda: orchestrator

    return TestClient(app)


def test_crawl_run_single_active_source(
    client: TestClient, source_repo: InMemorySourceRepo
) -> None:
    """Verify POST /api/crawl/run with active source_id crawls and returns 200."""
    source = next(
        s for s in source_repo._sources.values() if s.name == "Trendyol Lever"
    )

    resp = client.post("/api/crawl/run", json={"source_id": str(source.id)})
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total_sources_crawled"] == 1
    assert data["successful_crawls"] == 1
    assert data["failed_crawls"] == 0
    assert len(data["runs"]) == 1

    run = data["runs"][0]
    assert run["source_id"] == str(source.id)
    assert run["source_name"] == "Trendyol Lever"
    assert run["ats_type"] == "lever"
    assert run["status"] == "COMPLETED"
    assert run["jobs_found"] == 1
    assert run["jobs_created"] == 1
    assert run["crawl_run_id"] is not None


def test_crawl_run_unknown_source_returns_404(client: TestClient) -> None:
    """Verify POST /api/crawl/run with unknown source_id returns 404."""
    unknown_id = uuid.uuid4()
    resp = client.post("/api/crawl/run", json={"source_id": str(unknown_id)})
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert f"Source with ID '{unknown_id}' not found" in resp.json()["detail"]


def test_crawl_run_inactive_source_returns_400(
    client: TestClient, source_repo: InMemorySourceRepo
) -> None:
    """Verify POST /api/crawl/run with inactive source_id returns 400."""
    inactive = next(s for s in source_repo._sources.values() if not s.active)

    resp = client.post("/api/crawl/run", json={"source_id": str(inactive.id)})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "is inactive and cannot be crawled" in resp.json()["detail"]


def test_crawl_run_by_ats_type(client: TestClient) -> None:
    """Verify POST /api/crawl/run with ats_type filters active sources."""
    resp = client.post("/api/crawl/run", json={"ats_type": "lever"})
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    # 2 active lever sources: Trendyol and Getir
    assert data["total_sources_crawled"] == 2
    assert data["successful_crawls"] == 2
    for run in data["runs"]:
        assert run["ats_type"] == "lever"
        assert run["status"] == "COMPLETED"


def test_crawl_run_batch_limit_bounds_source_count(client: TestClient) -> None:
    """Verify limit bounds the number of active sources crawled."""
    resp = client.post("/api/crawl/run", json={"ats_type": "lever", "limit": 1})
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    assert data["total_sources_crawled"] == 1
    assert len(data["runs"]) == 1


def test_crawl_run_all_active_sources(client: TestClient) -> None:
    """Verify POST /api/crawl/run without filters crawls all active sources."""
    resp = client.post("/api/crawl/run", json={})
    assert resp.status_code == status.HTTP_200_OK

    data = resp.json()
    # 3 active sources (2 lever + 1 greenhouse)
    # Greenhouse has no registered adapter in this test setup -> ends with FAILED
    assert data["total_sources_crawled"] == 3
    assert data["successful_crawls"] == 2
    assert data["failed_crawls"] == 1


def test_crawl_run_rejects_extra_fields(client: TestClient) -> None:
    """Verify request validation rejects extra disallowed parameters."""
    resp = client.post("/api/crawl/run", json={"bogus_field": 123})
    assert resp.status_code == 422
