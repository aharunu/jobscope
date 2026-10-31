"""Offline contracts based on HRPeak's public list and detail HTML."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from backend.application.job_discovery.detail_plan import DetailPlan, detail_scope
from backend.application.job_discovery.dtos import RuntimeSourceDTO, SafeHttpResponseDTO
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
)
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.ats.hrpeak.adapter import HRPeakAdapter
from backend.infrastructure.parsers.markdown_source_parser import (
    MarkdownSourceParser,
    classify_ats_type,
)
from tests.test_acquisition_a3 import FakeClient
from tests.test_greenhouse_crawler_integration import (
    InMemoryCrawlRunRepository,
    InMemoryJobRepository,
    InMemoryRawJobRepository,
)

LIST = """<table id="C_G"><tr><th>Yayın Tarihi</th></tr><tr class="GR"><td>
<a href="/abc123.job" class="PL">Veri Mühendisi &amp; Analist</a>
<span class=location>İstanbul</span><a href="/abc123.job">Open</a></td>
<td>22.04.2026</td></tr></table>"""
DETAIL = """<div class="ilan"><h3>Veri Mühendisi</h3>
<div class="ilanMetni"><p>Python &amp; SQL</p><ul><li>İleri analiz</li></ul></div>
<a href="/application/easy">Apply</a></div>"""


def source(url="https://tei.hrpeak.com/jobs", **kwargs):
    return RuntimeSourceDTO.from_domain(
        Source(name="TEI", company="TEI", url=url, ats_type="hrpeak", **kwargs)
    )


async def test_list_detail_mapping_and_conservative_coverage():
    client = FakeClient(LIST, DETAIL)
    result = await create_adapter_registry(client).get_adapter("hrpeak").crawl(source())
    assert [c[1] for c in client.calls] == [
        "https://tei.hrpeak.com/jobs",
        "https://tei.hrpeak.com/abc123.job",
    ]
    assert len(result.jobs) == 1 and not result.is_complete
    job = result.jobs[0]
    assert job.external_job_id == "abc123"
    assert job.title == "Veri Mühendisi & Analist"
    assert job.metadata["location"] == "İstanbul"
    assert job.metadata["published_at"] == "2026-04-22"
    assert "Python &amp; SQL" in job.metadata["description"]
    assert "Apply" not in job.metadata["description"]
    assert json.loads(job.raw_content)["list"]["id"] == "abc123"


async def test_preview_defers_detail_and_has_no_persistence():
    client = FakeClient(LIST)
    with detail_scope(DetailPlan(preview=True)):
        result = await HRPeakAdapter(client).crawl(source())
    assert len(client.calls) == 1 and len(result.jobs) == 1
    assert result.jobs[0].metadata["acquisition_detail_deferred"] == "PREVIEW"
    assert not result.is_complete


async def test_empty_observed_table_is_partial():
    client = FakeClient('<table id="C_G"><tr><td>No positions</td></tr></table>')
    result = await HRPeakAdapter(client).crawl(source())
    assert result.jobs == [] and not result.is_complete


async def test_partial_empty_run_preserves_existing_jobs():
    src = source()
    jobs = InMemoryJobRepository()
    service = JobIngestionService(
        jobs,
        InMemoryRawJobRepository(),
        InMemoryCrawlRunRepository(),
        requirement_service=AsyncMock(),
    )
    first = await HRPeakAdapter(FakeClient(LIST, DETAIL)).crawl(src)
    await service.ingest_crawl_result(src, first)
    empty = await HRPeakAdapter(FakeClient('<table id="C_G"></table>')).crawl(src)
    run = await service.ingest_crawl_result(src, empty)
    assert run.status == CrawlStatus.PARTIAL and run.jobs_closed == 0
    assert len(jobs.jobs) == 1
    assert all(job.status == JobStatus.ACTIVE for job in jobs.jobs.values())


@pytest.mark.parametrize("body", ["<html>Login</html>", "bad root"])
async def test_missing_table_fails(body):
    with pytest.raises(MalformedAdapterResultError):
        await HRPeakAdapter(FakeClient(body)).crawl(source())


async def test_missing_description_fails():
    with pytest.raises(MalformedAdapterResultError):
        await HRPeakAdapter(FakeClient(LIST, "<html>Login</html>")).crawl(source())


@pytest.mark.parametrize("status", [403, 404, 429, 503])
async def test_http_failure_is_not_empty_success(status):
    with pytest.raises(AdapterExecutionError):
        await HRPeakAdapter(FakeClient(LIST, status=status)).crawl(source())


@pytest.mark.parametrize(
    "href",
    [
        "https://evil.example/abc123.job",
        "//other.hrpeak.com/abc123.job",
        "/application/easy",
        "/abc123.job?board=other",
    ],
)
async def test_unsafe_links_are_never_fetched(href):
    client = FakeClient(LIST.replace("/abc123.job", href))
    result = await HRPeakAdapter(client).crawl(source())
    assert not result.jobs and len(client.calls) == 1


async def test_duplicate_links_do_not_repeat_detail_request():
    row = '<tr class="GR">' + LIST.split('<tr class="GR">')[1].removesuffix("</table>")
    client = FakeClient(LIST.replace("</table>", row + "</table>"), DETAIL)
    result = await HRPeakAdapter(client).crawl(source())
    assert len(result.jobs) == 1 and len(client.calls) == 2


async def test_redirect_cannot_move_board():
    class RedirectClient:
        async def get(self, url, **kwargs):
            return SafeHttpResponseDTO(200, "https://hrpeak.com/jobs", text=LIST)

    with pytest.raises(AdapterExecutionError, match="binding"):
        await HRPeakAdapter(RedirectClient()).crawl(source())


@pytest.mark.parametrize(
    "url",
    [
        "https://tei.hrpeak.com/jobs",
        "https://milsoft.hrpeak.com",
        "https://kariyer.roketsan.com.tr/jobs",
    ],
)
def test_catalog_classifies_and_prioritizes_hrpeak(url):
    rows, warnings = MarkdownSourceParser().parse_content(
        f"## Sources\n- **Company** — `https://example.com/career` + `{url}` — open"
    )
    assert not warnings and rows[0].ats_type == "hrpeak"
    assert rows[0].adapter_config["host"] == url.split("/")[2]


@pytest.mark.parametrize(
    "url",
    [
        "https://hrpeak.com/jobs",
        "https://www.hrpeak.com/jobs",
        "https://tei.hrpeak.com.evil.example/jobs",
        "https://tei.hrpeak.com/login",
    ],
)
async def test_unbound_source_is_rejected_before_io(url):
    client = FakeClient()
    assert classify_ats_type(url) == "custom"
    with pytest.raises(InvalidSourceConfigurationError):
        await HRPeakAdapter(client).crawl(source(url))
    assert not client.calls


async def test_board_override_is_rejected_before_io():
    client = FakeClient()
    with pytest.raises(InvalidSourceConfigurationError):
        await HRPeakAdapter(client).crawl(
            replace(source(), adapter_config={"board": "other"})
        )
    assert not client.calls


def test_real_catalog_hrpeak_employers_are_supported():
    catalog = Path(__file__).parents[1] / "data" / "turkish-job-sources.md"
    rows, _ = MarkdownSourceParser().parse_file(str(catalog))
    names = {r.company for r in rows if r.ats_type == "hrpeak"}
    assert {"Ziraat Teknoloji", "MilSOFT Yazılım", "Roketsan"} <= names
    assert len(names) == 7
