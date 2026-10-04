"""Minimal public-response regressions observed in A3.1; no live CI traffic."""

from datetime import UTC, datetime

import pytest

from backend.infrastructure.ats.recruitee.adapter import (
    offer_publication,
    offer_work_mode,
)
from tests.test_acquisition_a3 import crawl, job, payload


async def test_workable_public_widget_shortcode_url_is_not_discarded():
    item = job("workable")
    item.pop("id", None)
    item.update(shortcode="CE391E6314", url="https://apply.workable.com/j/CE391E6314")
    result, client = await crawl("workable", payload("workable", [item]))
    assert len(result.jobs) == 1
    assert result.jobs[0].external_job_id == "CE391E6314"
    assert result.jobs[0].url == item["url"]
    assert result.jobs[0].metadata["description"] == (
        item["description"] + "\n" + item["requirements"]
    )
    assert not result.is_complete and result.warnings
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://apply.workable.com/j/OTHER",
        "https://apply.workable.com/j/CE391E6314/apply",
        "https://apply.workable.com.evil.test/j/CE391E6314",
        "https://evil.test/j/CE391E6314",
        "https://user:password@apply.workable.com/j/CE391E6314",
        "https://apply.workable.com/other-company/j/CE391E6314",
        "https://apply.workable.com/j/../CE391E6314",
    ],
)
async def test_workable_shortcode_url_remains_bound_to_returned_record(url):
    item = job("workable")
    item.update(shortcode="CE391E6314", url=url, shortlink=None)
    result, _ = await crawl("workable", payload("workable", [item]))
    assert not result.jobs
    assert "malformed_or_unidentified_posting" in result.warnings
    assert not result.is_complete


async def test_recruitee_real_structured_schedule_mode_and_utc_publication():
    item = job("recruitee")
    item.update(
        employment_type_code="fulltime_permanent",
        workplace_type=None,
        remote=False,
        hybrid=True,
        on_site=False,
        published_at="2026-08-07 22:35:48 UTC",
    )
    result, _ = await crawl("recruitee", payload("recruitee", [item]))
    meta = result.jobs[0].metadata
    assert meta["employment_type"] == "Full-time"
    assert meta["work_mode"] == "Hybrid"
    assert meta["published_at"] == datetime(2026, 8, 7, 22, 35, 48, tzinfo=UTC)
    assert meta["provider"]["employment_type_code"] == "fulltime_permanent"
    assert not result.is_complete and result.warnings


@pytest.mark.parametrize(
    "flags, expected",
    [
        ({"remote": True}, "Remote"),
        ({"hybrid": True}, "Hybrid"),
        ({"on_site": True}, "On-site"),
        ({"remote": False, "hybrid": False, "on_site": False}, None),
        ({"remote": True, "hybrid": True}, None),
        ({"hybrid": "true", "on_site": 1}, None),
    ],
)
def test_recruitee_mode_uses_only_unambiguous_structured_true(flags, expected):
    assert offer_work_mode(flags) == expected


@pytest.mark.parametrize(
    "value", ["yesterday", "2026-08-07 22:35:48", "invalid UTC", None, []]
)
def test_recruitee_unverified_publication_remains_unknown(value):
    assert offer_publication(value) is None


async def test_bamboohr_real_schedule_label_preserved_without_inference():
    item = job("bamboohr")
    item.update(
        employmentStatus=None, employmentType=None, employmentStatusLabel="Full-Time"
    )
    result, _ = await crawl("bamboohr", payload("bamboohr", [item]))
    assert result.jobs[0].metadata["employment_type"] == "Full-time"
    assert not result.is_complete and result.warnings


async def test_oracle_real_structured_workplace_label_when_code_not_canonical():
    item = job("oracle")
    item.update(WorkplaceTypeCode="ORA_ON_SITE", WorkplaceType="On-site")
    result, _ = await crawl("oracle", payload("oracle", [item]))
    assert result.jobs[0].metadata["work_mode"] == "On-site"
    assert not result.is_complete and result.warnings
