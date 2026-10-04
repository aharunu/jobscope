"""Offline acquisition contracts for every A3 provider; no external board traffic."""

import copy
import json
import socket
import uuid
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest

from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import (
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    AdapterUnavailableError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
)
from backend.application.job_discovery.services import SourceRegistryService
from backend.application.job_processing.extraction import RequirementExtractionService
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.ats.source_binding import NEW_PROVIDERS, source_binding
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)
from backend.infrastructure.http.safe_client import HttpSafeClient
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
    classify_ats_type,
)
from tests.test_greenhouse_crawler_integration import (
    InMemoryCrawlRunRepository,
    InMemoryJobRepository,
    InMemoryJobRequirementRepository,
    InMemoryRawJobRepository,
)
from tests.test_source_sync_service import InMemorySourceRepo, MockCatalogParser

URLS = {
    "ashby": "https://jobs.ashbyhq.com/acme",
    "workday": "https://acme.wd3.myworkdayjobs.com/en-US/Careers",
    "smartrecruiters": "https://careers.smartrecruiters.com/acme",
    "recruitee": "https://acme.recruitee.com",
    "personio": "https://acme.jobs.personio.de",
    "teamtailor": "https://acme.teamtailor.com",
    "workable": "https://apply.workable.com/acme",
    "hirex": "https://app.gethirex.com/o/acme/",
    "bamboohr": "https://acme.bamboohr.com/careers",
    "oracle": "https://acme.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1",
}
DESCRIPTION = "<p>Python, SQL and PostgreSQL experience required.</p>" * 30
PROVEN = {"ashby", "personio", "smartrecruiters"}


def source(provider, **kwargs):
    return RuntimeSourceDTO.from_domain(
        Source(
            name="Acme", company="Acme", url=URLS[provider], ats_type=provider, **kwargs
        )
    )


def job(provider, identifier="1"):
    common = {
        "id": identifier,
        "title": "Python Engineer",
        "description": DESCRIPTION,
        "unmapped": {"retain": [1, 2]},
    }
    if provider == "ashby":
        return {
            **common,
            "jobUrl": f"https://jobs.ashbyhq.com/acme/{identifier}",
            "applyUrl": f"https://jobs.ashbyhq.com/acme/{identifier}/application",
            "descriptionHtml": DESCRIPTION,
            "descriptionPlain": "Full plain description",
            "employmentType": "FullTime",
            "workplaceType": "Remote",
            "location": "Istanbul",
            "isListed": False,
            "secondaryLocations": [{"location": "Ankara"}],
            "publishedAt": "2026-10-01T12:00:00Z",
            "compensation": {"scrapeableCompensationSalarySummary": "$100 - $200"},
        }
    if provider == "workday":
        return {
            **common,
            "externalPath": f"/job/Istanbul/Engineer_R-{identifier}",
            "locationsText": "Istanbul",
            "jobDescription": DESCRIPTION,
            "timeType": "Full time",
            "workplaceType": "Remote",
            "postedOn": "Posted 3 Days Ago",
        }
    if provider == "smartrecruiters":
        return {
            **common,
            "name": "Python Engineer",
            "jobAdUrl": f"https://jobs.smartrecruiters.com/acme/{identifier}-engineer",
            "ref": f"https://api.smartrecruiters.com/v1/companies/acme/postings/{identifier}",
            "jobAd": {
                "sections": {
                    "jobDescription": {"text": DESCRIPTION},
                    "qualifications": {"text": "SQL required"},
                }
            },
            "location": {"city": "Istanbul", "country": "TR", "remote": True},
            "typeOfEmployment": {"label": "Full-time"},
            "releasedDate": "2026-10-01T12:00:00Z",
        }
    if provider == "recruitee":
        return {
            **common,
            "careers_url": f"https://acme.recruitee.com/o/engineer-{identifier}",
            "requirements": "SQL required",
            "city": "Istanbul",
            "country": "TR",
            "employment_type_code": "fulltime",
            "remote": True,
            "published_at": "2026-10-01T12:00:00Z",
        }
    if provider == "personio":
        return (
            f"<position><id>{identifier}</id><name>Python Engineer</name>"
            "<office>Istanbul</office><schedule>full-time</schedule>"
            "<employmentType>permanent</employmentType>"
            "<department>Technology</department><jobDescriptions>"
            "<jobDescription><name>Responsibilities</name>"
            f"<value><![CDATA[{DESCRIPTION}]]></value></jobDescription>"
            "<jobDescription><name>Requirements</name><value>SQL required</value>"
            "</jobDescription></jobDescriptions></position>"
        )
    if provider == "teamtailor":
        return {
            **common,
            "url": f"https://acme.teamtailor.com/jobs/{identifier}-engineer",
            "content_html": DESCRIPTION,
            "date_published": "2026-10-01T12:00:00Z",
            "_jobposting": {
                "employmentType": "FULL_TIME",
                "jobLocationType": "TELECOMMUTE",
                "jobLocation": {"address": {"addressLocality": "Istanbul"}},
            },
        }
    if provider == "workable":
        return {
            **common,
            "url": f"https://apply.workable.com/acme/j/{identifier}/",
            "employment_type": "full_time",
            "telecommuting": True,
            "city": "Istanbul",
            "country": "TR",
            "requirements": "SQL required",
            "published_on": "2026-10-01T12:00:00Z",
        }
    if provider == "hirex":
        return {
            **common,
            "@type": "JobPosting",
            "identifier": {"value": identifier},
            "url": f"https://app.gethirex.com/o/acme/jobs/{identifier}",
            "employmentType": "FULL_TIME",
            "jobLocationType": "TELECOMMUTE",
            "jobLocation": [{"address": {"addressLocality": "Istanbul"}}],
            "datePosted": "2026-10-01",
            "baseSalary": {"currency": "TRY", "value": {"minValue": 100}},
            "validThrough": "2026-12-31",
        }
    if provider == "bamboohr":
        return {
            **common,
            "jobOpeningName": "Python Engineer",
            "jobDescription": DESCRIPTION,
            "location": {"city": "Istanbul", "country": "TR"},
            "employmentStatus": "Full-time",
            "isRemote": True,
        }
    return {
        **common,
        "Id": identifier,
        "Title": "Python Engineer",
        "PrimaryLocation": "Istanbul",
        "ExternalDescriptionStr": DESCRIPTION,
        "ShortDescriptionStr": "Short",
        "WorkplaceTypeCode": "REMOTE",
        "EmploymentType": "Full-time",
        "PostedDate": "2026-10-01",
    }


