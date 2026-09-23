"""API integration and endpoint contract tests for /api/sources."""

from __future__ import annotations

import datetime
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source import Source, SourceRepository
from backend.interfaces.api.dependencies.sources import get_source_registry_service


class InMemorySourceRepo(SourceRepository):
    """Simple in-memory repository for API testing."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self.sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        return self.sources.get(source_id)

    async def get_by_url(self, url: str) -> Source | None:
        for s in self.sources.values():
            if s.url == url:
                return s
        return None

    async def list_all(
        self,
        active_only: bool = False,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        res = list(self.sources.values())
        if active_only:
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
        self.sources[source.id] = source
        return source

    async def save_bulk(self, sources: list[Source]) -> list[Source]:
        for s in sources:
            self.sources[s.id] = s
        return list(sources)

    async def count(
        self,
        active_only: bool = False,
        ats_type: str | None = None,
    ) -> int:
        res = list(self.sources.values())
        if active_only:
            res = [s for s in res if s.active]
        if ats_type is not None:
            res = [s for s in res if s.ats_type == ats_type]
        return len(res)


def _seed_test_sources() -> list[Source]:
    now = datetime.datetime.now(datetime.UTC)
    return [
        Source(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            name="Getir Lever",
            company="Getir",
            url="https://jobs.lever.co/getir",
            country="TR",
            ats_type="lever",
            active=True,
            adapter_config={"site_id": "getir"},
            pagination_config={},
            endpoint_config={},
            rate_limit_config={},
            metadata={"source": "manual"},
            created_at=now,
            updated_at=now,
        ),
        Source(
            id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            name="Trendyol Greenhouse",
            company="Trendyol",
            url="https://boards.greenhouse.io/trendyol",
            country="TR",
            ats_type="greenhouse",
            active=True,
            adapter_config={"board_token": "trendyol"},
            pagination_config={},
            endpoint_config={},
            rate_limit_config={},
            metadata={},
            created_at=now,
            updated_at=now,
        ),
        Source(
            id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
            name="Deprecated Source",
            company="OldCorp",
            url="https://jobs.ashbyhq.com/oldcorp",
            country="Global",
            ats_type="ashby",
            active=False,
            adapter_config={},
            pagination_config={},
            endpoint_config={},
            rate_limit_config={},
            metadata={},
            created_at=now,
            updated_at=now,
        ),
    ]


def test_get_sources_list_success(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources returns 200 with all registered sources."""
    repo = InMemorySourceRepo(_seed_test_sources())
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 3
    assert len(data["items"]) == 3

    first_item = data["items"][0]
    expected_fields = {
        "id",
        "name",
        "company",
        "url",
        "country",
        "ats_type",
        "active",
        "adapter_config",
        "pagination_config",
        "endpoint_config",
        "rate_limit_config",
        "metadata",
        "created_at",
        "updated_at",
    }
    assert expected_fields.issubset(set(first_item.keys()))


def test_get_sources_active_only_filter(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources?active_only=true returns only active sources."""
    repo = InMemorySourceRepo(_seed_test_sources())
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources?active_only=true")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all(item["active"] is True for item in data["items"])


def test_get_sources_ats_type_filter(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources?ats_type=greenhouse filters by ATS."""
    repo = InMemorySourceRepo(_seed_test_sources())
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources?ats_type=greenhouse")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["ats_type"] == "greenhouse"
    assert data["items"][0]["name"] == "Trendyol Greenhouse"


def test_get_sources_pagination(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources pagination with limit and offset."""
    repo = InMemorySourceRepo(_seed_test_sources())
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources?limit=1&offset=1")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3  # Total count unaffected by pagination
    assert len(data["items"]) == 1  # Sliced items count


def test_negative_post_source_not_implemented(client: TestClient) -> None:
    """Verify POST /api/sources returns 405 Method Not Allowed."""
    response = client.post(
        "/api/sources",
        json={"name": "Test", "url": "https://test.com", "ats_type": "lever"},
    )
    assert response.status_code == 405


def test_negative_get_source_detail_not_implemented(client: TestClient) -> None:
    """Verify GET /api/sources/{id} returns 404 (excluded from Phase 3.1)."""
    random_id = uuid.uuid4()
    response = client.get(f"/api/sources/{random_id}")
    assert response.status_code == 404


def test_negative_patch_source_not_implemented(client: TestClient) -> None:
    """Verify PATCH /api/sources/{id} returns 404 or 405 (excluded from Phase 3.1)."""
    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/sources/{random_id}",
        json={"name": "Renamed"},
    )
    assert response.status_code in (404, 405)


def test_negative_sync_endpoint_reserved_for_phase_3_2(client: TestClient) -> None:
    """Verify POST /api/sources/sync is not implemented in Phase 3.1."""
    response = client.post("/api/sources/sync")
    assert response.status_code in (404, 405)
