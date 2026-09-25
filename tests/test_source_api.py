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
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        res = list(self.sources.values())
        if is_active is not None:
            res = [s for s in res if s.active is is_active]
        elif active_only:
            res = [s for s in res if s.active]

        if ats_type is not None:
            res = [s for s in res if s.ats_type == ats_type]

        if search_query and search_query.strip():
            sq = search_query.strip().lower()
            res = [
                s
                for s in res
                if sq in s.name.lower()
                or (s.company and sq in s.company.lower())
                or sq in s.url.lower()
            ]

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
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        res = await self.list_all(
            active_only=active_only,
            is_active=is_active,
            ats_type=ats_type,
            search_query=search_query,
        )
        return len(res)

    async def count_by_ats_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.sources.values():
            counts[s.ats_type] = counts.get(s.ats_type, 0) + 1
        return counts

    async def count_by_country(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.sources.values():
            country = s.country or "Unknown"
            counts[country] = counts.get(country, 0) + 1
        return counts


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


def test_get_source_detail_success(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources/{id} returns 200 and full source details."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target = sources[0]
    response = client.get(f"/api/sources/{target.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(target.id)
    assert data["name"] == target.name
    assert data["company"] == target.company
    assert data["url"] == target.url
    assert data["active"] is True
    assert data["adapter_config"] == target.adapter_config


def test_get_source_detail_not_found(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources/{id} returns 404 when ID does not exist."""
    repo = InMemorySourceRepo([])
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    random_id = uuid.uuid4()
    response = client.get(f"/api/sources/{random_id}")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


def test_get_sources_is_active_filter(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources?is_active=false returns only inactive sources."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["active"] is False
    assert data["items"][0]["name"] == "Deprecated Source"


def test_get_sources_search_filter(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources?search=trendyol performs case-insensitive search."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources?search=trendyol")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Trendyol Greenhouse"


def test_get_sources_stats_success(app: FastAPI, client: TestClient) -> None:
    """Verify GET /api/sources/stats returns aggregated operational metrics."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_sources"] == 3
    assert data["active_sources"] == 2
    assert data["inactive_sources"] == 1
    assert "by_ats_type" in data
    assert "by_country" in data


def test_patch_source_config_success(app: FastAPI, client: TestClient) -> None:
    """Verify PATCH /api/sources/{id} updates operational config."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target = sources[0]
    response = client.patch(
        f"/api/sources/{target.id}",
        json={
            "name": "Renamed Getir",
            "adapter_config": {"site_id": "new-getir"},
            "metadata": {"updated_by": "admin"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Renamed Getir"
    assert data["adapter_config"] == {"site_id": "new-getir"}
    assert data["metadata"]["updated_by"] == "admin"
    assert data["active"] is True  # Preserved!


def test_patch_source_config_rejects_active_field(
    app: FastAPI, client: TestClient
) -> None:
    """CRITICAL: PATCH /api/sources/{id} must forbid active field (use /status)."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target = sources[0]
    response = client.patch(
        f"/api/sources/{target.id}",
        json={"active": False},
    )
    assert response.status_code == 422  # extra="forbid" triggers validation error


def test_patch_source_config_not_found(app: FastAPI, client: TestClient) -> None:
    """Verify PATCH /api/sources/{id} returns 404 for unknown ID."""
    repo = InMemorySourceRepo([])
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/sources/{random_id}",
        json={"name": "Renamed"},
    )
    assert response.status_code == 404


def test_patch_source_forbidden_extra_fields(app: FastAPI, client: TestClient) -> None:
    """Verify unknown fields in PATCH /api/sources/{id} are rejected with 422."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target = sources[0]
    response = client.patch(
        f"/api/sources/{target.id}",
        json={"unknown_property": "bad_data"},
    )
    assert response.status_code == 422


def test_patch_source_status_success(app: FastAPI, client: TestClient) -> None:
    """Verify PATCH /api/sources/{id}/status explicitly toggles active status."""
    sources = _seed_test_sources()
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    target = sources[0]
    assert target.active is True

    # Deactivate
    response = client.patch(
        f"/api/sources/{target.id}/status",
        json={"active": False},
    )
    assert response.status_code == 200
    assert response.json()["active"] is False

    # Reactivate
    response = client.patch(
        f"/api/sources/{target.id}/status",
        json={"active": True},
    )
    assert response.status_code == 200
    assert response.json()["active"] is True


def test_patch_source_status_not_found(app: FastAPI, client: TestClient) -> None:
    """Verify PATCH /api/sources/{id}/status returns 404 for unknown ID."""
    repo = InMemorySourceRepo([])
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    random_id = uuid.uuid4()
    response = client.patch(
        f"/api/sources/{random_id}/status",
        json={"active": False},
    )
    assert response.status_code == 404


def test_route_ordering_stats_not_matched_as_uuid(
    app: FastAPI, client: TestClient
) -> None:
    """Verify /stats is resolved properly and not parsed as a source_id UUID."""
    repo = InMemorySourceRepo([])
    service = SourceRegistryService(repo)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.get("/api/sources/stats")
    assert response.status_code == 200


def test_sync_endpoint_available_in_phase_3_2(app: FastAPI, client: TestClient) -> None:
    """Verify POST /api/sources/sync is implemented and returns 200 in Phase 3.2."""
    from backend.infrastructure.parsers.markdown_source_parser import (
        MarkdownSourceParser,
    )

    repo = InMemorySourceRepo([])
    parser = MarkdownSourceParser()
    service = SourceRegistryService(repo, catalog_parser=parser)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.post("/api/sources/sync")
    assert response.status_code == 200
    data = response.json()
    assert "total_scanned" in data
    assert "created" in data
    assert "updated" in data
    assert "skipped" in data