def payload(provider, rows, total=None, **extra):
    if provider == "personio":
        return "<workzag-jobs>" + "".join(rows) + "</workzag-jobs>"
    if provider == "hirex":
        return (
            '<html><script data-other="x" TYPE="application/ld+json">'
            + json.dumps(
                {
                    "@type": "CollectionPage",
                    "mainEntity": {
                        "@type": "ItemList",
                        "itemListElement": [{"item": item} for item in rows],
                    },
                }
            )
            + "</script></html>"
        )
    keys = {
        "ashby": "jobs",
        "workday": "jobPostings",
        "smartrecruiters": "content",
        "recruitee": "offers",
        "teamtailor": "items",
        "workable": "jobs",
        "bamboohr": "result",
    }
    if provider == "oracle":
        return {
            "items": [
                {
                    "requisitionList": rows,
                    "TotalJobsCount": len(rows) if total is None else total,
                }
            ],
            **extra,
        }
    result = {keys[provider]: rows, **extra}
    if provider in {"workday", "smartrecruiters"}:
        result["total" if provider == "workday" else "totalFound"] = (
            len(rows) if total is None else total
        )
    return result


class FakeClient:
    def __init__(self, *responses, status=200):
        self.responses, self.calls, self.status = list(responses), [], status

    async def get(self, url, **kwargs):
        return self._response("GET", url, kwargs)

    async def post_json(self, url, **kwargs):
        return self._response("POST", url, kwargs)

    def _response(self, method, url, kwargs):
        self.calls.append((method, url, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return SafeHttpResponseDTO(
            self.status,
            url,
            text=value if isinstance(value, str) else json.dumps(value),
        )


async def crawl(provider, *responses, src=None, status=200):
    client = FakeClient(*responses, status=status)
    result = (
        await create_adapter_registry(client)
        .get_adapter(provider)
        .crawl(src or source(provider))
    )
    return result, client


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_normal_rich_fields_and_original_raw(provider):
    rows = [job(provider, "1"), job(provider, "2")]
    result, client = await crawl(provider, payload(provider, rows))
    assert len(result.jobs) == 2 and result.is_complete == (provider in PROVEN)
    assert len(client.calls) == 1
    item = result.jobs[0]
    assert item.external_job_id and item.title == "Python Engineer"
    assert (
        DESCRIPTION in item.metadata["description"]
        and len(item.metadata["description"]) > 300
    )
    assert "Istanbul" in item.metadata["location"]
    assert item.metadata["employment_type"] == "Full-time"
    if provider != "personio":
        assert item.metadata["work_mode"] == "Remote"
        raw = json.loads(item.raw_content)
        assert (raw["list"] if provider == "workday" else raw) == rows[0]
    else:
        assert "<department>Technology</department>" in item.raw_content
        assert item.content_type == "application/xml"
    if not result.is_complete:
        assert result.warnings
    if provider == "workday":
        assert item.metadata["published_at"] is None
        assert "Posted 3 Days Ago" in item.raw_content
    if provider == "ashby":
        assert item.metadata["provider"]["isListed"] is False
        assert item.metadata["salary"] == "$100 - $200"


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_empty_is_not_a_malformed_root(provider):
    result, _ = await crawl(provider, payload(provider, []))
    assert result.jobs == [] and result.is_complete == (provider in PROVEN)


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_malformed_root_fails_or_explicitly_partial_html(provider):
    body = "<html>not a board</html>" if provider == "hirex" else "bad root"
    if provider == "hirex":
        result, _ = await crawl(provider, body)
        assert not result.is_complete and result.warnings
    else:
        with pytest.raises(MalformedAdapterResultError):
            await crawl(provider, body)


def without_identity(provider):
    item = job(provider)
    if provider == "personio":
        return item.replace("<id>1</id>", "")
    item = copy.deepcopy(item)
    for key in ("id", "Id", "identifier", "externalPath", "jobUrl", "url", "shortcode"):
        item.pop(key, None)
    return item


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("defect", ["identity", "duplicate", "malformed"])
async def test_a3_coverage_defects_cannot_be_complete(provider, defect):
    first = job(provider)
    broken = (
        without_identity(provider)
        if defect == "identity"
        else first
        if defect == "duplicate"
        else None
    )
    if provider == "personio" and defect == "malformed":
        broken = "<position><id>bad</id><name /></position>"
    result, _ = await crawl(provider, payload(provider, [first, broken]))
    assert len(result.jobs) == 1 and not result.is_complete and result.warnings


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("status", [401, 404, 429, 503])
async def test_a3_http_errors_are_never_empty_success(provider, status):
    with pytest.raises(AdapterExecutionError) as error:
        await crawl(provider, payload(provider, []), status=status)
    assert error.value.details == {"status_code": status}


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_network_failure_propagates_safe_error(provider):
    with pytest.raises(AdapterExecutionError):
        await crawl(provider, AdapterExecutionError("network failure"))


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("bad", [True, 0, -1, 1001, "10"])
async def test_a3_config_page_size_rejected_before_io(provider, bad):
    client = FakeClient()
    src = replace(source(provider), pagination_config={"page_size": bad})
    with pytest.raises(InvalidSourceConfigurationError):
        await create_adapter_registry(client).get_adapter(provider).crawl(src)
    assert not client.calls


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("bad", [True, -1, "0", float("inf")])
async def test_a3_config_delay_rejected_before_io(provider, bad):
    client = FakeClient()
    src = replace(source(provider), rate_limit_config={"delay_seconds": bad})
    with pytest.raises(InvalidSourceConfigurationError):
        await create_adapter_registry(client).get_adapter(provider).crawl(src)
    assert not client.calls


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_host_spoof_and_board_rebinding_rejected(provider):
    client = FakeClient()
    src = source(provider)
    spoof = src.url.replace("https://", "https://evil.example/")
    assert classify_ats_type(spoof) == "custom"
    for changed in (
        replace(src, url=spoof),
        replace(src, endpoint_config={"base_url": "https://evil.example"}),
        replace(src, adapter_config={"host": "evil.example"}),
    ):
        with pytest.raises(InvalidSourceConfigurationError):
            await create_adapter_registry(client).get_adapter(provider).crawl(changed)
    assert not client.calls


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_real_safe_client_body_budget_network_and_429(provider, monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    src = source(provider)
    body = payload(provider, [job(provider)])
    body = body if isinstance(body, str) else json.dumps(body)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=body))
    ) as client:
        adapter = create_adapter_registry(
            HttpSafeClient(client=client, max_response_bytes=10)
        ).get_adapter(provider)
        with pytest.raises(AdapterExecutionError) as error:
            await adapter.crawl(src)
        assert error.value.code == "RESPONSE_BODY_LIMIT_EXCEEDED"
        adapter = create_adapter_registry(HttpSafeClient(client=client)).get_adapter(
            provider
        )
        with (
            acquisition_scope(AcquisitionBudget(max_bytes=10)),
            pytest.raises(AdapterExecutionError) as error,
        ):
            await adapter.crawl(src)
        assert error.value.code == "ACQUISITION_BUDGET_EXHAUSTED"

    def timeout(request):
        raise httpx.ReadTimeout("sensitive body omitted")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(AdapterExecutionError):
            await (
                create_adapter_registry(HttpSafeClient(client=client))
                .get_adapter(provider)
                .crawl(src)
            )


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_partial_output_uses_real_ingestion_no_absence_closure(provider):
    src = source(provider)
    jobs, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    service = JobIngestionService(jobs, raw, runs, requirement_service=AsyncMock())
    old_result, _ = await crawl(provider, payload(provider, [job(provider, "old")]))
    await service.ingest_crawl_result(src, old_result)
    partial, _ = await crawl(
        provider, payload(provider, [job(provider), without_identity(provider)])
    )
    run = await service.ingest_crawl_result(src, partial)
    assert run.status == CrawlStatus.PARTIAL and run.jobs_closed == 0
    assert len(jobs.jobs) == 2 and all(
        j.status == JobStatus.ACTIVE for j in jobs.jobs.values()
    )


