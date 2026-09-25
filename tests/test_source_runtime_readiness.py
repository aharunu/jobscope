"""Unit and integration tests for Phase 3.5 — Source Registry Runtime Readiness."""

from __future__ import annotations

import dataclasses
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.application.job_discovery.ports import (
    RuntimeSourceProvider,
    SourceHealthProbe,
)
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source import Source, SourceRepository
from backend.domain.source.enums import KnownATSType, is_known_ats_type
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)


class InMemorySourceRepo(SourceRepository):
    """In-memory mock repository implementing SourceRepository protocol."""

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

        # Deterministic sorting: name ASC, id ASC
        res.sort(key=lambda s: (s.name, str(s.id)))
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


# ==============================================================================
# 1. ATS Type Classification & Boundary Tests
# ==============================================================================


def test_known_ats_type_semantics() -> None:
    """Verify known ATS platforms are identified, while custom/unknown are not."""
    # Enum invariants
    assert KnownATSType.LEVER == "lever"
    assert "custom" not in {t.value for t in KnownATSType}

    # Standard recognized ATS types
    assert is_known_ats_type("lever") is True
    assert is_known_ats_type("LEVER") is True
    assert is_known_ats_type("greenhouse") is True
    assert is_known_ats_type("workday") is True
    assert is_known_ats_type("ashby") is True
    assert is_known_ats_type("smartrecruiters") is True
    assert is_known_ats_type("recruitee") is True
    assert is_known_ats_type("personio") is True
    assert is_known_ats_type("workable") is True
    assert is_known_ats_type("bamboohr") is True
    assert is_known_ats_type("hirex") is True
    assert is_known_ats_type("teamtailor") is True
    assert is_known_ats_type("oracle") is True
    assert is_known_ats_type("kariyer_net") is True

    # "custom" must remain representable, but NOT classified as a known ATS platform
    assert is_known_ats_type("custom") is False
    assert is_known_ats_type("CUSTOM") is False

    # Arbitrary/unsupported ATS types are representable, not known
    assert is_known_ats_type("custom_portal") is False
    assert is_known_ats_type("legacy_erp") is False
    assert is_known_ats_type("unknown_scraper") is False
    assert is_known_ats_type("") is False


def test_runtime_source_dto_is_known_ats_property() -> None:
    """Verify RuntimeSourceDTO.is_known_ats property behaves consistently."""
    source_known = Source(
        name="Trendyol",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        active=True,
    )
    dto_known = RuntimeSourceDTO.from_domain(source_known)
    assert dto_known.is_known_ats is True

    source_custom = Source(
        name="Local Portal",
        url="https://example.com/careers",
        ats_type="custom",
        active=True,
    )
    dto_custom = RuntimeSourceDTO.from_domain(source_custom)
    assert dto_custom.is_known_ats is False

    source_arbitrary = Source(
        name="Legacy ERP",
        url="https://erp.corp.com/jobs",
        ats_type="legacy_erp",
        active=True,
    )
    dto_arbitrary = RuntimeSourceDTO.from_domain(source_arbitrary)
    assert dto_arbitrary.is_known_ats is False


# ==============================================================================
# 2. RuntimeSourceDTO Immutability & Deep-Copy Tests
# ==============================================================================


def test_runtime_source_dto_frozen_immutability() -> None:
    """Verify RuntimeSourceDTO cannot be mutated via attribute assignment."""
    source = Source(
        name="Getir",
        url="https://jobs.lever.co/getir",
        ats_type="lever",
        active=True,
    )
    dto = RuntimeSourceDTO.from_domain(source)

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.name = "Mutated Name"  # type: ignore[misc]

    with pytest.raises(dataclasses.FrozenInstanceError):
        dto.ats_type = "greenhouse"  # type: ignore[misc]


def test_runtime_source_dto_nested_deep_copy_isolation() -> None:
    """Verify deep defensive copying prevents nested mutation leakage."""
    source = Source(
        name="Test Corp",
        url="https://test.com",
        ats_type="lever",
        active=True,
        adapter_config={"nested": {"client_id": "secret-123", "tags": ["tech", "tr"]}},
        pagination_config={"settings": {"page_size": 50, "cursors": [1, 2]}},
        endpoint_config={"headers": {"Authorization": "Bearer token"}},
        rate_limit_config={"limits": {"rpm": 60}},
        metadata={"alternate_urls": ["https://test.com/alt1"], "category": "IT"},
    )

    dto = RuntimeSourceDTO.from_domain(source)

    # 1. Mutate nested structures inside the DTO
    dto.adapter_config["nested"]["client_id"] = "MUTATED"
    dto.adapter_config["nested"]["tags"].append("MUTATED_TAG")
    dto.pagination_config["settings"]["page_size"] = 999
    dto.metadata["alternate_urls"].append("https://test.com/MUTATED")

    # 2. Assert source entity remains completely untouched
    assert source.adapter_config["nested"]["client_id"] == "secret-123"
    assert source.adapter_config["nested"]["tags"] == ["tech", "tr"]
    assert source.pagination_config["settings"]["page_size"] == 50
    assert source.metadata["alternate_urls"] == ["https://test.com/alt1"]

    # 3. Mutate source entity nested structures
    source.endpoint_config["headers"]["Authorization"] = "Bearer NEW_TOKEN"
    source.rate_limit_config["limits"]["rpm"] = 120

    # 4. Assert DTO remains completely untouched
    assert dto.endpoint_config["headers"]["Authorization"] == "Bearer token"
    assert dto.rate_limit_config["limits"]["rpm"] == 60


