"""Provider-side narrowing never turns a filtered list into a full snapshot."""

import uuid
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from backend.application.ingestion.policy import PolicySnapshot
from backend.application.ingestion.runner import IngestionRunner
from backend.application.job_discovery.budget import AcquisitionBudget
from backend.application.job_discovery.detail_plan import (
    DetailPlan,
    acquisition_countries,
    detail_scope,
)
from backend.application.job_discovery.dtos import CrawlResultDTO
from backend.infrastructure.ats.workday.country_facets import country_facets
from tests.test_acquisition_a3 import crawl, job, payload, source


def envelope(rows, total=2, nested=False):
    facet = {
        "facetParameter": "Location_Country",
        "values": [
            {"descriptor": "Türkiye", "id": "board-tr", "count": 1},
            {"descriptor": "Spain", "id": "board-es", "count": 1},
        ],
    }
    return {
        "total": total,
        "jobPostings": rows,
        "facets": [{"facetParameter": "locationMainGroup", "values": [facet]}]
        if nested
        else [facet],
    }


@pytest.mark.parametrize("provider", ["smartrecruiters"])
async def test_country_requests_paginate_and_never_authorize_closure(provider):
    src = replace(source(provider), pagination_config={"page_size": 1})
    with detail_scope(DetailPlan(country_codes=("TR",))):
        result, client = await crawl(
            provider,
            payload(provider, [job(provider, "1")], total=2),
            payload(provider, [job(provider, "2")], total=2),
            src=src,
        )
    assert len(result.jobs) == 2 and not result.is_complete
    assert "provider_country_scoped_acquisition" in result.warnings
    for index, call in enumerate(client.calls):
        params = call[2]["params"]
        assert params == {"limit": 1, "offset": index, "country": "tr"}


@pytest.mark.parametrize("provider", ["smartrecruiters"])
async def test_multiple_countries_use_separate_queries_and_union_identity(provider):
    with detail_scope(DetailPlan(country_codes=("TR", "ES"))):
        result, client = await crawl(
            provider,
            payload(provider, [job(provider, "1")]),
            payload(provider, [job(provider, "1"), job(provider, "2")]),
        )
    assert len(result.jobs) == 2 and len(client.calls) == 2
    assert "duplicate_or_overlapping_page_detected" not in result.warnings
    assert result.metadata["country_scope"] == ["TR", "ES"]
    for call, code in zip(client.calls, ("TR", "ES"), strict=True):
        params = call[2]["params"]
        assert params["country"] == code.lower()


@pytest.mark.parametrize("nested", [False, True])
async def test_workday_discovers_board_ids_then_only_pages_filtered_population(nested):
    src = replace(source("workday"), pagination_config={"page_size": 1})
    with detail_scope(DetailPlan(country_codes=("TR", "ES"))):
        result, client = await crawl(
            "workday",
            envelope([job("workday", "global")], nested=nested),
            payload("workday", [job("workday", "1")], total=2),
            payload("workday", [job("workday", "2")], total=0),
            src=src,
        )
    assert [j.external_job_id for j in result.jobs] == ["Engineer_R-1", "Engineer_R-2"]
    assert [c[2]["json"]["offset"] for c in client.calls] == [0, 0, 1]
    assert client.calls[0][2]["json"]["appliedFacets"] == {}
    assert all(
        c[2]["json"]["appliedFacets"] == {"Location_Country": ["board-tr", "board-es"]}
        for c in client.calls[1:]
    )
    assert not result.is_complete


async def test_workday_missing_facet_reuses_first_page_and_falls_back():
    src = replace(source("workday"), pagination_config={"page_size": 1})
    with detail_scope(DetailPlan(country_codes=("TR",))):
        result, client = await crawl(
            "workday",
            payload("workday", [job("workday", "1")], total=2),
            payload("workday", [job("workday", "2")], total=0),
            src=src,
        )
    assert len(result.jobs) == 2 and len(client.calls) == 2
    assert all(c[2]["json"]["appliedFacets"] == {} for c in client.calls)
    assert "provider_country_filter_unavailable_unfiltered_fallback" in result.warnings