def test_a3_factory_all_twelve_and_explicit_unimplemented():
    registry = create_adapter_registry(FakeClient())
    assert registry.list_supported_types() == sorted(
        ["lever", "greenhouse", *NEW_PROVIDERS]
    )
    with pytest.raises(AdapterUnavailableError):
        registry.get_adapter("kariyer_net")


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
def test_a3_catalog_config_inference_and_spoof(provider):
    url = URLS[provider]
    assert classify_ats_type(url) == provider
    dtos, warnings = MarkdownSourceParser().parse_content(
        f"## Jobs\n- **Acme** — `{url}` — open"
    )
    assert not warnings and dtos[0].adapter_config == source_binding(url, provider)
    assert classify_ats_type(url.replace("https://", "https://credential@")) == "custom"


async def test_a3_catalog_sync_preserves_identity_and_manual_config():
    from backend.domain.source.normalization import normalize_source_url

    domain = Source(
        name="Acme",
        url=normalize_source_url(URLS["workday"]),
        ats_type="workday",
        active=False,
        adapter_config={"site": "Careers"},
        pagination_config={"max_pages": 5},
    )
    repo = InMemorySourceRepo([domain])
    dtos, _ = MarkdownSourceParser().parse_content(
        f"## Jobs\n- **Acme** — `{URLS['workday']}` — open"
    )
    service = SourceRegistryService(repo, MockCatalogParser())
    await service.sync_sources(dtos)
    await service.sync_sources(dtos)
    stored = list(repo.sources.values())
    assert len(stored) == 1 and stored[0].id == domain.id
    assert stored[0].adapter_config == {"site": "Careers"} and not stored[0].active