# ==============================================================================
# 3. Active Runtime Query & Filtering Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_crawlable_sources_excludes_inactive_sources() -> None:
    """Verify get_crawlable_sources strictly returns active sources."""
    s1 = Source(name="Active 1", url="https://a1.com", ats_type="lever", active=True)
    s2 = Source(name="Inactive 1", url="https://i1.com", ats_type="lever", active=False)
    s3 = Source(
        name="Active 2", url="https://a2.com", ats_type="greenhouse", active=True
    )
    s4 = Source(
        name="Inactive 2", url="https://i2.com", ats_type="workday", active=False
    )

    repo = InMemorySourceRepo([s1, s2, s3, s4])
    service = SourceRegistryService(repo)

    crawlable = await service.get_crawlable_sources()
    assert len(crawlable) == 2
    crawlable_ids = {c.id for c in crawlable}
    assert s1.id in crawlable_ids
    assert s3.id in crawlable_ids
    assert s2.id not in crawlable_ids
    assert s4.id not in crawlable_ids


@pytest.mark.asyncio
async def test_get_crawlable_sources_ats_filter() -> None:
    """Verify get_crawlable_sources filters by ATS type."""
    s1 = Source(name="Lever 1", url="https://l1.com", ats_type="lever", active=True)
    s2 = Source(name="Lever 2", url="https://l2.com", ats_type="lever", active=True)
    s3 = Source(name="Ashby 1", url="https://a1.com", ats_type="ashby", active=True)
    s4 = Source(name="Custom 1", url="https://c1.com", ats_type="custom", active=True)

    repo = InMemorySourceRepo([s1, s2, s3, s4])
    service = SourceRegistryService(repo)

    lever_sources = await service.get_crawlable_sources(ats_type="lever")
    assert len(lever_sources) == 2
    assert all(s.ats_type == "lever" for s in lever_sources)

    custom_sources = await service.get_crawlable_sources(ats_type="custom")
    assert len(custom_sources) == 1
    assert custom_sources[0].ats_type == "custom"


@pytest.mark.asyncio
async def test_get_crawlable_sources_pagination() -> None:
    """Verify get_crawlable_sources deterministic pagination."""
    sources = [
        Source(
            name=f"Source {i:02d}",
            url=f"https://s{i}.com",
            ats_type="lever",
            active=True,
        )
        for i in range(10)
    ]
    repo = InMemorySourceRepo(sources)
    service = SourceRegistryService(repo)

    page1 = await service.get_crawlable_sources(limit=4, offset=0)
    page2 = await service.get_crawlable_sources(limit=4, offset=4)
    page3 = await service.get_crawlable_sources(limit=4, offset=8)

    assert len(page1) == 4
    assert len(page2) == 4
    assert len(page3) == 2

    # Verify no overlaps and all unique
    seen_ids = set()
    for item in page1 + page2 + page3:
        assert item.id not in seen_ids
        seen_ids.add(item.id)
    assert len(seen_ids) == 10


@pytest.mark.asyncio
async def test_get_crawlable_source_by_id_active_and_inactive() -> None:
    """Verify get_crawlable_source returns DTO for active, None for inactive."""
    s_active = Source(
        name="Active", url="https://act.com", ats_type="lever", active=True
    )
    s_inactive = Source(
        name="Inactive", url="https://inact.com", ats_type="lever", active=False
    )

    repo = InMemorySourceRepo([s_active, s_inactive])
    service = SourceRegistryService(repo)

    # Active source -> returns RuntimeSourceDTO
    result_active = await service.get_crawlable_source(s_active.id)
    assert result_active is not None
    assert isinstance(result_active, RuntimeSourceDTO)
    assert result_active.id == s_active.id
    assert result_active.name == "Active"

    # Inactive source -> strictly returns None (cannot be crawled)
    result_inactive = await service.get_crawlable_source(s_inactive.id)
    assert result_inactive is None

    # Missing UUID -> returns None
    result_missing = await service.get_crawlable_source(uuid.uuid4())
    assert result_missing is None


# ==============================================================================
# 4. Port & Architecture Boundary Tests
# ==============================================================================


def test_service_satisfies_runtime_source_provider_protocol() -> None:
    """Verify SourceRegistryService implements RuntimeSourceProvider protocol."""
    repo = InMemorySourceRepo([])
    service = SourceRegistryService(repo)
    assert isinstance(service, RuntimeSourceProvider)


@pytest.mark.asyncio
async def test_runtime_retrieval_does_not_probe_or_mutate() -> None:
    """Verify runtime queries never invoke health probe or mutate repository state."""
    mock_probe = AsyncMock(spec=SourceHealthProbe)
    s = Source(name="Stable", url="https://stable.com", ats_type="lever", active=True)
    repo = InMemorySourceRepo([s])
    service = SourceRegistryService(repo, health_probe=mock_probe)

    # Execute runtime queries
    await service.get_crawlable_sources()
    await service.get_crawlable_source(s.id)

    # Health probe must NEVER be called
    mock_probe.probe.assert_not_called()
    mock_probe.probe_batch.assert_not_called()

    # Source active status remains unchanged
    assert repo.sources[s.id].active is True


@pytest.mark.asyncio
async def test_repository_list_all_deterministic_ordering_statement() -> None:
    """Verify SQLAlchemySourceRepository orders deterministically with tie-breaker."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemySourceRepository(mock_session)
    await repo.list_all(active_only=True)

    executed_stmt = mock_session.execute.call_args[0][0]
    sql_str = str(executed_stmt).lower()

    # Check ORDER BY clauses
    assert "order by" in sql_str
    assert "sources.name asc" in sql_str
    assert "sources.created_at desc" in sql_str
    assert "sources.id asc" in sql_str
