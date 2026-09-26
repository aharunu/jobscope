"""Unit and contract tests for Greenhouse ATS Adapter."""

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
from backend.infrastructure.ats.greenhouse import (
    GreenhouseAdapter,
    extract_greenhouse_board_token,
)

# ==============================================================================
# Helpers and Test Doubles
# ==============================================================================


def make_greenhouse_source(
    name: str = "Gram Games",
    url: str = "https://boards.greenhouse.io/gramgamescareers",
    company: str | None = "Gram Games",
    adapter_config: dict[str, Any] | None = None,
    pagination_config: dict[str, Any] | None = None,
    endpoint_config: dict[str, Any] | None = None,
    rate_limit_config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> RuntimeSourceDTO:
    """Construct a test RuntimeSourceDTO configured for Greenhouse."""
    return RuntimeSourceDTO(
        id=uuid.uuid4(),
        name=name,
        url=url,
        ats_type="greenhouse",
        company=company,
        country="TR",
        adapter_config=adapter_config or {},
        pagination_config=pagination_config or {},
        endpoint_config=endpoint_config or {},
        rate_limit_config=rate_limit_config or {},
        metadata=metadata or {},
    )


class MockSafeHttpClient(SafeHttpClient):
    """Mock SafeHttpClient for testing adapters without external network access."""

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
            return SafeHttpResponseDTO(
                status_code=200, url=url, text='{"jobs": [], "meta": {"total": 0}}'
            )
        return self.responses.pop(0)


SAMPLE_GREENHOUSE_POSTINGS = [
    {
        "id": 4829101,
        "internal_job_id": 1001,
        "title": "Senior Backend Engineer - Python",
        "absolute_url": "https://boards.greenhouse.io/gramgamescareers/jobs/4829101",
        "location": {"name": "Istanbul, Turkey"},
        "updated_at": "2026-09-01T10:30:00Z",
        "requisition_id": "ENG-4829",
        "content": (
            "&lt;p&gt;We are looking for a Senior Backend Engineer "
            "proficient in Python and FastAPI.&lt;/p&gt;"
        ),
        "departments": [{"id": 201, "name": "Engineering"}],
        "offices": [{"id": 301, "name": "Istanbul Office"}],
    },
    {
        "id": 4829102,
        "internal_job_id": 1002,
        "title": "Data Analyst",
        "absolute_url": "https://boards.greenhouse.io/gramgamescareers/jobs/4829102",
        "location": {"name": "Istanbul, Turkey"},
        "updated_at": "2026-09-02T11:00:00Z",
        "requisition_id": "DATA-4830",
        "content": (
            "&lt;p&gt;Looking for a Data Analyst with SQL and Python "
            "experience.&lt;/p&gt;"
        ),
        "departments": [{"id": 202, "name": "Data & Analytics"}],
        "offices": [{"id": 301, "name": "Istanbul Office"}],
    },
]

# ==============================================================================
# Protocol & ATS Type Tests
# ==============================================================================


def test_greenhouse_adapter_implements_protocol_and_ats_type() -> None:
    """Verify GreenhouseAdapter satisfies ATSAdapter protocol
    with ats_type == 'greenhouse'.
    """
    adapter = GreenhouseAdapter(http_client=MockSafeHttpClient())
    assert isinstance(adapter, ATSAdapter)
    assert adapter.ats_type == "greenhouse"


# ==============================================================================
# Token Extraction Tests
# ==============================================================================


def test_extract_token_from_standard_boards_url() -> None:
    source = make_greenhouse_source(url="https://boards.greenhouse.io/gramgamescareers")
    assert extract_greenhouse_board_token(source) == "gramgamescareers"


def test_extract_token_from_job_boards_url() -> None:
    source = make_greenhouse_source(url="https://job-boards.greenhouse.io/oliver")
    assert extract_greenhouse_board_token(source) == "oliver"


def test_extract_token_from_job_boards_eu_url() -> None:
    source = make_greenhouse_source(
        url="https://job-boards.eu.greenhouse.io/constructortech"
    )
    assert extract_greenhouse_board_token(source) == "constructortech"


def test_extract_token_from_embed_query_url() -> None:
    source = make_greenhouse_source(
        url="https://boards.greenhouse.io/embed/job_board?for=twitch"
    )
    assert extract_greenhouse_board_token(source) == "twitch"


def test_extract_token_from_api_url() -> None:
    source = make_greenhouse_source(
        url="https://boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs?content=true"
    )
    assert extract_greenhouse_board_token(source) == "gramgamescareers"


def test_extract_token_from_url_with_subpath() -> None:
    source = make_greenhouse_source(url="https://boards.greenhouse.io/okx/jobs/12345")
    assert extract_greenhouse_board_token(source) == "okx"


def test_extract_token_explicit_config_override() -> None:
    source = make_greenhouse_source(
        url="https://boards.greenhouse.io/wrongtoken",
        adapter_config={"board_token": "correct_token"},
    )
    assert extract_greenhouse_board_token(source) == "correct_token"


def test_extract_token_fallback_keys_in_config() -> None:
    for key in ("site_token", "token", "company_slug"):
        source = make_greenhouse_source(
            url="https://boards.greenhouse.io/ignored",
            adapter_config={key: f"token_via_{key}"},
        )
        assert extract_greenhouse_board_token(source) == f"token_via_{key}"


def test_extract_token_rejects_non_greenhouse_hostnames() -> None:
    source = make_greenhouse_source(url="https://careers.greenhouse-corp.com/jobs")
    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        extract_greenhouse_board_token(source)
    assert "does not belong to Greenhouse" in exc_info.value.message


def test_extract_token_rejects_missing_url() -> None:
    source = make_greenhouse_source(url="")
    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        extract_greenhouse_board_token(source)
    assert "has no URL configured" in exc_info.value.message


def test_extract_token_rejects_unresolvable_url() -> None:
    source = make_greenhouse_source(url="https://boards.greenhouse.io/")
    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        extract_greenhouse_board_token(source)
    assert "Cannot resolve Greenhouse board token" in exc_info.value.message


def test_extract_token_rejects_template_tokens() -> None:
    source = make_greenhouse_source(url="https://boards.greenhouse.io/<token>")
    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        extract_greenhouse_board_token(source)
    assert "Cannot resolve Greenhouse board token" in exc_info.value.message


# ==============================================================================
# Crawl & DiscoveredJobDTO Mapping Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_adapter_crawls_and_maps_dto() -> None:
    """Verify standard Greenhouse crawl maps to DiscoveredJobDTO
    with expected fields.
    """
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs",
                text=json.dumps({"jobs": SAMPLE_GREENHOUSE_POSTINGS}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)

    assert isinstance(result, CrawlResultDTO)
    assert result.source_id == source.id
    assert result.ats_type == "greenhouse"
    assert len(result.jobs) == 2
    assert result.raw_payload_count == 2
    assert result.is_complete is True
    assert result.warnings == []

    # Verify first job mapping
    job1 = result.jobs[0]
    assert isinstance(job1, DiscoveredJobDTO)
    assert job1.external_job_id == "4829101"
    assert job1.title == "Senior Backend Engineer - Python"
    assert job1.url == "https://boards.greenhouse.io/gramgamescareers/jobs/4829101"
    assert job1.content_type == "application/json"
    assert json.loads(job1.raw_content)["id"] == 4829101
    assert job1.metadata["company"] == "Gram Games"
    assert job1.metadata["location"] == "Istanbul, Turkey"
    assert job1.metadata["board_token"] == "gramgamescareers"
    assert job1.metadata["requisition_id"] == "ENG-4829"
    assert job1.metadata["internal_job_id"] == 1001
    assert "proficient in Python" in job1.metadata["description"]
    assert job1.metadata["departments"] == [{"id": 201, "name": "Engineering"}]
    assert job1.metadata["offices"] == [{"id": 301, "name": "Istanbul Office"}]


@pytest.mark.asyncio
async def test_greenhouse_adapter_fallback_canonical_url() -> None:
    """When absolute_url is missing, generate canonical fallback URL."""
    item = dict(SAMPLE_GREENHOUSE_POSTINGS[0])
    item.pop("absolute_url")

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="https://boards-api.greenhouse.io/v1/boards/gramgamescareers/jobs",
                text=json.dumps({"jobs": [item]}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)
    assert len(result.jobs) == 1
    assert (
        result.jobs[0].url
        == "https://boards.greenhouse.io/gramgamescareers/jobs/4829101"
    )


@pytest.mark.asyncio
async def test_greenhouse_adapter_skips_postings_without_valid_id() -> None:
    """Postings missing id or having empty id must be skipped with warning."""
    items = [
        {"title": "No ID job", "absolute_url": "https://boards.greenhouse.io/job/1"},
        {"id": "   ", "title": "Whitespace ID job"},
        SAMPLE_GREENHOUSE_POSTINGS[0],
    ]
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": items}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)
    assert len(result.jobs) == 1
    assert result.jobs[0].external_job_id == "4829101"
    assert len(result.warnings) == 2
    assert "Skipped posting without valid ID" in result.warnings[0]


@pytest.mark.asyncio
async def test_greenhouse_adapter_skips_non_dict_items() -> None:
    """Non-dict items in jobs array must be skipped with warning."""
    items = ["not-a-dict", 12345, SAMPLE_GREENHOUSE_POSTINGS[0]]
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": items}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)
    assert len(result.jobs) == 1
    assert len(result.warnings) == 2
    assert "Skipped non-dict item" in result.warnings[0]


# ==============================================================================
# Deduplication and Title Collision Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_adapter_deduplicates_by_job_id_within_crawl() -> None:
    """Duplicate job IDs across pages are not emitted twice."""
    page1 = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]
    page2 = [
        SAMPLE_GREENHOUSE_POSTINGS[0],  # Duplicate of page 1 job
        {
            "id": 9999999,
            "title": "Staff DevOps Engineer",
            "absolute_url": "https://boards.greenhouse.io/job/9999999",
        },
    ]
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page1})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page2})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"page_size": 2, "max_pages": 5})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 3
    job_ids = [j.external_job_id for j in result.jobs]
    assert job_ids == ["4829101", "4829102", "9999999"]