async def test_a3_cross_provider_real_ingestion_requirements_raw_and_audit():
    jobs, raw, runs, requirements = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
        InMemoryJobRequirementRepository(),
    )
    extraction = RequirementExtractionService(
        requirements, DeterministicRequirementExtractor()
    )
    service = JobIngestionService(jobs, raw, runs, requirement_service=extraction)
    for provider in ("ashby", "workday", "recruitee", "personio", "smartrecruiters"):
        src = source(provider)
        before = len(jobs.jobs), len(raw.raw_jobs), len(runs.runs)
        result, _ = await crawl(provider, payload(provider, [job(provider)]))
        assert before == (len(jobs.jobs), len(raw.raw_jobs), len(runs.runs))
        run = await service.ingest_crawl_result(src, result)
        assert run.jobs_created == 1 and run.jobs_closed == 0
        stored = [j for j in jobs.jobs.values() if j.source_id == src.id]
        assert len(stored) == 1 and stored[0].description != stored[0].title
        assert requirements.requirements[stored[0].id]
    assert (
        len(jobs.jobs) == len(raw.raw_jobs) == len(runs.runs) == len(runs.run_jobs) == 5
    )


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters", "oracle"])
async def test_a3_pagination_beyond_200_without_product_filters(provider):
    rows = [job(provider, str(i + 1)) for i in range(205)]
    src = replace(source(provider), pagination_config={"page_size": 100})
    result, client = await crawl(
        provider,
        *[payload(provider, rows[i : i + 100], total=205) for i in (0, 100, 200)],
        src=src,
    )
    assert len(result.jobs) == 205 and len(client.calls) == 3
    for offset, (method, _url, args) in zip((0, 100, 200), client.calls, strict=True):
        assert (
            "country" not in args.get("params", {})
            and "analyst" not in str(args)
            and "Istanbul" not in str(args)
        )
        if provider == "workday":
            assert method == "POST" and args["json"] == {
                "limit": 100,
                "offset": offset,
                "searchText": "",
                "appliedFacets": {},
            }
        elif provider == "oracle":
            assert f"offset={offset}" in args["params"]["finder"]
            assert "keyword" not in args["params"]["finder"]
        else:
            assert args["params"] == {"limit": 100, "offset": offset}


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters", "oracle"])
@pytest.mark.parametrize(
    "defect", ["repeat", "total_change", "early_empty", "cap", "later_failure"]
)
async def test_a3_paginated_coverage_failures(provider, defect):
    src = replace(
        source(provider),
        pagination_config={"page_size": 1, "max_pages": 1 if defect == "cap" else 5},
    )
    first = payload(provider, [job(provider, "1")], total=3)
    second = payload(
        provider,
        [job(provider, "1" if defect == "repeat" else "2")],
        total=4 if defect == "total_change" else 3,
    )
    if defect == "early_empty":
        second = payload(provider, [], total=3)
    if defect == "later_failure":
        with pytest.raises(AdapterExecutionError):
            await crawl(
                provider, first, AdapterExecutionError("Later page failed"), src=src
            )
    else:
        result, _ = await crawl(provider, first, second, src=src)
        assert not result.is_complete and result.warnings


