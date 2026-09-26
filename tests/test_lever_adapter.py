"""Unit tests for Lever ATS Adapter."""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
)
from backend.application.job_discovery.ports import ATSAdapter, SafeHttpClient
from backend.infrastructure.ats.lever import LeverAdapter, extract_lever_site_token

# ==============================================================================
# Helpers and Test Doubles
# ==============================================================================


def make_runtime_source(
    name: str = "Trendyol",
    url: str = "https://jobs.lever.co/trendyol",
    company: str | None = "Trendyol",
    adapter_config: dict[str, Any] | None = None,
    pagination_config: dict[str, Any] | None = None,
    endpoint_config: dict[str, Any] | None = None,
    rate_limit_config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RuntimeSourceDTO:
    """Construct a test RuntimeSourceDTO."""
    return RuntimeSourceDTO(
        id=uuid.uuid4(),
        name=name,
        url=url,
        ats_type="lever",
        company=company,
        country="TR",
        adapter_config=adapter_config or {},
        pagination_config=pagination_config or {},
        endpoint_config=endpoint_config or {},
        rate_limit_config=rate_limit_config or {},
        metadata=metadata or {},
    )


class MockSafeHttpClient(SafeHttpClient):
    """Mock SafeHttpClient for unit testing adapters without network."""

    def __init__(self, responses: list[SafeHttpResponseDTO] | None = None) -> None:
        self.responses = list(responses or [])
        self.requests: list[dict[str, Any]] = []

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        self.requests.append(
            {"url": url, "headers": headers, "params": params, "timeout": timeout}
        )
        if not self.responses:
            return SafeHttpResponseDTO(status_code=200, url=url, text="[]")
        return self.responses.pop(0)


SAMPLE_LEVER_POSTINGS = [
    {
        "id": "e2f18374-1234-4a5b-8c9d-abcdef012345",
        "text": "Senior Backend Engineer - Python",
        "hostedUrl": "https://jobs.lever.co/trendyol/e2f18374-1234-4a5b-8c9d-abcdef012345",
        "applyUrl": "https://jobs.lever.co/trendyol/e2f18374-1234-4a5b-8c9d-abcdef012345/apply",
        "createdAt": 1718000000000,
        "workplaceType": "hybrid",
        "categories": {
            "department": "Engineering",
            "team": "Search & Recommendations",
            "location": "Istanbul, Turkey",
            "commitment": "Full time",
        },
    },
    {
        "id": "a1b2c3d4-5678-4e9f-0a1b-cdef12345678",
        "text": "Data Analyst",
        "hostedUrl": "https://jobs.lever.co/trendyol/a1b2c3d4-5678-4e9f-0a1b-cdef12345678",
        "applyUrl": "https://jobs.lever.co/trendyol/a1b2c3d4-5678-4e9f-0a1b-cdef12345678/apply",
        "createdAt": 1718100000000,
        "workplaceType": "remote",
        "categories": {
            "department": "Data & Analytics",
            "team": "Analytics",
            "location": "Ankara, Turkey",
            "commitment": "Full time",
        },
    },
]

# ==============================================================================
# Token Extraction Tests
# ==============================================================================


def test_extract_token_from_standard_lever_url() -> None:
    source = make_runtime_source(url="https://jobs.lever.co/trendyol")
    assert extract_lever_site_token(source) == "trendyol"


def test_extract_token_with_hyphen_and_subpath() -> None:
    source = make_runtime_source(url="https://jobs.lever.co/trendyol-go/some-role")
    assert extract_lever_site_token(source) == "trendyol-go"


def test_extract_token_with_query_params() -> None:
    source = make_runtime_source(url="https://jobs.lever.co/trendyol?department=Dolap")
    assert extract_lever_site_token(source) == "trendyol"


def test_extract_token_from_api_url() -> None:
    source = make_runtime_source(
        url="https://api.lever.co/v0/postings/papara?mode=json"
    )
    assert extract_lever_site_token(source) == "papara"


def test_extract_token_config_override() -> None:
    source = make_runtime_source(
        url="https://example.com/careers",
        adapter_config={"site_token": "insiderone"},
    )
    assert extract_lever_site_token(source) == "insiderone"


def test_extract_token_rejects_unilever_substring_false_positive() -> None:
    """careers.unilever.com contains 'lever.co' as substring but is NOT Lever ATS."""
    source = make_runtime_source(
        name="Unilever",
        url="https://careers.unilever.com/location/istanbul-turkey-jobs/34155/298795-745042/3",
    )
    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        extract_lever_site_token(source)
    assert "does not belong to Lever" in exc_info.value.message


def test_extract_token_missing_token_raises() -> None:
    source = make_runtime_source(url="https://jobs.lever.co/")
    with pytest.raises(InvalidSourceConfigurationError):
        extract_lever_site_token(source)


# ==============================================================================
# Adapter Crawl & Mapping Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_lever_adapter_successful_job_discovery() -> None:
    """Verify Lever postings are parsed into DiscoveredJobDTOs conforming
    to the exact contract.
    """
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/trendyol?mode=json&limit=100",
                text=json.dumps(SAMPLE_LEVER_POSTINGS),
            )
        ]
    )

    adapter = LeverAdapter(http_client=mock_http)
    assert isinstance(adapter, ATSAdapter)
    assert adapter.ats_type == "lever"

    source = make_runtime_source(
        name="Trendyol",
        url="https://jobs.lever.co/trendyol",
        company="Trendyol",
    )

    result = await adapter.crawl(source)

    assert isinstance(result, CrawlResultDTO)
    assert result.source_id == source.id
    assert result.ats_type == "lever"
    assert result.raw_payload_count == 2
    assert len(result.jobs) == 2
    assert result.warnings == []
    assert result.metadata["site_token"] == "trendyol"
    assert result.metadata["pages_fetched"] == 1

    job1 = result.jobs[0]
    assert isinstance(job1, DiscoveredJobDTO)
    assert job1.external_job_id == "e2f18374-1234-4a5b-8c9d-abcdef012345"
    assert (
        job1.url
        == "https://jobs.lever.co/trendyol/e2f18374-1234-4a5b-8c9d-abcdef012345"
    )
    assert job1.title == "Senior Backend Engineer - Python"
    assert job1.content_type == "application/json"
    assert "Senior Backend Engineer" in job1.raw_content

    # Invariant: metadata contains location, company, payload_hash, etc.
    assert job1.metadata["company"] == "Trendyol"
    assert job1.metadata["location"] == "Istanbul, Turkey"
    assert job1.metadata["workplace_type"] == "hybrid"
    assert job1.metadata["site_token"] == "trendyol"
    assert len(job1.metadata["payload_hash"]) == 64


