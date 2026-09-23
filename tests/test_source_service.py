"""Unit tests for SourceRegistryService."""

from __future__ import annotations

import sys
import uuid

import pytest

from backend.application.job_discovery.dtos import SourceCreateDTO, SourceFilterDTO
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source import Source, SourceRepository


class InMemorySourceRepository(SourceRepository):
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


def test_application_service_layer_independence() -> None:
    """Verify that SourceRegistryService does not import ORM models or SQLAlchemy."""
    mod = sys.modules.get("backend.application.job_discovery.services")
    assert mod is not None, "backend.application.job_discovery.services not loaded"
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"Application service imports SQLAlchemy: {attr_name}"
            )
            assert (
                "infrastructure.database.models" not in attr_val.__module__.lower()
            ), f"Application service imports ORM models: {attr_name}"


@pytest.mark.asyncio
async def test_service_list_sources_default() -> None:
    """Verify list_sources returns all sources when no filter is provided."""
    s1 = Source(name="Alpha", url="https://alpha.com", ats_type="lever", active=True)
    s2 = Source(
        name="Beta", url="https://beta.com", ats_type="greenhouse", active=False
    )
    repo = InMemorySourceRepository([s1, s2])
    service = SourceRegistryService(repo)

    result = await service.list_sources()

    assert len(result) == 2
    assert result[0].name == "Alpha"
    assert result[1].name == "Beta"


@pytest.mark.asyncio
async def test_service_list_sources_with_filter() -> None:
    """Verify list_sources applies active_only and ats_type filters."""
    s1 = Source(name="Alpha", url="https://alpha.com", ats_type="lever", active=True)
    s2 = Source(
        name="Beta", url="https://beta.com", ats_type="greenhouse", active=False
    )
    s3 = Source(
        name="Gamma", url="https://gamma.com", ats_type="greenhouse", active=True
    )
    repo = InMemorySourceRepository([s1, s2, s3])
    service = SourceRegistryService(repo)

    # Filter active only
    active_sources = await service.list_sources(SourceFilterDTO(active_only=True))
    assert len(active_sources) == 2
    assert {s.name for s in active_sources} == {"Alpha", "Gamma"}

    # Filter ats_type greenhouse
    gh_sources = await service.list_sources(SourceFilterDTO(ats_type="greenhouse"))
    assert len(gh_sources) == 2
    assert {s.name for s in gh_sources} == {"Beta", "Gamma"}

    # Filter active AND greenhouse
    active_gh = await service.list_sources(
        SourceFilterDTO(active_only=True, ats_type="greenhouse")
    )
    assert len(active_gh) == 1
    assert active_gh[0].name == "Gamma"


@pytest.mark.asyncio
async def test_service_count_sources() -> None:
    """Verify count_sources counts according to filters."""
    s1 = Source(name="Alpha", url="https://alpha.com", ats_type="lever", active=True)
    s2 = Source(name="Beta", url="https://beta.com", ats_type="lever", active=False)
    repo = InMemorySourceRepository([s1, s2])
    service = SourceRegistryService(repo)

    total = await service.count_sources()
    assert total == 2

    active_count = await service.count_sources(active_only=True)
    assert active_count == 1

    lever_active = await service.count_sources(active_only=True, ats_type="lever")
    assert lever_active == 1

    workday_count = await service.count_sources(ats_type="workday")
    assert workday_count == 0


@pytest.mark.asyncio
async def test_service_get_source_by_id_and_url() -> None:
    """Verify get_source and get_source_by_url retrieve expected entity."""
    test_id = uuid.uuid4()
    s = Source(
        id=test_id,
        name="Target Source",
        url="https://target.com",
        ats_type="ashby",
    )
    repo = InMemorySourceRepository([s])
    service = SourceRegistryService(repo)

    found_by_id = await service.get_source(test_id)
    assert found_by_id is not None
    assert found_by_id.id == test_id

    not_found = await service.get_source(uuid.uuid4())
    assert not_found is None

    found_by_url = await service.get_source_by_url("https://target.com")
    assert found_by_url is not None
    assert found_by_url.name == "Target Source"

    not_found_url = await service.get_source_by_url("https://nonexistent.com")
    assert not_found_url is None


@pytest.mark.asyncio
async def test_service_register_source() -> None:
    """Verify register_source constructs domain entity and persists via repository."""
    repo = InMemorySourceRepository()
    service = SourceRegistryService(repo)

    dto = SourceCreateDTO(
        name="Peak Games Greenhouse",
        url="https://boards.greenhouse.io/peakgames",
        ats_type="greenhouse",
        company="Peak Games",
        country="TR",
        adapter_config={"board_token": "peakgames"},
    )

    created = await service.register_source(dto)

    assert isinstance(created, Source)
    assert created.name == "Peak Games Greenhouse"
    assert created.company == "Peak Games"
    assert created.adapter_config == {"board_token": "peakgames"}
    assert created.id in repo.sources


@pytest.mark.asyncio
async def test_service_save_sources_bulk() -> None:
    """Verify save_sources persists multiple sources."""
    repo = InMemorySourceRepository()
    service = SourceRegistryService(repo)

    s1 = Source(name="S1", url="https://s1.com", ats_type="lever")
    s2 = Source(name="S2", url="https://s2.com", ats_type="workday")

    saved = await service.save_sources([s1, s2])

    assert len(saved) == 2
    assert len(repo.sources) == 2
