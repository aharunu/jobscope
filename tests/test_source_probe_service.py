"""Unit tests for SourceRegistryService health probing and architectural boundaries."""

from __future__ import annotations

import ast
import uuid
from collections.abc import Sequence
from pathlib import Path

import pytest

from backend.application.job_discovery.dtos import (
    SourceBatchProbeResultDTO,
    SourceFilterDTO,
    SourceProbeResultDTO,
)
from backend.application.job_discovery.ports import SourceHealthProbe
from backend.application.job_discovery.services import SourceRegistryService
from backend.domain.source import Source
from tests.test_source_service import InMemorySourceRepository


class MockSourceHealthProbe(SourceHealthProbe):
    """In-memory mock implementing SourceHealthProbe port."""

    def __init__(self) -> None:
        self.probed_urls: list[str] = []
        self.probed_batches: list[list[tuple[uuid.UUID, str, str | None]]] = []
        self.next_result: SourceProbeResultDTO | None = None

    async def probe(
        self,
        url: str,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
    ) -> SourceProbeResultDTO:
        self.probed_urls.append(url)
        if self.next_result:
            return self.next_result
        return SourceProbeResultDTO(
            source_id=source_id,
            url=url,
            is_reachable=True,
            status_code=200,
            latency_ms=12.5,
            final_url=url,
            redirect_count=0,
            error_type=None,
            error_message=None,
            ats_type=ats_type,
        )

    async def probe_batch(
        self,
        sources: Sequence[tuple[uuid.UUID, str, str | None]],
        max_concurrency: int = 10,
    ) -> SourceBatchProbeResultDTO:
        self.probed_batches.append(list(sources))
        results = [
            await self.probe(url=u, source_id=sid, ats_type=ats)
            for sid, u, ats in sources
        ]
        reachable = sum(1 for r in results if r.is_reachable)
        return SourceBatchProbeResultDTO(
            total_probed=len(results),
            reachable_count=reachable,
            unreachable_count=len(results) - reachable,
            results=results,
        )


def test_clean_architecture_domain_application_boundaries() -> None:
    """Verify domain and application layers have zero network or infra imports."""
    forbidden_modules = {
        "socket",
        "httpx",
        "requests",
        "urllib.request",
        "ipaddress",
        "backend.infrastructure",
    }

    project_root = Path(__file__).parent.parent
    checked_dirs = [
        project_root / "backend" / "domain",
        project_root / "backend" / "application",
    ]

    for target_dir in checked_dirs:
        for py_file in target_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        for forbidden in forbidden_modules:
                            assert not alias.name.startswith(forbidden), (
                                f"Forbidden import '{alias.name}' found in {py_file}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for forbidden in forbidden_modules:
                        assert not mod.startswith(forbidden), (
                            f"Forbidden import from '{mod}' found in {py_file}"
                        )


@pytest.mark.asyncio
async def test_probe_source_delegates_to_health_probe() -> None:
    """Verify probe_source retrieves entity and delegates to injected probe."""
    source_id = uuid.uuid4()
    source = Source(
        id=source_id,
        name="Trendyol Careers",
        url="https://trendyol.com/careers",
        ats_type="lever",
        company="Trendyol",
        active=True,
    )
    repo = InMemorySourceRepository([source])
    mock_probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=mock_probe)

    result = await service.probe_source(source_id)

    assert result is not None
    assert result.source_id == source_id
    assert result.url == "https://trendyol.com/careers"
    assert result.ats_type == "lever"
    assert result.is_reachable
    assert mock_probe.probed_urls == ["https://trendyol.com/careers"]


@pytest.mark.asyncio
async def test_probe_source_returns_none_for_missing_source() -> None:
    """Verify probe_source returns None when source ID does not exist."""
    repo = InMemorySourceRepository([])
    mock_probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=mock_probe)

    result = await service.probe_source(uuid.uuid4())
    assert result is None
    assert mock_probe.probed_urls == []


@pytest.mark.asyncio
async def test_probe_failure_does_not_mutate_source_active() -> None:
    """CRITICAL: Failed probe must never deactivate or modify Source.active."""
    source_id = uuid.uuid4()
    source = Source(
        id=source_id,
        name="Getir Careers",
        url="https://getir.com/careers",
        ats_type="greenhouse",
        company="Getir",
        active=True,
    )
    repo = InMemorySourceRepository([source])
    mock_probe = MockSourceHealthProbe()
    mock_probe.next_result = SourceProbeResultDTO(
        source_id=source_id,
        url=source.url,
        is_reachable=False,
        status_code=500,
        latency_ms=80.0,
        final_url=source.url,
        redirect_count=0,
        error_type="server_error",
        error_message="HTTP server error: 500",
        ats_type=source.ats_type,
    )
    service = SourceRegistryService(repository=repo, health_probe=mock_probe)

    result = await service.probe_source(source_id)
    assert result is not None
    assert not result.is_reachable
    assert result.status_code == 500

    # Ensure source in repository remains active=True and untouched
    persisted_source = await repo.get_by_id(source_id)
    assert persisted_source is not None
    assert persisted_source.active is True


@pytest.mark.asyncio
async def test_probe_sources_batch_delegates_filtered_list() -> None:
    """Verify probe_sources_batch applies filter and passes targets to probe_batch."""
    s1 = Source(
        id=uuid.uuid4(),
        name="Source 1",
        url="https://s1.com",
        ats_type="greenhouse",
        active=True,
    )
    s2 = Source(
        id=uuid.uuid4(),
        name="Source 2",
        url="https://s2.com",
        ats_type="lever",
        active=False,
    )
    s3 = Source(
        id=uuid.uuid4(),
        name="Source 3",
        url="https://s3.com",
        ats_type="greenhouse",
        active=True,
    )
    repo = InMemorySourceRepository([s1, s2, s3])
    mock_probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=mock_probe)

    filter_dto = SourceFilterDTO(active_only=True, ats_type="greenhouse")
    batch_result = await service.probe_sources_batch(
        filter_=filter_dto, max_concurrency=5
    )

    assert batch_result.total_probed == 2
    assert batch_result.reachable_count == 2
    assert len(mock_probe.probed_batches) == 1
    passed_targets = mock_probe.probed_batches[0]
    assert len(passed_targets) == 2
    assert {t[0] for t in passed_targets} == {s1.id, s3.id}


@pytest.mark.asyncio
async def test_probe_sources_batch_empty_results() -> None:
    """Verify probe_sources_batch returns empty summary when no sources match."""
    repo = InMemorySourceRepository([])
    mock_probe = MockSourceHealthProbe()
    service = SourceRegistryService(repository=repo, health_probe=mock_probe)

    batch_result = await service.probe_sources_batch()
    assert batch_result.total_probed == 0
    assert batch_result.reachable_count == 0
    assert batch_result.unreachable_count == 0
    assert batch_result.results == []
    assert len(mock_probe.probed_batches) == 0


@pytest.mark.asyncio
async def test_probe_raises_if_probe_port_not_injected() -> None:
    """Verify RuntimeError is raised if health_probe is None on service."""
    repo = InMemorySourceRepository([])
    service = SourceRegistryService(repository=repo, health_probe=None)

    with pytest.raises(RuntimeError, match="Health probe port is not configured"):
        await service.probe_source(uuid.uuid4())

    with pytest.raises(RuntimeError, match="Health probe port is not configured"):
        await service.probe_sources_batch()