@pytest.mark.asyncio
async def test_lever_adapter_handles_empty_postings() -> None:
    """Empty JSON array should yield a clean CrawlResultDTO with 0 jobs."""
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/trendyol?mode=json&limit=100",
                text="[]",
            )
        ]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    result = await adapter.crawl(source)
    assert result.raw_payload_count == 0
    assert result.jobs == []
    assert result.warnings == []


# ==============================================================================
# Pagination and Max Pages Warning Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_lever_adapter_multi_page_pagination() -> None:
    """Multi-page pagination terminates when a page has fewer than page_size items."""
    # Page size 2; page 1 returns 2 items; page 2 returns 1 item
    page1 = [SAMPLE_LEVER_POSTINGS[0], SAMPLE_LEVER_POSTINGS[1]]
    page2 = [
        {
            "id": "third-job-id",
            "text": "Product Manager",
            "hostedUrl": "https://jobs.lever.co/trendyol/third-job-id",
        }
    ]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/trendyol",
                text=json.dumps(page1),
            ),
            SafeHttpResponseDTO(
                status_code=200,
                url="https://api.lever.co/v0/postings/trendyol",
                text=json.dumps(page2),
            ),
        ]
    )

    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source(pagination_config={"page_size": 2, "max_pages": 5})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 3
    assert result.metadata["pages_fetched"] == 2
    assert "pagination_max_pages_reached" not in result.warnings

    # Verify second request passed skip=last_id
    assert len(mock_http.requests) == 2
    assert (
        mock_http.requests[1]["params"]["skip"]
        == "a1b2c3d4-5678-4e9f-0a1b-cdef12345678"
    )


@pytest.mark.asyncio
async def test_lever_adapter_records_pagination_max_pages_reached_warning() -> None:
    """Reaching max_pages when more jobs exist must record warning."""
    page_full = [SAMPLE_LEVER_POSTINGS[0], SAMPLE_LEVER_POSTINGS[1]]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(status_code=200, url="...", text=json.dumps(page_full)),
            SafeHttpResponseDTO(status_code=200, url="...", text=json.dumps(page_full)),
        ]
    )

    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source(pagination_config={"page_size": 2, "max_pages": 2})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 4
    assert result.metadata["pages_fetched"] == 2
    assert "pagination_max_pages_reached" in result.warnings


@pytest.mark.asyncio
async def test_lever_adapter_respects_rate_limit_delay() -> None:
    """Verify rate limit delay is triggered between pagination requests."""
    page_full = [SAMPLE_LEVER_POSTINGS[0], SAMPLE_LEVER_POSTINGS[1]]
    page_end = [SAMPLE_LEVER_POSTINGS[0]]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(status_code=200, url="...", text=json.dumps(page_full)),
            SafeHttpResponseDTO(status_code=200, url="...", text=json.dumps(page_end)),
        ]
    )

    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source(
        pagination_config={"page_size": 2, "max_pages": 5},
        rate_limit_config={"delay_seconds": 0.5},
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await adapter.crawl(source)
        assert len(result.jobs) == 3
        # Should have slept once between page 1 and page 2
        mock_sleep.assert_awaited_once_with(0.5)


# ==============================================================================
# Upstream Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_lever_adapter_404_raises_invalid_source_config() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=404, url="...", text="Not Found")]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        await adapter.crawl(source)
    assert "not found (HTTP 404)" in exc_info.value.message


@pytest.mark.asyncio
async def test_lever_adapter_429_raises_adapter_execution_error() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=429, url="...", text="Too Many Requests")]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    with pytest.raises(AdapterExecutionError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
    assert "Rate limited" in exc_info.value.message


@pytest.mark.asyncio
async def test_lever_adapter_500_raises_adapter_execution_error() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=500, url="...", text="Internal Server Error")]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    with pytest.raises(AdapterExecutionError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
    assert "upstream server error" in exc_info.value.message


@pytest.mark.asyncio
async def test_lever_adapter_malformed_json_raises_malformed_result() -> None:
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text="<html><body>Gateway Error</body></html>",
            )
        ]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    with pytest.raises(MalformedAdapterResultError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "MALFORMED_ADAPTER_RESULT"
    assert "not valid JSON" in exc_info.value.message


@pytest.mark.asyncio
async def test_lever_adapter_non_list_json_raises_malformed_result() -> None:
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text='{"error": "something went wrong"}',
            )
        ]
    )
    adapter = LeverAdapter(http_client=mock_http)
    source = make_runtime_source()

    with pytest.raises(MalformedAdapterResultError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "MALFORMED_ADAPTER_RESULT"
    assert "Expected JSON list" in exc_info.value.message