async def test_a3_workday_required_detail_and_failure():
    item = job("workday")
    item.pop("jobDescription")
    detail = {
        "jobPostingInfo": {
            "title": item["title"],
            "jobDescription": DESCRIPTION,
            "timeType": "Part time",
            "workplaceType": "Hybrid",
            "jobReqId": "R-1",
        }
    }
    result, client = await crawl("workday", payload("workday", [item]), detail)
    assert client.calls[1][0:2] == (
        "GET",
        "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers/job/Istanbul/Engineer_R-1",
    )
    assert json.loads(result.jobs[0].raw_content) == {
        "version": 1,
        "list": item,
        "detail": detail,
    }
    assert result.jobs[0].metadata["employment_type"] == "Part-time"
    with pytest.raises(AdapterExecutionError):
        await crawl(
            "workday",
            payload("workday", [item]),
            AdapterExecutionError("detail failed"),
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://acme.wd3.myworkdayjobs.com/en-US",
        "https://acme.wd3.myworkdayjobs.com/",
        "https://acme.wd3.myworkdayjobs.com/Careers/unexpected",
        "https://acme.wd3.myworkdayjobs.com.evil.example/Careers",
    ],
)
def test_a3_workday_ambiguous_or_spoofed_site_rejected(url):
    with pytest.raises(InvalidSourceConfigurationError):
        source_binding(url, "workday")


async def test_a3_ashby_url_identity_only_and_no_graphql():
    item = job("ashby")
    item.pop("id")
    result, client = await crawl("ashby", payload("ashby", [item]))
    assert result.jobs[0].external_job_id == "1"
    assert client.calls == [
        (
            "GET",
            "https://api.ashbyhq.com/posting-api/job-board/acme",
            {"params": {"includeCompensation": "true"}},
        )
    ]


async def test_a3_smartrecruiters_required_detail_human_url():
    item = job("smartrecruiters")
    item.pop("jobAd")
    result, client = await crawl(
        "smartrecruiters", payload("smartrecruiters", [item]), job("smartrecruiters")
    )
    assert len(client.calls) == 2 and client.calls[1][1].endswith("/postings/1")
    assert result.jobs[0].url.startswith("https://jobs.smartrecruiters.com/")
    assert "SQL required" in result.jobs[0].metadata["description"]


@pytest.mark.parametrize("tld", ["com", "de"])
async def test_a3_personio_domain_binding_and_xxe(tld):
    src = replace(source("personio"), url=f"https://acme.jobs.personio.{tld}")
    result, client = await crawl(
        "personio", payload("personio", [job("personio")]), src=src
    )
    assert (
        len(client.calls) == 1
        and client.calls[0][1] == f"https://acme.jobs.personio.{tld}/xml"
    )
    assert result.jobs[0].url == f"https://acme.jobs.personio.{tld}/job/1"
    with pytest.raises(MalformedAdapterResultError):
        await crawl(
            "personio",
            '<!DOCTYPE root [<!ENTITY evil SYSTEM "file:///secret">]><workzag-jobs>&evil;</workzag-jobs>',
            src=src,
        )


async def test_a3_teamtailor_follows_safe_next_and_rejects_spoof():
    result, client = await crawl(
        "teamtailor",
        payload("teamtailor", [job("teamtailor")], next_url="/jobs.json?page=2"),
        payload("teamtailor", [job("teamtailor", "2")]),
    )
    assert (
        len(result.jobs) == 2
        and client.calls[1][1] == "https://acme.teamtailor.com/jobs.json?page=2"
    )
    result, client = await crawl(
        "teamtailor",
        payload(
            "teamtailor", [job("teamtailor")], next_url="https://evil.example/jobs.json"
        ),
    )
    assert len(client.calls) == 1 and not result.is_complete


