"""Invent's renamed board is fixed in Source data, not by relaxing redirects."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from backend.application.ingestion.policy import PolicySnapshot
from backend.application.job_discovery.dtos import SafeHttpResponseDTO
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.ats.hirex.adapter import HirexAdapter
from backend.infrastructure.parsers.markdown_source_parser import MarkdownSourceParser
from tests.test_acquisition_a3 import FakeClient, source

CANONICAL = "https://app.gethirex.com/o/invent-ai/"


def test_invent_catalog_points_to_current_hirex_board():
    catalog = Path(__file__).parents[1] / "data" / "turkish-job-sources.md"
    rows, _ = MarkdownSourceParser().parse_content(catalog.read_text(encoding="utf-8"))
    invent = [r for r in rows if r.name == "Invent Analytics" and r.ats_type == "hirex"]
    assert invent
    assert all(r.url.rstrip("/") == CANONICAL.rstrip("/") for r in invent)


async def test_canonical_invent_board_acquires_lowercase_country_without_redirect():
    body = (
        '<script type="application/ld+json">'
        + json.dumps(
            {
                "@type": "JobPosting",
                "title": "Engineer",
                "description": "Python",
                "url": CANONICAL + "stable-id/",
                "jobLocation": {"address": {"addressCountry": "tr"}},
            }
        )
        + "</script>"
    )
    client = FakeClient(body)
    result = await HirexAdapter(client).crawl(replace(source("hirex"), url=CANONICAL))
    assert client.calls[0][1] == CANONICAL
    assert len(result.jobs) == 1
    assert result.jobs[0].external_job_id == "stable-id"
    assert PolicySnapshot("RUN_OVERRIDE", ("TR",)).decide(result.jobs[0]) == (
        "ACCEPTED",
        "COUNTRY_ALLOWED",
        "TR",
    )
    assert not result.is_complete


async def test_old_invent_redirect_is_still_rejected():
    class RedirectClient:
        async def get(self, url, **kwargs):
            return SafeHttpResponseDTO(200, CANONICAL, text="<html></html>")

    old = "https://app.gethirex.com/o/invent-analytics/"
    with pytest.raises(AdapterExecutionError, match="redirect changed the board"):
        await HirexAdapter(RedirectClient()).crawl(replace(source("hirex"), url=old))