@pytest.mark.asyncio
async def test_greenhouse_adapter_does_not_merge_distinct_jobs_with_same_title() -> (
    None
):
    """Jobs with identical titles but different external IDs
    are preserved separately.
    """
    items = [
        {
            "id": 101,
            "title": "Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/job/101",
        },
        {
            "id": 102,
            "title": "Software Engineer",
            "absolute_url": "https://boards.greenhouse.io/job/102",
        },
    ]
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": items})
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)
    assert len(result.jobs) == 2
    assert result.jobs[0].external_job_id == "101"
    assert result.jobs[1].external_job_id == "102"
    assert result.jobs[0].title == result.jobs[1].title == "Software Engineer"


# ==============================================================================
# Empty Board Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_adapter_handles_valid_empty_board() -> None:
    """A board returning 0 jobs terminates naturally as complete with 0 jobs."""
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": [], "meta": {"total": 0}}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    result = await adapter.crawl(source)
    assert len(result.jobs) == 0
    assert result.raw_payload_count == 0
    assert result.is_complete is True
    assert result.warnings == []
    assert result.metadata["pages_fetched"] == 1


# ==============================================================================
# Pagination & Completeness Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_adapter_multi_page_natural_exhaustion() -> None:
    """Multi-page pagination terminates with is_complete=True
    when page has < page_size items.
    """
    page1 = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]
    page2 = [
        {
            "id": 9999999,
            "title": "Staff DevOps Engineer",
            "absolute_url": "https://boards.greenhouse.io/job/9999999",
        }
    ]
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page1})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page2})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"page_size": 2, "max_pages": 5})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 3
    assert result.metadata["pages_fetched"] == 2
    assert "pagination_max_pages_reached" not in result.warnings
    assert result.is_complete is True

    # Verify params passed
    assert len(mock_http.requests) == 2
    assert mock_http.requests[0]["params"] == {
        "content": "true",
        "page": 1,
        "per_page": 2,
    }
    assert mock_http.requests[1]["params"] == {
        "content": "true",
        "page": 2,
        "per_page": 2,
    }


