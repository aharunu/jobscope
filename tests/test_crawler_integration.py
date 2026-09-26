"""Integration tests for the complete Crawler & ATS Adapter pipeline."""

from __future__ import annotations

import json
import uuid

import pytest

from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    CrawlExecutionResultDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
)
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.source.entities import Source
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.interfaces.api.main import create_app
from tests.test_lever_adapter import SAMPLE_LEVER_POSTINGS, MockSafeHttpClient


class InMemoryRuntimeSourceProvider:
    """In-memory test double for RuntimeSourceProvider."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self.sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_crawlable_source(
        self, source_id: uuid.UUID
    ) -> RuntimeSourceDTO | None:
        source = self.sources.get(source_id)
        if not source or not source.active:
            return None
        return RuntimeSourceDTO.from_domain(source)

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        matching = [s for s in self.sources.values() if s.active]
        if ats_type is not None:
            matching = [s for s in matching if s.ats_type == ats_type]
        sliced = matching[offset : offset + limit if limit else None]
        return [RuntimeSourceDTO.from_domain(s) for s in sliced]


@pytest.mark.asyncio
async def test_end_to_end_crawler_pipeline_with_lever() -> None:
    """Verify full pipeline:
    Provider -> Orchestrator -> Registry -> LeverAdapter -> MockHttpClient.
    """
    source = Source(
        id=uuid.uuid4(),
        name="Trendyol Careers",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/trendyol?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            )
        ]
    )

    registry = create_adapter_registry(http_client=mock_http)
    assert registry.is_supported("lever")

    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
    )

    result = await orchestrator.crawl_source(source.id)

    assert isinstance(result, CrawlExecutionResultDTO)
    assert result.success is True
    assert result.status == CrawlStatus.COMPLETED
    assert result.source_id == source.id
    assert result.source_name == "Trendyol Careers"
    assert result.ats_type == "lever"
    assert result.jobs_found == 2
    assert result.error_type is None
    assert result.crawl_result is not None
    assert len(result.crawl_result.jobs) == 2

    # Verify DiscoveredJobDTO contract
    job = result.crawl_result.jobs[0]
    assert job.external_job_id == "e2f18374-1234-4a5b-8c9d-abcdef012345"
    assert job.title == "Senior Backend Engineer - Python"
    assert job.metadata["company"] == "Trendyol"
    assert job.metadata["location"] == "Istanbul, Turkey"


@pytest.mark.asyncio
async def test_end_to_end_crawler_handles_upstream_404_cleanly() -> None:
    """Verify upstream 404 produces a graceful failed CrawlExecutionResultDTO."""
    source = Source(
        id=uuid.uuid4(),
        name="Deleted Lever Board",
        url="https://jobs.lever.co/nonexistent-board",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])

    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=404, url="...", text="Not Found")]
    )
    registry = create_adapter_registry(http_client=mock_http)
    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
    )

    result = await orchestrator.crawl_source(source.id)

    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "INVALID_SOURCE_CONFIG"
    assert "not found (HTTP 404)" in (result.error_message or "")
    assert result.jobs_found == 0


@pytest.mark.asyncio
async def test_end_to_end_crawl_multiple_sources() -> None:
    """Verify crawl_sources_by_ats_type runs sequentially and isolates errors."""
    source_good = Source(
        id=uuid.uuid4(),
        name="Good Lever Board",
        url="https://jobs.lever.co/good",
        ats_type="lever",
        active=True,
    )
    source_bad = Source(
        id=uuid.uuid4(),
        name="Bad Lever Board",
        url="https://jobs.lever.co/bad",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source_good, source_bad])

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps(SAMPLE_LEVER_POSTINGS[:1]),
            ),
            SafeHttpResponseDTO(status_code=500, url="...", text="Error"),
        ]
    )
    registry = create_adapter_registry(http_client=mock_http)
    orchestrator = CrawlerOrchestrator(provider, registry)

    results = await orchestrator.crawl_sources_by_ats_type(ats_type="lever")

    assert len(results) == 2
    assert results[0].success is True
    assert results[0].jobs_found == 1
    assert results[1].success is False
    assert results[1].error_type == "ADAPTER_EXECUTION_FAILURE"


@pytest.mark.asyncio
async def test_fastapi_lifespan_manages_http_safe_client_and_registry() -> None:
    """Verify FastAPI application lifespan initializes and cleanly closes clients."""
    app = create_app()

    # Before lifespan: uninitialized
    assert getattr(app.state, "http_safe_client", None) is None
    assert getattr(app.state, "adapter_registry", None) is None

    async with app.router.lifespan_context(app):
        # During lifespan: initialized and shared
        client = getattr(app.state, "http_safe_client", None)
        assert client is not None
        registry = getattr(app.state, "adapter_registry", None)
        assert registry is not None
        assert registry.is_supported("lever")

    # After lifespan: closed and cleared
    assert getattr(app.state, "http_safe_client", None) is None