async def test_a3_hirex_multiple_blocks_nested_graph_and_malformed_block():
    body = (
        '<script TYPE="application/ld+json" data-id="x">'
        + json.dumps(job("hirex"))
        + '</script><script type = "application/ld+json">'
        + json.dumps({"@graph": [job("hirex", "2")]})
        + '</script><script type="application/ld+json">broken</script>'
    )
    result, _ = await crawl("hirex", body)
    assert len(result.jobs) == 2 and "malformed_json_ld_block" in result.warnings
    assert json.loads(result.jobs[0].raw_content)["baseSalary"]["currency"] == "TRY"


async def test_a3_bamboohr_conditional_public_detail():
    item = job("bamboohr")
    item.pop("jobDescription")
    item.pop("description")
    detail = {
        "@type": "JobPosting",
        "identifier": {"value": "1"},
        "description": DESCRIPTION,
    }
    body = '<script type="application/ld+json">' + json.dumps(detail) + "</script>"
    result, client = await crawl("bamboohr", payload("bamboohr", [item]), body)
    assert (
        len(client.calls) == 2
        and client.calls[1][1] == "https://acme.bamboohr.com/careers/1"
    )
    assert result.jobs[0].metadata["description"] == DESCRIPTION
    assert json.loads(result.jobs[0].raw_content)["detail_json_ld"] == detail


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_exact_first_request_contract(provider):
    _, client = await crawl(provider, payload(provider, [job(provider)]))
    expected = {
        "ashby": (
            "GET",
            "https://api.ashbyhq.com/posting-api/job-board/acme",
            {"params": {"includeCompensation": "true"}},
        ),
        "workday": (
            "POST",
            "https://acme.wd3.myworkdayjobs.com/wday/cxs/acme/Careers/jobs",
            {"json": {"limit": 20, "offset": 0, "searchText": "", "appliedFacets": {}}},
        ),
        "smartrecruiters": (
            "GET",
            "https://api.smartrecruiters.com/v1/companies/acme/postings",
            {"params": {"limit": 100, "offset": 0}},
        ),
        "recruitee": (
            "GET",
            "https://acme.recruitee.com/api/offers/",
            {"params": None},
        ),
        "personio": ("GET", "https://acme.jobs.personio.de/xml", {"params": None}),
        "teamtailor": (
            "GET",
            "https://acme.teamtailor.com/jobs.json",
            {"params": None},
        ),
        "workable": (
            "GET",
            "https://apply.workable.com/api/v1/widget/accounts/acme",
            {"params": {"details": "true"}},
        ),
        "hirex": ("GET", "https://app.gethirex.com/o/acme/", {"params": None}),
        "bamboohr": ("GET", "https://acme.bamboohr.com/careers/list", {"params": None}),
        "oracle": (
            "GET",
            "https://acme.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
            {
                "params": {
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": (
                        "findReqs;siteNumber=CX_1,limit=100,offset=0,"
                        "sortBy=POSTING_DATES_DESC"
                    ),
                }
            },
        ),
    }
    assert client.calls == [expected[provider]]


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("bad", [True, 0, -1, 1001, "10"])
async def test_a3_invalid_page_ceiling_before_io(provider, bad):
    client = FakeClient()
    src = replace(source(provider), pagination_config={"max_pages": bad})
    with pytest.raises(InvalidSourceConfigurationError):
        await create_adapter_registry(client).get_adapter(provider).crawl(src)
    assert not client.calls


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters", "oracle"])
@pytest.mark.parametrize("total", [None, True, -1, "1", 1.5])
async def test_a3_missing_invalid_total_prevents_completeness(provider, total):
    root = payload(provider, [job(provider)])
    if provider == "oracle":
        root["items"][0]["TotalJobsCount"] = total
    else:
        root["total" if provider == "workday" else "totalFound"] = total
    result, _ = await crawl(provider, root)
    assert not result.is_complete and "missing_or_invalid_total" in result.warnings


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters", "oracle"])
async def test_a3_exact_multiple_with_total_does_not_invent_extra_request(provider):
    src = replace(source(provider), pagination_config={"page_size": 1})
    result, client = await crawl(
        provider,
        payload(provider, [job(provider)], total=2),
        payload(provider, [job(provider, "2")], total=2),
        src=src,
    )
    assert len(client.calls) == len(result.jobs) == 2
    assert result.is_complete == (provider == "smartrecruiters")