@pytest.mark.asyncio
async def test_greenhouse_adapter_multi_page_empty_final_page() -> None:
    """Multi-page pagination terminates with is_complete=True
    when final page returns 0 items.
    """
    page1 = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]
    page2: list[dict[str, Any]] = []

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page1})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page2})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"page_size": 2, "max_pages": 5})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 2
    assert result.metadata["pages_fetched"] == 2
    assert result.is_complete is True


@pytest.mark.asyncio
async def test_greenhouse_adapter_pagination_max_pages_warning() -> None:
    """Reaching max_pages when full page returned records warning
    and sets is_complete=False.
    """
    page_full = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]
    page_full_2 = [
        {
            "id": 1001,
            "title": "Job 1",
            "absolute_url": "https://boards.greenhouse.io/job/1001",
        },
        {
            "id": 1002,
            "title": "Job 2",
            "absolute_url": "https://boards.greenhouse.io/job/1002",
        },
    ]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page_full})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page_full_2})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"page_size": 2, "max_pages": 2})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 4
    assert result.metadata["pages_fetched"] == 2
    assert "pagination_max_pages_reached" in result.warnings
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_greenhouse_adapter_loop_protection_duplicate_page() -> None:
    """When server returns identical non-empty page, break to prevent infinite loop."""
    page_full = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page_full})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page_full})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"page_size": 2, "max_pages": 10})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 2
    assert result.metadata["pages_fetched"] == 2
    assert "duplicate_page_detected" in result.warnings
    assert result.is_complete is False


