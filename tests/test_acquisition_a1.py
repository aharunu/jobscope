"""Offline reference contracts and real ingestion/closure regressions for A1."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import SafeHttpResponseDTO
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
)
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.ats.greenhouse import GreenhouseAdapter
from backend.infrastructure.ats.lever import LeverAdapter
from tests.test_greenhouse_adapter import (
    SAMPLE_GREENHOUSE_POSTINGS,
    MockSafeHttpClient,
    make_greenhouse_source,
)
from tests.test_greenhouse_crawler_integration import (
    InMemoryCrawlRunRepository,
    InMemoryJobRepository,
    InMemoryRawJobRepository,
    InMemoryRuntimeSourceProvider,
)
from tests.test_lever_adapter import SAMPLE_LEVER_POSTINGS, make_runtime_source


def response(payload, status=200):
    return SafeHttpResponseDTO(
        status_code=status, url="https://provider.example", text=json.dumps(payload)
    )


def posting(i):
    return {"id": f"job-{i}", "text": f"Role {i}", "descriptionPlain": "Build systems."}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "count,offsets", [(0, [0]), (100, [0, 100]), (150, [0, 100]), (200, [0, 100, 200])]
)
async def test_lever_exhaustion_and_exact_request_contract(count, offsets):
    items = [posting(i) for i in range(count)]
    pages = [items[start : start + 100] for start in offsets]
    client = MockSafeHttpClient([response(page) for page in pages])
    source = make_runtime_source(
        url="https://jobs.lever.co/trendyol?location=Remote&team=Data"
    )
    result = await LeverAdapter(client).crawl(source)
    assert result.is_complete and not result.warnings
    assert len(result.jobs) == result.raw_payload_count == count
    assert [r["params"] for r in client.requests] == [
        {"mode": "json", "limit": 100, "skip": offset} for offset in offsets
    ]
    assert all(
        r["url"] == "https://api.lever.co/v0/postings/trendyol" for r in client.requests
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("second", [[posting(0), posting(1)], [posting(1), posting(2)]])
async def test_lever_repeat_overlap_keeps_unique_jobs_and_stops(second):
    client = MockSafeHttpClient([response([posting(0), posting(1)]), response(second)])
    result = await LeverAdapter(client).crawl(
        make_runtime_source(pagination_config={"page_size": 2})
    )
    assert not result.is_complete
    assert "duplicate_or_overlapping_page_detected" in result.warnings
    ids = [j.external_job_id for j in result.jobs]
    assert len(ids) == len(set(ids))
    assert len(client.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_id", [None, "", " ", True, False, {}, [], 1.5, 0, "../bad"]
)
@pytest.mark.parametrize("provider", ["lever", "greenhouse"])
async def test_bad_identity_is_skipped_and_coverage_incomplete(provider, bad_id):
    if provider == "lever":
        items = [posting(0), dict(posting(1), id=bad_id)]
        payload = items
        source = make_runtime_source()
        adapter = LeverAdapter
    else:
        items = [
            SAMPLE_GREENHOUSE_POSTINGS[0],
            dict(SAMPLE_GREENHOUSE_POSTINGS[1], id=bad_id),
        ]
        payload = {"jobs": items, "meta": {"total": 2}}
        source = make_greenhouse_source()
        adapter = GreenhouseAdapter
    result = await adapter(MockSafeHttpClient([response(payload)])).crawl(source)
    assert len(result.jobs) == 1
    assert result.raw_payload_count == 2
    assert not result.is_complete and result.warnings


@pytest.mark.asyncio
@pytest.mark.parametrize("total", [None, True, False, -1, "2", 2.0, {}, [], 0, 1, 3])
async def test_greenhouse_invalid_or_mismatched_totals_never_complete(total):
    payload = {"jobs": SAMPLE_GREENHOUSE_POSTINGS, "meta": {"total": total}}
    result = await GreenhouseAdapter(MockSafeHttpClient([response(payload)])).crawl(
        make_greenhouse_source()
    )
    assert len(result.jobs) == 2
    assert not result.is_complete and result.warnings


@pytest.mark.asyncio
@pytest.mark.parametrize("meta", [None, {}, [], "bad"])
async def test_greenhouse_missing_total_is_explicitly_incomplete(meta):
    result = await GreenhouseAdapter(
        MockSafeHttpClient([response({"jobs": [], "meta": meta})])
    ).crawl(make_greenhouse_source())
    assert result.warnings == ["missing_or_invalid_total"]
    assert not result.is_complete


@pytest.mark.asyncio
async def test_greenhouse_prospect_full_content_and_update_date_preserved():
    item = copy.deepcopy(SAMPLE_GREENHOUSE_POSTINGS[0])
    item.update(
        internal_job_id=None,
        content="&lt;p&gt;" + "Long content " * 100 + "&lt;/p&gt;",
        metadata=[{"name": "Employment", "value": "Full-time"}],
    )
    source = make_greenhouse_source()
    result = await GreenhouseAdapter(
        MockSafeHttpClient([response({"jobs": [item], "meta": {"total": 1}})])
    ).crawl(source)
    dto = result.jobs[0]
    canonical = JobNormalizer().normalize(dto, source)
    assert result.is_complete and not result.warnings
    assert dto.external_job_id == str(item["id"])
    assert json.loads(dto.raw_content) == item
    assert len(canonical.description) > 1000
    assert dto.metadata["updated_at_upstream"] == item["updated_at"]
    assert canonical.published_at is None
    assert canonical.employment_type is None and canonical.work_mode is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "commitment,expected",
    [
        ("Full time", "Full-time"),
        ("FULL-TIME", "Full-time"),
        ("Parttime", "Part-time"),
        ("Contract", "Contract"),
        ("Intern", "Internship"),
        ("Internship", "Internship"),
        ("Temporary", None),
        (None, None),
    ],
)
@pytest.mark.parametrize(
    "workplace,mode",
    [
        ("remote", "Remote"),
        ("HYBRID", "Hybrid"),
        ("on-site", "On-site"),
        ("onsite", "On-site"),
        ("unknown", None),
        (None, None),
    ],
)
async def test_lever_structured_values_only(commitment, expected, workplace, mode):
    item = dict(
        posting(0),
        categories={"location": "Remote", "commitment": commitment},
        workplaceType=workplace,
    )
    source = make_runtime_source()
    result = await LeverAdapter(MockSafeHttpClient([response([item])])).crawl(source)
    canonical = JobNormalizer().normalize(result.jobs[0], source)
    assert canonical.employment_type == expected and canonical.work_mode == mode
    assert json.loads(result.jobs[0].raw_content) == item
    assert result.jobs[0].metadata["provider"]["commitment"] == commitment


@pytest.mark.asyncio
async def test_lever_full_description_responsibilities_and_raw():
    item = copy.deepcopy(SAMPLE_LEVER_POSTINGS[0])
    item.update(
        description="<p>Opening and body " + "Python " * 100 + "</p>",
        descriptionBody="SHOULD NOT DUPLICATE BODY",
        descriptionPlain="Opening and body " + "Python " * 100,
        lists=[
            {"text": "Responsibilities", "content": "<ul><li>Build APIs</li></ul>"},
            {"text": "Requirements", "content": "<ul><li>SQL experience</li></ul>"},
        ],
        additional="<p>Closing benefits</p>",
        additionalPlain="Closing benefits",
    )
    source = make_runtime_source()
    dto = (
        await LeverAdapter(MockSafeHttpClient([response([item])])).crawl(source)
    ).jobs[0]
    canonical = JobNormalizer().normalize(dto, source)
    assert len(canonical.description) > 700
    assert (
        "SQL experience" in canonical.description
        and "Closing benefits" in canonical.description
    )
    assert "SHOULD NOT DUPLICATE" not in canonical.description
    assert "Build APIs" in canonical.responsibilities
    assert dto.metadata["apply_url"] == item["applyUrl"]
    assert dto.metadata["team"] == item["categories"]["team"]
    assert json.loads(dto.raw_content) == item
    assert dto.content_type == "application/json"
    assert (
        canonical.published_at is None
    )  # createdAt is not a verified publication contract


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["lever", "greenhouse"])
async def test_missing_optional_description_never_uses_raw_json(provider):
    source = make_runtime_source() if provider == "lever" else make_greenhouse_source()
    payload = (
        [posting(0)]
        if provider == "lever"
        else {"jobs": [{"id": 1, "title": "Role"}], "meta": {"total": 1}}
    )
    if provider == "lever":
        payload[0].pop("descriptionPlain")
    adapter = LeverAdapter if provider == "lever" else GreenhouseAdapter
    result = await adapter(MockSafeHttpClient([response(payload)])).crawl(source)
    job = JobNormalizer().normalize(result.jobs[0], source)
    assert job.description == job.title
    assert result.is_complete


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "settings",
    [
        {"pagination_config": {"pagination_mode": "cursor"}},
        {"pagination_config": {"page_size": True}},
        {"pagination_config": {"page_size": "100"}},
        {"pagination_config": {"page_size": 0}},
        {"pagination_config": {"max_pages": -1}},
        {"pagination_config": {"max_pages": False}},
        {"pagination_config": {"max_pages": 1001}},
        {"adapter_config": {"region": {}}},
        {"adapter_config": {"region": "eu"}},
        {"endpoint_config": {"base_url": "https://api.eu.lever.co/v0/postings"}},
    ],
)
async def test_lever_invalid_configuration_fails_before_http(settings):
    client = MockSafeHttpClient()
    with pytest.raises(InvalidSourceConfigurationError):
        await LeverAdapter(client).crawl(make_runtime_source(**settings))
    assert not client.requests


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["lever", "greenhouse"])
@pytest.mark.parametrize(
    "settings",
    [
        {"adapter_config": {"token": "../bad"}},
        {"adapter_config": {"token": True}},
        {"adapter_config": {"token": "bad?filter=yes"}},
        {"endpoint_config": {"base_url": "http://127.0.0.1"}},
        {"endpoint_config": {"base_url": "https://evil.example"}},
        {"endpoint_config": {"base_url": 12}},
        {"rate_limit_config": {"delay_seconds": True}},
        {"rate_limit_config": {"delay_seconds": -1}},
        {"rate_limit_config": {"delay_seconds": "0.5"}},
        {"rate_limit_config": {"delay_seconds": float("nan")}},
        {"rate_limit_config": {"delay_seconds": float("inf")}},
    ],
)
async def test_provider_config_validation_is_safe_and_pre_network(provider, settings):
    client = MockSafeHttpClient()
    factory = make_runtime_source if provider == "lever" else make_greenhouse_source
    adapter = LeverAdapter if provider == "lever" else GreenhouseAdapter
    with pytest.raises(InvalidSourceConfigurationError) as error:
        await adapter(client).crawl(factory(**settings))
    assert not client.requests
    assert error.value.code == "INVALID_SOURCE_CONFIG"
    assert "input_value" not in error.value.message


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ["https://jobs.eu.lever.co/example", "https://api.eu.lever.co/v0/postings/example"],
)
async def test_lever_eu_region_is_deterministic(url):
    client = MockSafeHttpClient([response([posting(0)])])
    result = await LeverAdapter(client).crawl(make_runtime_source(url=url))
    assert client.requests[0]["url"] == "https://api.eu.lever.co/v0/postings/example"
    assert result.jobs[0].url == "https://jobs.eu.lever.co/example/job-0"
    assert result.metadata["region"] == "eu"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 429, 500])
async def test_lever_failure_does_not_try_another_region(status):
    client = MockSafeHttpClient([response([], status)])
    with pytest.raises((AdapterExecutionError, InvalidSourceConfigurationError)):
        await LeverAdapter(client).crawl(make_runtime_source())
    assert len(client.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_page", [response([], 503), response({"error": "bad"})])
async def test_lever_later_page_failure_never_returns_partial_as_success(bad_page):
    client = MockSafeHttpClient([response([posting(0)]), bad_page])
    with pytest.raises((AdapterExecutionError, MalformedAdapterResultError)):
        await LeverAdapter(client).crawl(
            make_runtime_source(pagination_config={"page_size": 1})
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "lever_cap",
        "lever_repeat",
        "lever_bad_item",
        "greenhouse_missing_total",
        "greenhouse_mismatch",
        "greenhouse_bad_item",
        "greenhouse_duplicate",
        "complete",
        "empty",
    ],
)
async def test_actual_adapter_results_control_ingestion_and_absence_closure(case):
    source = (
        make_runtime_source() if case.startswith("lever") else make_greenhouse_source()
    )
    client = MockSafeHttpClient()
    if case == "lever_cap":
        source = replace(source, pagination_config={"page_size": 1, "max_pages": 1})
        client.responses = [response([posting(0)])]
    elif case == "lever_repeat":
        source = replace(source, pagination_config={"page_size": 1})
        client.responses = [response([posting(0)]), response([posting(0)])]
    elif case == "lever_bad_item":
        client.responses = [response([posting(0), None])]
    else:
        jobs = [SAMPLE_GREENHOUSE_POSTINGS[0]]
        meta = {"total": 1}
        if case == "greenhouse_missing_total":
            meta = {}
        elif case == "greenhouse_mismatch":
            meta = {"total": 3}
        elif case == "greenhouse_bad_item":
            jobs.append({"id": None})
            meta = {"total": 2}
        elif case == "greenhouse_duplicate":
            jobs.append(jobs[0])
            meta = {"total": 2}
        elif case == "empty":
            jobs, meta = [], {"total": 0}
        client.responses = [response({"jobs": jobs, "meta": meta})]
    adapter = LeverAdapter if source.ats_type == "lever" else GreenhouseAdapter
    result = await adapter(client).crawl(source)
    repo, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    stale_dto = (
        await LeverAdapter(MockSafeHttpClient([response([posting(999)])])).crawl(
            make_runtime_source()
        )
    ).jobs[0]
    stale = JobNormalizer().normalize(stale_dto, source)
    await repo.save(stale)
    summary = await JobIngestionService(repo, raw, runs).ingest_crawl_result(
        source, result
    )
    if case == "complete":
        assert result.is_complete and summary.status == CrawlStatus.COMPLETED
        assert summary.jobs_closed == 1 and stale.status == JobStatus.CLOSED
    else:
        assert summary.status == CrawlStatus.PARTIAL
        assert summary.jobs_closed == 0 and stale.status == JobStatus.ACTIVE
        if case == "empty":
            assert "zero_jobs_discovered_closure_suppressed" in summary.warnings
        else:
            assert not result.is_complete and result.warnings


@pytest.mark.asyncio
async def test_acquisition_failure_records_failed_without_ingestion():
    source = Source(
        name="Example", url="https://jobs.lever.co/example", ats_type="lever"
    )
    from unittest.mock import AsyncMock

    persistence = AsyncMock()
    client = MockSafeHttpClient([response([], 503)])
    result = await CrawlerOrchestrator(
        InMemoryRuntimeSourceProvider([source]),
        ATSAdapterRegistry([LeverAdapter(client)]),
        persistence,
    ).crawl_source(source.id)
    assert result.status == CrawlStatus.FAILED and not result.success
    persistence.execute_ingestion.assert_not_awaited()
    persistence.mark_run_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_lever_over_limit_response_is_not_an_exhaustion_proof():
    client = MockSafeHttpClient([response([posting(0), posting(1)])])
    result = await LeverAdapter(client).crawl(
        make_runtime_source(pagination_config={"page_size": 1})
    )
    assert len(result.jobs) == 2
    assert not result.is_complete
    assert "unexpected_page_size" in result.warnings
    assert len(client.requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["lever", "greenhouse"])
@pytest.mark.parametrize("field_kind", ["title", "url", "description"])
async def test_malformed_essential_fields_are_safe_item_warnings(provider, field_kind):
    if provider == "lever":
        good = posting(0)
        bad = dict(posting(1))
        key = {"title": "text", "url": "hostedUrl", "description": "descriptionPlain"}[
            field_kind
        ]
        bad[key] = {"not": "a string"}
        payload, source, adapter = [good, bad], make_runtime_source(), LeverAdapter
    else:
        good = SAMPLE_GREENHOUSE_POSTINGS[0]
        bad = dict(SAMPLE_GREENHOUSE_POSTINGS[1])
        key = {"title": "title", "url": "absolute_url", "description": "content"}[
            field_kind
        ]
        bad[key] = {"not": "a string"}
        payload = {"jobs": [good, bad], "meta": {"total": 2}}
        source, adapter = make_greenhouse_source(), GreenhouseAdapter
    result = await adapter(MockSafeHttpClient([response(payload)])).crawl(source)
    assert len(result.jobs) == 1
    assert not result.is_complete and result.warnings


@pytest.mark.asyncio
async def test_greenhouse_full_board_larger_than_legacy_page_size():
    jobs = [
        dict(
            SAMPLE_GREENHOUSE_POSTINGS[0],
            id=i + 1,
            absolute_url=f"https://boards.greenhouse.io/example/jobs/{i + 1}",
        )
        for i in range(150)
    ]
    client = MockSafeHttpClient([response({"jobs": jobs, "meta": {"total": 150}})])
    result = await GreenhouseAdapter(client).crawl(
        make_greenhouse_source(pagination_config={"page_size": 100, "max_pages": 1})
    )
    assert result.is_complete and not result.warnings
    assert len(result.jobs) == result.raw_payload_count == 150
    assert len(client.requests) == 1
    assert client.requests[0]["params"] == {"content": "true"}


@pytest.mark.asyncio
async def test_lever_explicit_region_and_base_on_custom_catalog_url():
    client = MockSafeHttpClient([response([posting(0)])])
    source = make_runtime_source(
        url="https://example.com/careers",
        adapter_config={"site_token": "example", "region": "eu"},
        endpoint_config={"base_url": "https://api.eu.lever.co/v0/postings/"},
    )
    result = await LeverAdapter(client).crawl(source)
    assert result.is_complete
    assert client.requests[0]["url"] == "https://api.eu.lever.co/v0/postings/example"


@pytest.mark.asyncio
async def test_rich_mapping_keeps_raw_timing_and_detects_employment_change():
    source = make_runtime_source()
    repo, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    service = JobIngestionService(repo, raw, runs)
    item = dict(
        posting(0), workplaceType="hybrid", categories={"commitment": "Full time"}
    )

    async def ingest():
        result = await LeverAdapter(MockSafeHttpClient([response([item])])).crawl(
            source
        )
        return await service.ingest_crawl_result(source, result)

    first = await ingest()
    job = next(iter(repo.jobs.values()))
    assert first.jobs_created == 1
    assert job.employment_type == "Full-time" and job.work_mode == "Hybrid"
    assert len(raw.raw_jobs) == 1
    item["categories"]["commitment"] = "Contract"
    employment_only = await ingest()
    assert employment_only.jobs_updated == 1
    assert job.employment_type == "Contract"
    assert len(raw.raw_jobs) == 2
    item["descriptionPlain"] = "New full description"
    updated = await ingest()
    assert updated.jobs_updated == 1 and job.employment_type == "Contract"
    assert json.loads(raw.raw_jobs[-1].raw_content) == item
    assert len(raw.raw_jobs) == 3
    job.status, job.closed_at = JobStatus.CLOSED, datetime.now(UTC)
    reopened = await ingest()
    assert (
        reopened.jobs_updated == 1
        and job.status == JobStatus.ACTIVE
        and job.closed_at is None
    )
    assert len(raw.raw_jobs) == 4