@pytest.mark.parametrize("provider", sorted(PROVEN))
async def test_a3_proven_nonempty_board_retains_normal_closure(provider):
    src = source(provider)
    jobs, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    service = JobIngestionService(jobs, raw, runs)
    result, _ = await crawl(provider, payload(provider, [job(provider, "old")]))
    await service.ingest_crawl_result(src, result)
    result, _ = await crawl(provider, payload(provider, [job(provider)]))
    run = await service.ingest_crawl_result(src, result)
    assert run.status == CrawlStatus.COMPLETED and run.jobs_closed == 1


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_fatal_acquisition_audits_failed_without_ingestion(provider):
    src = source(provider)
    provider_port, persistence = AsyncMock(), AsyncMock()
    provider_port.get_crawlable_source.return_value = src
    persistence.create_initial_run.return_value = uuid.uuid4()
    orchestrator = CrawlerOrchestrator(
        provider_port,
        create_adapter_registry(FakeClient(AdapterExecutionError("safe failure"))),
        persistence,
    )
    result = await orchestrator.crawl_source(src.id)
    assert result.status == CrawlStatus.FAILED and result.jobs_closed == 0
    persistence.execute_ingestion.assert_not_awaited()
    persistence.mark_run_failed.assert_awaited_once()


async def test_a3_teamtailor_url_feed_identity_and_repeated_next():
    item = job("teamtailor")
    item["id"] = item["url"]
    result, client = await crawl(
        "teamtailor", payload("teamtailor", [item], next_url="/jobs.json")
    )
    assert len(result.jobs) == 1 and len(client.calls) == 1
    assert "repeated_continuation_url" in result.warnings


async def test_a3_smartrecruiters_documented_apply_url_not_api_reference():
    item = job("smartrecruiters")
    item.pop("jobAdUrl")
    item["applyUrl"] = "https://www.smartrecruiters.com/acme/1-engineer?oga=true"
    result, _ = await crawl("smartrecruiters", payload("smartrecruiters", [item]))
    assert result.jobs[0].url == item["applyUrl"]


@pytest.mark.parametrize("provider", ["recruitee", "workable", "bamboohr"])
async def test_a3_unverified_continuation_never_silently_complete(provider):
    result, client = await crawl(
        provider,
        payload(provider, [job(provider)], next_url="https://evil.example/private"),
    )
    assert len(result.jobs) == 1 and not result.is_complete and result.warnings
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "value", ["Temporary", "Seasonal", "Other", "Volunteer", None, True, {}]
)
def test_a3_unknown_structured_values_never_invent_canonical(value):
    from backend.infrastructure.ats.acquisition import employment, work_mode

    assert employment(value) is None
    assert work_mode(value) is None
    assert work_mode(None, False) is None


