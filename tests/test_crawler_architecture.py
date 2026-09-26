"""Unit and contract tests for Phase 4.1 — Crawler & ATS Adapter Architecture."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from backend.application.job_discovery import (
    AdapterExecutionError,
    AdapterUnavailableError,
    ATSAdapter,
    ATSAdapterRegistry,
    CrawlerError,
    CrawlerOrchestrator,
    CrawlExecutionResultDTO,
    CrawlResultDTO,
    DiscoveredJobDTO,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
    RuntimeSourceDTO,
    RuntimeSourceProvider,
    SafeHttpClient,
    SafeHttpResponseDTO,
    UnsupportedATSError,
)
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.source.entities import Source

# ==============================================================================
# Test Fixtures and Test Doubles
# ==============================================================================


class DummyValidAdapter:
    """Mock adapter conforming to ATSAdapter protocol."""

    def __init__(
        self,
        ats_type: str = "lever",
        jobs_to_return: list[DiscoveredJobDTO] | None = None,
        should_fail_with: Exception | None = None,
    ) -> None:
        self._ats_type = ats_type
        self.jobs_to_return = jobs_to_return or []
        self.should_fail_with = should_fail_with
        self.crawled_sources: list[RuntimeSourceDTO] = []

    @property
    def ats_type(self) -> str:
        return self._ats_type

    async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
        self.crawled_sources.append(source)
        if self.should_fail_with:
            raise self.should_fail_with
        return CrawlResultDTO(
            source_id=source.id,
            ats_type=self.ats_type,
            jobs=list(self.jobs_to_return),
            raw_payload_count=len(self.jobs_to_return),
            warnings=[],
            metadata={"mock": True},
        )


class DummyHttpClient:
    """Mock client conforming to SafeHttpClient protocol."""

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        return SafeHttpResponseDTO(
            status_code=200,
            url=url,
            headers={"content-type": "application/json"},
            text='{"mock": "response"}',
        )


class InMemoryRuntimeSourceProvider(RuntimeSourceProvider):
    """In-memory mock provider implementing RuntimeSourceProvider protocol."""

    def __init__(self, sources: list[Source] | None = None) -> None:
        self._sources: dict[uuid.UUID, Source] = {s.id: s for s in (sources or [])}

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        res = [s for s in self._sources.values() if s.active]
        if ats_type is not None:
            res = [s for s in res if s.ats_type.lower() == ats_type.lower()]
        res.sort(key=lambda s: (s.name, str(s.id)))
        if offset:
            res = res[offset:]
        if limit is not None:
            res = res[:limit]
        return [RuntimeSourceDTO.from_domain(s) for s in res]

    async def get_crawlable_source(
        self,
        source_id: uuid.UUID,
    ) -> RuntimeSourceDTO | None:
        source = self._sources.get(source_id)
        if source is None or not source.active:
            return None
        return RuntimeSourceDTO.from_domain(source)


# ==============================================================================
# 1. ATS Adapter & SafeHttpClient Port Conformance Tests
# ==============================================================================


def test_ats_adapter_protocol_runtime_checkable() -> None:
    """Verify ATSAdapter protocol conforms to runtime_checkable expectations."""
    adapter = DummyValidAdapter(ats_type="lever")
    assert isinstance(adapter, ATSAdapter)

    # Class missing ats_type
    class MissingAtsType:
        async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
            raise NotImplementedError

    assert not isinstance(MissingAtsType(), ATSAdapter)

    # Class missing crawl method
    class MissingCrawl:
        @property
        def ats_type(self) -> str:
            return "lever"

    assert not isinstance(MissingCrawl(), ATSAdapter)


def test_safe_http_client_protocol_runtime_checkable() -> None:
    """Verify SafeHttpClient protocol conforms to runtime_checkable expectations."""
    client = DummyHttpClient()
    assert isinstance(client, SafeHttpClient)

    class IncompleteClient:
        pass

    assert not isinstance(IncompleteClient(), SafeHttpClient)


def test_safe_http_response_dto_attributes() -> None:
    """Verify SafeHttpResponseDTO encapsulates HTTP response fields cleanly."""
    dto = SafeHttpResponseDTO(
        status_code=200,
        url="https://api.lever.co/v0/postings/test",
        headers={"content-type": "application/json"},
        text='[{"id": "1"}]',
        content_bytes=b'[{"id": "1"}]',
    )
    assert dto.status_code == 200
    assert dto.url == "https://api.lever.co/v0/postings/test"
    assert dto.headers["content-type"] == "application/json"
    assert dto.text == '[{"id": "1"}]'
    assert dto.content_bytes == b'[{"id": "1"}]'


# ==============================================================================
# 2. ATS Adapter Registry & Resolution Tests
# ==============================================================================


def test_adapter_registry_registration_and_lookup() -> None:
    """Verify registering and looking up adapters works deterministically."""
    registry = ATSAdapterRegistry()
    lever_adapter = DummyValidAdapter(ats_type="lever")
    greenhouse_adapter = DummyValidAdapter(ats_type="greenhouse")

    registry.register(lever_adapter)
    registry.register(greenhouse_adapter)

    assert registry.is_supported("lever") is True
    assert registry.is_supported("greenhouse") is True
    assert registry.is_supported("workday") is False

    assert registry.get_adapter("lever") is lever_adapter
    # Case-insensitivity and whitespace trimming
    assert registry.get_adapter("LEVER") is lever_adapter
    assert registry.get_adapter("  greenhouse  ") is greenhouse_adapter
    assert registry.list_supported_types() == ["greenhouse", "lever"]


def test_adapter_registry_resolving_known_ats_without_adapter_raises() -> None:
    """Verify resolving known ATS without registered adapter raises expected error."""
    registry = ATSAdapterRegistry()
    # "workday" is a KnownATSType, but not registered
    with pytest.raises(AdapterUnavailableError) as exc_info:
        registry.get_adapter("workday")

    err = exc_info.value
    assert err.code == "ADAPTER_UNAVAILABLE"
    assert err.details == {"ats_type": "workday"}
    assert "No adapter is registered" in err.message


def test_adapter_registry_resolving_unknown_ats_raises_unsupported() -> None:
    """Verify resolving an arbitrary unknown ATS type raises UnsupportedATSError."""
    registry = ATSAdapterRegistry()
    with pytest.raises(UnsupportedATSError) as exc_info:
        registry.get_adapter("unrecognized_custom_platform")

    err = exc_info.value
    assert err.code == "UNSUPPORTED_ATS_TYPE"
    assert err.details == {"ats_type": "unrecognized_custom_platform"}
    assert "Unsupported ATS platform type" in err.message


def test_adapter_registry_init_with_sequence() -> None:
    """Verify ATSAdapterRegistry can be initialized with a sequence of adapters."""
    lever = DummyValidAdapter(ats_type="lever")
    ashby = DummyValidAdapter(ats_type="ashby")
    registry = ATSAdapterRegistry([lever, ashby])

    assert registry.is_supported("lever") is True
    assert registry.is_supported("ashby") is True
    assert registry.list_supported_types() == ["ashby", "lever"]


# ==============================================================================
# 3. Crawler Application Exceptions Hierarchy
# ==============================================================================


def test_crawler_exceptions_hierarchy_and_codes() -> None:
    """Verify crawler exceptions inherit from CrawlerError and carry codes."""
    assert issubclass(UnsupportedATSError, CrawlerError)
    assert issubclass(AdapterUnavailableError, CrawlerError)
    assert issubclass(InvalidSourceConfigurationError, CrawlerError)
    assert issubclass(AdapterExecutionError, CrawlerError)
    assert issubclass(MalformedAdapterResultError, CrawlerError)

    err1 = UnsupportedATSError("Unknown ATS", details={"ats_type": "foo"})
    assert err1.code == "UNSUPPORTED_ATS_TYPE"
    assert err1.details == {"ats_type": "foo"}

    err2 = AdapterExecutionError("Upstream timeout", details={"source_id": "123"})
    assert err2.code == "ADAPTER_EXECUTION_FAILURE"
    assert err2.details == {"source_id": "123"}

    err3 = InvalidSourceConfigurationError("Missing board token")
    assert err3.code == "INVALID_SOURCE_CONFIG"

    err4 = MalformedAdapterResultError("Missing title field")
    assert err4.code == "MALFORMED_ADAPTER_RESULT"


# ==============================================================================
# 4. Crawl Result DTO vs Crawl Execution Result DTO Separation
# ==============================================================================


def test_crawl_result_and_execution_result_separation() -> None:
    """Verify adapter output is decoupled from orchestrator execution metadata."""
    source_id = uuid.uuid4()
    job = DiscoveredJobDTO(
        external_job_id="job-101",
        url="https://jobs.lever.co/acme/job-101",
        title="Backend Engineer",
        raw_content='{"id": "job-101", "title": "Backend Engineer"}',
        content_type="application/json",
        metadata={
            "company": "Acme Corp",
            "location": "Istanbul, Turkey",
        },
    )

    # Adapter output: contains ONLY discovery payload
    adapter_result = CrawlResultDTO(
        source_id=source_id,
        ats_type="lever",
        jobs=[job],
        raw_payload_count=1,
        warnings=[],
        metadata={"board": "acme"},
    )
    assert len(adapter_result.jobs) == 1
    assert adapter_result.raw_payload_count == 1
    assert not hasattr(adapter_result, "duration_ms")
    assert not hasattr(adapter_result, "success")

    # Orchestrator result: wraps execution lifecycle metadata and adapter output
    exec_result = CrawlExecutionResultDTO(
        source_id=source_id,
        source_name="Acme Lever",
        ats_type="lever",
        status=CrawlStatus.COMPLETED,
        success=True,
        jobs_found=1,
        duration_ms=45.2,
        crawl_result=adapter_result,
    )
    assert exec_result.success is True
    assert exec_result.status == CrawlStatus.COMPLETED
    assert exec_result.jobs_found == 1
    assert exec_result.duration_ms == 45.2
    assert exec_result.crawl_result is adapter_result


# ==============================================================================
# 5. Crawler Orchestrator Execution & Error Isolation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_crawl_source_successful_execution() -> None:
    """Verify crawling valid active source executes adapter and returns success."""
    source = Source(
        name="Trendyol Lever",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])

    discovered_job = DiscoveredJobDTO(
        external_job_id="ty-1",
        url="https://jobs.lever.co/trendyol/ty-1",
        title="Software Engineer",
        raw_content='{"id": "ty-1"}',
        content_type="application/json",
    )
    lever_adapter = DummyValidAdapter(ats_type="lever", jobs_to_return=[discovered_job])
    registry = ATSAdapterRegistry([lever_adapter])

    orchestrator = CrawlerOrchestrator(
        source_provider=provider,
        adapter_registry=registry,
    )

    result = await orchestrator.crawl_source(source.id)

    assert isinstance(result, CrawlExecutionResultDTO)
    assert result.source_id == source.id
    assert result.source_name == "Trendyol Lever"
    assert result.ats_type == "lever"
    assert result.status == CrawlStatus.COMPLETED
    assert result.success is True
    assert result.jobs_found == 1
    assert result.duration_ms >= 0.0
    assert result.error_type is None
    assert result.crawl_result is not None
    assert len(result.crawl_result.jobs) == 1

    # Invariant: Adapter strictly receives RuntimeSourceDTO, not domain Source
    assert len(lever_adapter.crawled_sources) == 1
    crawled_source = lever_adapter.crawled_sources[0]
    assert isinstance(crawled_source, RuntimeSourceDTO)
    assert crawled_source.id == source.id


@pytest.mark.asyncio
async def test_crawl_source_missing_or_inactive_source_returns_failure() -> None:
    """Verify non-existent or inactive source returns structured failure."""
    active_source = Source(
        name="Active",
        url="https://active.com",
        ats_type="lever",
        active=True,
    )
    inactive_source = Source(
        name="Inactive",
        url="https://inactive.com",
        ats_type="lever",
        active=False,
    )
    provider = InMemoryRuntimeSourceProvider([active_source, inactive_source])
    registry = ATSAdapterRegistry([DummyValidAdapter(ats_type="lever")])
    orchestrator = CrawlerOrchestrator(provider, registry)

    # 1. Non-existent ID
    non_existent_id = uuid.uuid4()
    result_missing = await orchestrator.crawl_source(non_existent_id)
    assert result_missing.source_id == non_existent_id
    assert result_missing.success is False
    assert result_missing.status == CrawlStatus.FAILED
    assert result_missing.error_type == "SOURCE_NOT_FOUND_OR_INACTIVE"
    assert "does not exist or is not active" in (result_missing.error_message or "")

    # 2. Inactive source ID (refused by RuntimeSourceProvider)
    result_inactive = await orchestrator.crawl_source(inactive_source.id)
    assert result_inactive.source_id == inactive_source.id
    assert result_inactive.success is False
    assert result_inactive.status == CrawlStatus.FAILED
    assert result_inactive.error_type == "SOURCE_NOT_FOUND_OR_INACTIVE"


@pytest.mark.asyncio
async def test_crawl_source_unsupported_ats_records_failure() -> None:
    """Verify source with unrecognized ats_type records UNSUPPORTED_ATS_TYPE failure."""
    source = Source(
        name="Custom Source",
        url="https://custom.com/jobs",
        ats_type="unrecognized_ats_xyz",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    registry = ATSAdapterRegistry()  # empty
    orchestrator = CrawlerOrchestrator(provider, registry)

    result = await orchestrator.crawl_source(source.id)
    assert result.source_id == source.id
    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "UNSUPPORTED_ATS_TYPE"
    assert "Unsupported ATS platform type" in (result.error_message or "")


@pytest.mark.asyncio
async def test_crawl_source_known_ats_without_adapter_records_unavailable() -> None:
    """Verify source with recognized ATS but no adapter records ADAPTER_UNAVAILABLE."""
    source = Source(
        name="Greenhouse Source",
        url="https://boards.greenhouse.io/acme",
        ats_type="greenhouse",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    registry = ATSAdapterRegistry()  # greenhouse not registered
    orchestrator = CrawlerOrchestrator(provider, registry)

    result = await orchestrator.crawl_source(source.id)
    assert result.source_id == source.id
    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "ADAPTER_UNAVAILABLE"
    assert "No adapter is registered" in (result.error_message or "")


@pytest.mark.asyncio
async def test_crawl_source_adapter_crawler_error_isolation() -> None:
    """Verify adapter raising CrawlerError is captured gracefully."""
    source = Source(
        name="Failing Lever",
        url="https://jobs.lever.co/failing",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    failing_adapter = DummyValidAdapter(
        ats_type="lever",
        should_fail_with=AdapterExecutionError(
            message="Remote server 503 Service Unavailable",
            details={"status_code": 503},
        ),
    )
    registry = ATSAdapterRegistry([failing_adapter])
    orchestrator = CrawlerOrchestrator(provider, registry)

    result = await orchestrator.crawl_source(source.id)
    assert result.source_id == source.id
    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "ADAPTER_EXECUTION_FAILURE"
    assert "Remote server 503" in (result.error_message or "")


@pytest.mark.asyncio
async def test_crawl_source_unexpected_exception_isolation() -> None:
    """Verify unexpected runtime exceptions in adapter are caught and formatted."""
    source = Source(
        name="Crashing Lever",
        url="https://jobs.lever.co/crashing",
        ats_type="lever",
        active=True,
    )
    provider = InMemoryRuntimeSourceProvider([source])
    crashing_adapter = DummyValidAdapter(
        ats_type="lever",
        should_fail_with=RuntimeError("Unexpected memory corruption"),
    )
    registry = ATSAdapterRegistry([crashing_adapter])
    orchestrator = CrawlerOrchestrator(provider, registry)

    result = await orchestrator.crawl_source(source.id)
    assert result.source_id == source.id
    assert result.success is False
    assert result.status == CrawlStatus.FAILED
    assert result.error_type == "UNEXPECTED_EXECUTION_ERROR"
    assert "Unexpected memory corruption" in (result.error_message or "")


@pytest.mark.asyncio
async def test_crawl_sources_sequential_iteration_and_error_isolation() -> None:
    """Verify batch crawl iterates sequentially and isolates errors between sources."""
    s1 = Source(name="S1", url="https://s1.com", ats_type="lever", active=True)
    s2 = Source(name="S2 Bad", url="https://s2.com", ats_type="lever", active=True)
    s3 = Source(name="S3", url="https://s3.com", ats_type="lever", active=True)
    s4 = Source(name="S4 Inact", url="https://s4.com", ats_type="lever", active=False)

    provider = InMemoryRuntimeSourceProvider([s1, s2, s3, s4])

    class ConditionalAdapter:
        @property
        def ats_type(self) -> str:
            return "lever"

        async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
            if "Bad" in source.name:
                raise AdapterExecutionError("Connection reset by peer")
            return CrawlResultDTO(
                source_id=source.id,
                ats_type="lever",
                jobs=[
                    DiscoveredJobDTO(
                        external_job_id=f"job-{source.name}",
                        url=f"https://lever.co/{source.name}",
                        title="Engineer",
                        raw_content="{}",
                        content_type="application/json",
                    )
                ],
            )

    registry = ATSAdapterRegistry([ConditionalAdapter()])
    orchestrator = CrawlerOrchestrator(provider, registry)

    # 1. Crawl all active sources for ATS type "lever"
    results = await orchestrator.crawl_sources_by_ats_type("lever")

    # Inactive source s4 was not returned by provider
    assert len(results) == 3

    # Error isolation: s1 succeeds, s2 fails, s3 succeeds
    assert results[0].success is True
    assert results[0].jobs_found == 1

    assert results[1].success is False
    assert results[1].error_type == "ADAPTER_EXECUTION_FAILURE"

    assert results[2].success is True
    assert results[2].jobs_found == 1

    # 2. Crawl all active sources
    all_results = await orchestrator.crawl_all_active_sources()
    assert len(all_results) == 3