@pytest.mark.asyncio
async def test_greenhouse_adapter_pagination_mode_none() -> None:
    """When pagination_mode == 'none', completes after single fetch
    without page params.
    """
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text=json.dumps({"jobs": SAMPLE_GREENHOUSE_POSTINGS}),
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(pagination_config={"pagination_mode": "none"})

    result = await adapter.crawl(source)
    assert len(result.jobs) == 2
    assert result.is_complete is True
    assert mock_http.requests[0]["params"] == {"content": "true"}


@pytest.mark.asyncio
async def test_greenhouse_adapter_respects_rate_limit_delay() -> None:
    """Rate limit delay is triggered between pagination requests."""
    page1 = [SAMPLE_GREENHOUSE_POSTINGS[0], SAMPLE_GREENHOUSE_POSTINGS[1]]
    page2 = [SAMPLE_GREENHOUSE_POSTINGS[0]]

    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page1})
            ),
            SafeHttpResponseDTO(
                status_code=200, url="...", text=json.dumps({"jobs": page2})
            ),
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source(
        pagination_config={"page_size": 2, "max_pages": 5},
        rate_limit_config={"delay_seconds": 0.5},
    )

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await adapter.crawl(source)
        assert len(result.jobs) == 2
        mock_sleep.assert_awaited_once_with(0.5)


# ==============================================================================
# Upstream Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_greenhouse_adapter_404_raises_invalid_source_config() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=404, url="...", text="Not Found")]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(InvalidSourceConfigurationError) as exc_info:
        await adapter.crawl(source)
    assert "not found (HTTP 404)" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_429_raises_adapter_execution_error() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=429, url="...", text="Too Many Requests")]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(AdapterExecutionError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
    assert "Rate limited" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_500_raises_adapter_execution_error() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=500, url="...", text="Internal Server Error")]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(AdapterExecutionError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
    assert "upstream server error" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_unexpected_status_raises_error() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=418, url="...", text="I'm a teapot")]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(AdapterExecutionError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
    assert "Unexpected HTTP status 418" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_malformed_json_raises_malformed_result() -> None:
    mock_http = MockSafeHttpClient(
        [
            SafeHttpResponseDTO(
                status_code=200,
                url="...",
                text="<html><body>Bad Gateway</body></html>",
            )
        ]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(MalformedAdapterResultError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "MALFORMED_ADAPTER_RESULT"
    assert "not valid JSON" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_non_dict_json_raises_malformed_result() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=200, url="...", text="[1, 2, 3]")]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(MalformedAdapterResultError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "MALFORMED_ADAPTER_RESULT"
    assert "Expected JSON object" in exc_info.value.message


@pytest.mark.asyncio
async def test_greenhouse_adapter_missing_jobs_list_raises_malformed_result() -> None:
    mock_http = MockSafeHttpClient(
        [SafeHttpResponseDTO(status_code=200, url="...", text='{"status": "ok"}')]
    )
    adapter = GreenhouseAdapter(http_client=mock_http)
    source = make_greenhouse_source()

    with pytest.raises(MalformedAdapterResultError) as exc_info:
        await adapter.crawl(source)
    assert exc_info.value.code == "MALFORMED_ADAPTER_RESULT"
    assert "Expected 'jobs' list" in exc_info.value.message


# ==============================================================================
# Architecture Cleanliness Tests
# ==============================================================================


def test_greenhouse_adapter_architecture_cleanliness() -> None:
    """Verify GreenhouseAdapter satisfies clean architecture boundaries."""
    from pathlib import Path

    adapter_path = Path("backend/infrastructure/ats/greenhouse/adapter.py")
    assert adapter_path.exists(), "adapter.py must exist"

    with open(adapter_path, encoding="utf-8") as f:
        source_code = f.read()

    # 1. No direct httpx import
    assert "httpx" not in source_code, "Must not import or reference httpx directly"

    # 2. No direct database or SQLAlchemy imports
    assert "sqlalchemy" not in source_code, "Must not import SQLAlchemy"
    assert "JobRepository" not in source_code, "Must not import JobRepository"

    # 3. No requirement extraction dependency
    assert "JobRequirementRepository" not in source_code, (
        "Must not import JobRequirementRepository"
    )
    assert "RequirementExtractionService" not in source_code, (
        "Must not import RequirementExtractionService"
    )

    # 4. No matching or scoring logic
    assert (
        "score" not in source_code.lower()
        or "score"
        in [
            # ignore generic words if any, but ensure no matching algorithms
        ]
    ), "Must not contain matching/scoring logic"
