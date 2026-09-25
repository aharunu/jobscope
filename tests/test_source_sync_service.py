"""Unit tests for SourceRegistryService synchronization logic."""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest

from backend.application.job_discovery.dtos import SourceCreateDTO
from backend.application.job_discovery.ports import CatalogParser
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source.entities import Source
from backend.domain.source.repositories import SourceRepository


class InMemorySourceRepo(SourceRepository):
    """In-memory stub implementing SourceRepository for testing."""

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
    """Mock implementation of CatalogParser for testing."""

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


def test_clean_architecture_service_independence() -> None:
    """Verify services.py does not import infrastructure parsers or settings."""
    service_file = Path("backend/application/job_discovery/services.py")
    tree = ast.parse(service_file.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "infrastructure" not in alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert "infrastructure" not in node.module


@pytest.mark.asyncio
async def test_sync_sources_first_import_and_idempotency() -> None:
    """Verify first sync creates entries and second sync is idempotent (created=0)."""
    repo = InMemorySourceRepo()
    service = SourceRegistryService(repo)

    dtos = [
        SourceCreateDTO(
            name="Trendyol",
            company="Trendyol",
            url="https://jobs.lever.co/trendyol",
            ats_type="lever",
            country="TR",
            active=True,
            metadata={"category": "E-commerce"},
        ),
        SourceCreateDTO(
            name="Getir",
            company="Getir",
            url="https://boards.greenhouse.io/getir/",
            ats_type="greenhouse",
            country="TR",
            active=True,
            metadata={"category": "Quick-commerce"},
        ),
    ]

    # First run: creates 2 sources
    result_1 = await service.sync_sources(dtos)
    assert result_1.total_scanned == 2
    assert result_1.created == 2
    assert result_1.updated == 0
    assert result_1.skipped == 0
    assert await repo.count() == 2

    # Second run with same DTOs: 0 created, 2 updated
    result_2 = await service.sync_sources(dtos)
    assert result_2.total_scanned == 2
    assert result_2.created == 0
    assert result_2.updated == 2
    assert result_2.skipped == 0
    assert await repo.count() == 2


@pytest.mark.asyncio
async def test_sync_sources_preserves_custom_config_and_active_status() -> None:
    """Verify sync preserves manual active=False toggle and adapter configs."""
    repo = InMemorySourceRepo()
    service = SourceRegistryService(repo)

    # Manually configure an existing source with custom adapter config and active=False
    existing = Source(
        id=uuid.uuid4(),
        name="Custom Co",
        url="https://jobs.lever.co/custom",
        ats_type="lever",
        active=False,  # Manually deactivated
        adapter_config={"custom_header": "Bearer secret"},
        metadata={"custom_note": "Do not delete"},
    )
    await repo.save(existing)

    catalog_dtos = [
        SourceCreateDTO(
            name="Custom Co Updated Name",
            url="https://jobs.lever.co/custom/",
            ats_type="lever",
            active=True,  # Catalog defaults to True; DB active=False preserved
            adapter_config={},  # Catalog has empty adapter config
            metadata={"category": "Tech"},
        )
    ]

    result = await service.sync_sources(catalog_dtos)
    assert result.created == 0
    assert result.updated == 1

    saved = await repo.get_by_url("https://jobs.lever.co/custom")
    assert saved is not None
    assert saved.active is False  # Manual deactivation preserved!
    assert saved.adapter_config == {"custom_header": "Bearer secret"}  # Preserved!
    assert saved.metadata["custom_note"] == "Do not delete"  # Preserved!
    assert saved.metadata["category"] == "Tech"  # Enriched!


@pytest.mark.asyncio
async def test_sync_sources_in_memory_deduplication() -> None:
    """Verify intra-file duplicate URLs are merged before persisting."""
    repo = InMemorySourceRepo()
    service = SourceRegistryService(repo)

    dtos = [
        SourceCreateDTO(
            name="Alpha Corp",
            url="https://alpha.com/jobs/",
            ats_type="custom",
            metadata={
                "category": "Category 1",
                "alternate_urls": ["https://alpha.com"],
            },
        ),
        SourceCreateDTO(
            name="Alpha Corp Secondary",
            url="https://alpha.com/jobs",  # Same normalized URL!
            ats_type="custom",
            metadata={"category": "Category 2", "notes": "Merged note"},
        ),
    ]

    result = await service.sync_sources(dtos)
    assert result.created == 1
    assert result.skipped == 1  # 1 duplicate merged
    assert await repo.count() == 1

    saved = await repo.get_by_url("https://alpha.com/jobs")
    assert saved is not None
    assert saved.metadata["notes"] == "Merged note"


@pytest.mark.asyncio
async def test_sync_from_catalog_success() -> None:
    """Verify sync_from_catalog delegates to injected parser and default path."""
    repo = InMemorySourceRepo()
    mock_parser = MockCatalogParser(
        dtos=[
            SourceCreateDTO(
                name="Mock Source",
                url="https://mock.com/jobs",
                ats_type="custom",
            )
        ],
        warnings=["Sample warning"],
    )
    service = SourceRegistryService(
        repository=repo,
        catalog_parser=mock_parser,
        default_catalog_path="data/turkish-job-sources.md",
    )

    result = await service.sync_from_catalog()
    assert result.created == 1
    assert "Sample warning" in result.errors


@pytest.mark.asyncio
async def test_sync_from_catalog_unconfigured_parser_raises() -> None:
    """Verify sync_from_catalog raises RuntimeError if catalog_parser is None."""
    repo = InMemorySourceRepo()
    service = SourceRegistryService(repo, catalog_parser=None)

    with pytest.raises(RuntimeError, match="Catalog parser port is not configured"):
        await service.sync_from_catalog()