async def test_a3_required_detail_and_page_pacing(monkeypatch):
    import backend.infrastructure.ats.acquisition as shared

    sleep = AsyncMock()
    monkeypatch.setattr(shared.asyncio, "sleep", sleep)
    item = job("workday")
    item.pop("jobDescription")
    src = replace(
        source("workday"),
        pagination_config={"page_size": 1},
        rate_limit_config={"delay_seconds": 0.1},
    )
    detail = {"jobPostingInfo": {"title": item["title"], "jobDescription": DESCRIPTION}}
    result, client = await crawl(
        "workday",
        payload("workday", [item], total=2),
        detail,
        payload("workday", [job("workday", "2")], total=2),
        src=src,
    )
    assert len(client.calls) == 3 and len(result.jobs) == 2
    assert sleep.await_count == 2


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_request_budget_prevents_first_io(provider, monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with (
            acquisition_scope(AcquisitionBudget(max_requests=0)),
            pytest.raises(AdapterExecutionError) as error,
        ):
            await (
                create_adapter_registry(HttpSafeClient(client=client))
                .get_adapter(provider)
                .crawl(source(provider))
            )
    assert error.value.code == "ACQUISITION_BUDGET_EXHAUSTED" and not requests


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
@pytest.mark.parametrize("mode", [[], {}, True, "cursor"])
async def test_a3_invalid_mode_is_safe_config_error(provider, mode):
    client = FakeClient()
    src = replace(source(provider), pagination_config={"pagination_mode": mode})
    with pytest.raises(InvalidSourceConfigurationError):
        await create_adapter_registry(client).get_adapter(provider).crawl(src)
    assert not client.calls


async def test_a3_malformed_required_workday_detail_is_fatal():
    item = job("workday")
    item.pop("jobDescription")
    with pytest.raises(MalformedAdapterResultError):
        await crawl("workday", payload("workday", [item]), {"jobPostingInfo": []})


async def test_a3_html_script_without_type_cannot_raise_attribute_error():
    result, _ = await crawl("hirex", "<script type>not json</script>")
    assert not result.jobs and not result.is_complete and result.warnings


@pytest.mark.parametrize("provider", NEW_PROVIDERS)
async def test_a3_response_redirect_cannot_change_provider_board(provider):
    class Redirected(FakeClient):
        def _response(self, method, url, kwargs):
            response = super()._response(method, url, kwargs)
            response.url = "https://evil.example/another-board"
            return response

    with pytest.raises(AdapterExecutionError, match="binding"):
        await (
            create_adapter_registry(Redirected(payload(provider, [job(provider)])))
            .get_adapter(provider)
            .crawl(source(provider))
        )


@pytest.mark.parametrize(
    "url",
    ["https://acme.wd3.myworkdayjobs.com/", "https://acme.wd3.myworkdayjobs.com/en-US"],
)
async def test_a3_ambiguous_workday_can_be_resolved_explicitly(url):
    src = replace(
        source("workday"),
        url=url,
        adapter_config={"site": "Careers", "locale": "en-US"},
    )
    result, client = await crawl(
        "workday", payload("workday", [job("workday")]), src=src
    )
    assert len(result.jobs) == 1 and "/acme/Careers/jobs" in client.calls[0][1]


async def test_a3_detail_does_not_lose_structured_list_fields():
    item = job("smartrecruiters")
    item.pop("jobAd")
    detail = job("smartrecruiters")
    for key in ("location", "typeOfEmployment", "releasedDate", "jobAdUrl"):
        detail.pop(key)
    result, _ = await crawl(
        "smartrecruiters", payload("smartrecruiters", [item]), detail
    )
    assert result.jobs[0].metadata["employment_type"] == "Full-time"
    assert result.jobs[0].metadata["work_mode"] == "Remote"
    assert "Istanbul" in result.jobs[0].metadata["location"]
    assert result.jobs[0].metadata["published_at"] == item["releasedDate"]


async def test_a3_bamboohr_detail_structured_fields_are_projected():
    item = job("bamboohr")
    for key in ("jobDescription", "description", "employmentStatus", "isRemote"):
        item.pop(key)
    detail = {
        "@type": "JobPosting",
        "identifier": {"value": "1"},
        "description": DESCRIPTION,
        "employmentType": "CONTRACT",
        "jobLocationType": "TELECOMMUTE",
        "datePosted": "2026-10-01",
    }
    html = '<script type="application/ld+json">' + json.dumps(detail) + "</script>"
    result, _ = await crawl("bamboohr", payload("bamboohr", [item]), html)
    assert result.jobs[0].metadata["employment_type"] == "Contract"
    assert result.jobs[0].metadata["work_mode"] == "Remote"
    assert result.jobs[0].metadata["published_at"] == "2026-10-01"


@pytest.mark.parametrize(
    "host",
    ["fa-evlj-saasfaprod1.fa.ocs.oraclecloud.com", "iaahwm.fa.ocs.oraclecloud.eu"],
)
def test_a3_oracle_regional_catalog_hosts_bound(host):
    url = f"https://{host}/hcmUI/CandidateExperience/en/sites/CX_1/jobs"
    assert source_binding(url, "oracle")["host"] == host
    assert classify_ats_type(url) == "oracle"
    assert classify_ats_type(url.replace(host, host + ".evil.example")) == "custom"


async def test_a3_oracle_short_only_observation_cannot_erase_rich_description():
    src = source("oracle")
    jobs, raw, runs = (
        InMemoryJobRepository(),
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
    )
    service = JobIngestionService(jobs, raw, runs)
    rich, _ = await crawl("oracle", payload("oracle", [job("oracle")]))
    await service.ingest_crawl_result(src, rich)
    item = job("oracle")
    item.pop("ExternalDescriptionStr")
    item["ShortDescriptionStr"] = "Short summary only"
    partial, _ = await crawl("oracle", payload("oracle", [item]))
    run = await service.ingest_crawl_result(src, partial)
    assert (
        run.jobs_unchanged == 1
        and next(iter(jobs.jobs.values())).description == DESCRIPTION
    )
    assert len(raw.raw_jobs) == 1 and not partial.is_complete


async def test_a3_personio_empty_value_is_unknown_description():
    item = job("personio").replace(DESCRIPTION, "").replace("SQL required", "")
    result, _ = await crawl("personio", payload("personio", [item]))
    assert result.jobs[0].metadata["description_available"] is False