async def test_workday_reconciled_country_facet_can_prove_no_selected_jobs():
    root = envelope([job("workday")])
    root["facets"][0]["values"] = [
        {"descriptor": "Spain", "id": "board-es", "count": 2}
    ]
    with detail_scope(DetailPlan(country_codes=("TR",))):
        result, client = await crawl("workday", root)
    assert not result.jobs and len(client.calls) == 1
    assert not result.is_complete


@pytest.mark.parametrize(
    "defect",
    [
        "boolean_count",
        "bad_id",
        "duplicate_id",
        "missing_values",
        "localized",
        "unknown_code",
        "truncated",
    ],
)
def test_unproven_country_facets_never_guess_or_empty_the_board(defect):
    root = envelope([])
    values = root["facets"][0]["values"]
    countries = ("TR",)
    if defect == "boolean_count":
        values[0]["count"] = True
    elif defect == "bad_id":
        values[0]["id"] = "../other"
    elif defect == "duplicate_id":
        values[1]["id"] = values[0]["id"]
    elif defect == "missing_values":
        root["facets"][0]["values"] = None
    elif defect == "localized":
        values[0]["descriptor"] = "Unrecognized translation"
        root["total"] = 10
    elif defect == "unknown_code":
        countries = ("ZZ",)
    else:
        countries = ("US",)
        root["total"] = 10
    assert country_facets(root, countries) is None


@pytest.mark.parametrize("provider", ["smartrecruiters", "oracle", "workday"])
async def test_unscoped_crawls_still_request_entire_board(provider):
    result, client = await crawl(provider, payload(provider, [job(provider)]))
    assert len(result.jobs) == 1 and len(client.calls) == 1
    options = client.calls[0][2]
    assert options.get("json", {}).get("appliedFacets", {}) == {}
    assert "country" not in options.get("params", {})
    assert "workLocationCountryCode" not in options.get("params", {}).get("finder", "")


@pytest.mark.parametrize("mode", ["PREVIEW", "PERSIST"])
@pytest.mark.parametrize(
    "policy, expected",
    [
        (PolicySnapshot("TEST", ("TR",)), ("TR",)),
        (PolicySnapshot("TEST", ("TR", "ES")), ("TR", "ES")),
        (PolicySnapshot("TEST", ("TR",), include_unknown_country=True), ()),
        (PolicySnapshot("TEST", ("TR",), enabled=False), ()),
        (PolicySnapshot("TEST"), ()),
    ],
)
async def test_runner_uses_frozen_policy_and_preserves_unknown_and_disabled_modes(
    mode, policy, expected
):
    observed = []

    class Store:
        async def mark_running(self, *args):
            pass

        async def detail(self, *args):
            return {"cancel_requested_at": None}

        async def complete_source(self, *args):
            assert acquisition_countries() == ()

        async def finish(self, *args):
            pass

        async def fail_source(self, *args):
            pytest.fail("Source should complete")

    class Guard:
        @asynccontextmanager
        async def hold(self, *args):
            yield

    class Adapter:
        async def crawl(self, src):
            observed.append(acquisition_countries())
            return CrawlResultDTO(src.id, src.ats_type)

    guard = Guard()
    lease = guard.hold()
    await lease.__aenter__()
    runner = IngestionRunner(
        Store(),
        SimpleNamespace(get_adapter=lambda _: Adapter()),
        guard,
        AcquisitionBudget,
    )
    await runner._execute(
        {"id": uuid.uuid4(), "mode": mode},
        [(uuid.uuid4(), source("workday"), policy)],
        lease,
    )
    assert observed == [expected] and acquisition_countries() == ()


@pytest.mark.parametrize(
    "provider",
    [
        "ashby",
        "recruitee",
        "personio",
        "teamtailor",
        "workable",
        "hirex",
        "bamboohr",
        "oracle",
    ],
)
async def test_unverified_endpoints_ignore_pushdown_but_still_return_local_policy_input(
    provider,
):
    with detail_scope(DetailPlan(country_codes=("TR",))):
        result, client = await crawl(provider, payload(provider, [job(provider)]))
    assert len(result.jobs) == 1
    assert "provider_country_scoped_acquisition" not in result.warnings
    assert all("country" not in (c[2].get("params") or {}) for c in client.calls)
