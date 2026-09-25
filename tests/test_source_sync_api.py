"""Integration tests for POST /api/sources/sync API endpoint."""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.application.job_discovery.dtos import SourceCreateDTO
from backend.application.job_discovery.ports import CatalogParser
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source.entities import Source
from backend.domain.source.repositories import SourceRepository
from backend.interfaces.api.dependencies.sources import (
    get_catalog_parser,
    get_source_registry_service,
)


class InMemorySourceRepo(SourceRepository):
    """In-memory stub implementing SourceRepository."""

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
        if offset > 0:
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
        return sources

    async def count(
        self, active_only: bool = False, ats_type: str | None = None
    ) -> int:
        return len(await self.list_all(active_only=active_only, ats_type=ats_type))


class MockCatalogParser(CatalogParser):
    """Mock implementation of CatalogParser."""

    def __init__(
        self,
        dtos: list[SourceCreateDTO] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        self.dtos = dtos or []
        self.warnings = warnings or []

    def parse_content(self, content: str) -> tuple[list[SourceCreateDTO], list[str]]:
        return self.dtos, self.warnings

    def parse_file(self, file_path: str) -> tuple[list[SourceCreateDTO], list[str]]:
        return self.dtos, self.warnings


def test_post_sources_sync_success(app: FastAPI, client: TestClient) -> None:
    """Verify POST /api/sources/sync returns 200 with SourceSyncResponse."""
    repo = InMemorySourceRepo([])
    mock_parser = MockCatalogParser(
        dtos=[
            SourceCreateDTO(
                name="Trendyol",
                company="Trendyol",
                url="https://jobs.lever.co/trendyol",
                ats_type="lever",
            ),
            SourceCreateDTO(
                name="Getir",
                company="Getir",
                url="https://boards.greenhouse.io/getir",
                ats_type="greenhouse",
            ),
        ],
        warnings=["Sample non-fatal parse warning"],
    )
    service = SourceRegistryService(repository=repo, catalog_parser=mock_parser)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    response = client.post("/api/sources/sync")
    assert response.status_code == 200

    data = response.json()
    assert data["total_scanned"] == 3  # 2 dtos + 1 warning
    assert data["created"] == 2
    assert data["updated"] == 0
    assert data["skipped"] == 1
    assert "Sample non-fatal parse warning" in data["errors"]


def test_post_sources_sync_idempotency_via_http(
    app: FastAPI, client: TestClient
) -> None:
    """Verify calling POST /api/sources/sync twice produces created=0 on second call."""
    repo = InMemorySourceRepo([])
    mock_parser = MockCatalogParser(
        dtos=[
            SourceCreateDTO(
                name="Trendyol",
                company="Trendyol",
                url="https://jobs.lever.co/trendyol",
                ats_type="lever",
            )
        ]
    )
    service = SourceRegistryService(repository=repo, catalog_parser=mock_parser)
    app.dependency_overrides[get_source_registry_service] = lambda: service

    # First call: created == 1
    resp1 = client.post("/api/sources/sync")
    assert resp1.status_code == 200
    assert resp1.json()["created"] == 1
    assert resp1.json()["updated"] == 0

    # Second call: created == 0, updated == 1
    resp2 = client.post("/api/sources/sync")
    assert resp2.status_code == 200
    assert resp2.json()["created"] == 0
    assert resp2.json()["updated"] == 1


def test_catalog_parser_dependency_injection(app: FastAPI) -> None:
    """Verify get_catalog_parser returns a CatalogParser instance."""
    parser = get_catalog_parser()
    assert isinstance(parser, CatalogParser)
