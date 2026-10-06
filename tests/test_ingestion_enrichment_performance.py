"""List-only previews and conservative enrichment/partial-result contracts."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest

from backend.application.ingestion.policy import PolicySnapshot
from backend.application.ingestion.runner import IngestionRunner
from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.detail_plan import DetailPlan, detail_scope
from backend.application.job_discovery.dtos import CrawlResultDTO
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.ats.factory import create_adapter_registry
from tests.test_acquisition_a3 import (
    DESCRIPTION,
    FakeClient,
    crawl,
    job,
    payload,
    source,
)


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters"])
async def test_preview_lists_every_posting_without_detail_calls(provider):
    rows = [job(provider, str(i)) for i in range(3)]
    for row in rows:
        row.pop("jobDescription" if provider == "workday" else "jobAd")
    src = replace(source(provider), pagination_config={"page_size": 2})
    with detail_scope(DetailPlan(preview=True)):
        result, client = await crawl(
            provider,
            payload(provider, rows[:2], total=3),
            payload(provider, rows[2:], total=0 if provider == "workday" else 3),
            src=src,
        )
    assert len(client.calls) == 2
    assert len(result.jobs) == 3
    assert all(
        item.metadata["acquisition_detail_deferred"] == "PREVIEW"
        for item in result.jobs
    )
    assert not result.is_complete
    assert "preview_details_deferred_until_persist" in result.warnings


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters"])
async def test_persist_skips_known_rejected_country_but_enriches_accepted(provider):
    excluded, accepted = job(provider, "1"), job(provider, "2")
    for row in (excluded, accepted):
        row.pop("jobDescription" if provider == "workday" else "jobAd")
    if provider == "smartrecruiters":
        excluded["location"] = {"city": "Paris", "country": "FR"}
        detail = job(provider, "2")
    else:
        excluded["locationsText"] = "France, Paris"
        detail = {
            "jobPostingInfo": {
                "title": accepted["title"],
                "jobDescription": DESCRIPTION,
            }
        }
    policy = PolicySnapshot("TEST", ("TR",))
    with detail_scope(DetailPlan(reject_without_detail=policy.rejects_known_country)):
        result, client = await crawl(
            provider, payload(provider, [excluded, accepted]), detail
        )
    assert len(client.calls) == 2  # list + accepted posting detail
    assert len(result.jobs) == 2
    assert policy.decide(result.jobs[0])[:2] == ("REJECTED", "COUNTRY_NOT_ALLOWED")
    assert result.jobs[0].metadata["acquisition_detail_deferred"] == "COUNTRY_POLICY"
    assert "acquisition_detail_deferred" not in result.jobs[1].metadata
    assert result.jobs[1].metadata["description"]


async def test_unknown_country_still_gets_details_during_persist():
    item = job("workday")
    item.pop("jobDescription")
    item["locationsText"] = "Multiple locations"
    policy = PolicySnapshot("TEST", ("TR",))
    with detail_scope(DetailPlan(reject_without_detail=policy.rejects_known_country)):
        result, client = await crawl(
            "workday",
            payload("workday", [item]),
            {
                "jobPostingInfo": {
                    "title": item["title"],
                    "jobDescription": DESCRIPTION,
                    "location": "Istanbul",
                }
            },
        )
    assert len(client.calls) == 2
    assert policy.decide(result.jobs[0])[0] == "ACCEPTED"


async def test_unscoped_direct_crawl_keeps_required_detail_and_no_plan_leak():
    with detail_scope(DetailPlan(preview=True)):
        pass
    item = job("smartrecruiters")
    item.pop("jobAd")
    result, client = await crawl(
        "smartrecruiters", payload("smartrecruiters", [item]), job("smartrecruiters")
    )
    assert len(client.calls) == 2 and result.is_complete
    assert "acquisition_detail_deferred" not in result.jobs[0].metadata


async def test_workday_later_zero_total_is_not_changed_total_or_exhaustion():
    src = replace(source("workday"), pagination_config={"page_size": 1})
    result, client = await crawl(
        "workday",
        payload("workday", [job("workday", "1")], total=3),
        payload("workday", [job("workday", "2")], total=0),
        payload("workday", [job("workday", "3")], total=0),
        src=src,
    )
    assert len(client.calls) == 3 and len(result.jobs) == 3
    assert [call[2]["json"]["offset"] for call in client.calls] == [0, 1, 2]
    assert "total_changed_between_pages" not in result.warnings
    assert not result.is_complete  # Hosted CXS coverage safeguard remains.


@pytest.mark.parametrize("preview", [False, True])
async def test_workday_unmappable_identity_skips_detail_without_weakening_validation(
    preview,
):
    invalid, valid = job("workday", "1"), job("workday", "2")
    invalid.pop("jobDescription")
    invalid["externalPath"] = "/job/Istanbul/Engineer%20Role_R-1"
    with detail_scope(DetailPlan(preview=preview)):
        result, client = await crawl("workday", payload("workday", [invalid, valid]))
    assert len(client.calls) == 1
    assert len(result.jobs) == 1 and result.jobs[0].external_job_id.endswith("R-2")
    assert "malformed_or_unidentified_posting" in result.warnings
    assert not result.is_complete


@pytest.mark.parametrize("provider", ["workday", "smartrecruiters"])
async def test_budget_recovery_keeps_only_validated_jobs_and_suppresses_closure(
    provider,
):
    budget = AcquisitionBudget()
    item = job(provider)
    with acquisition_scope(budget):
        with pytest.raises(AdapterExecutionError) as caught:
            await crawl(
                provider,
                payload(provider, [item], total=2),
                AdapterExecutionError("budget", code="ACQUISITION_BUDGET_EXHAUSTED"),
                src=replace(source(provider), pagination_config={"page_size": 1}),
            )
        result = budget.recover_partial(caught.value)
    assert result is not None and len(result.jobs) == 1
    assert not result.is_complete
    assert "acquisition_budget_exhausted_partial_results" in result.warnings
    assert budget.recover_partial(AdapterExecutionError("network")) is None
    assert budget.recover_partial(TimeoutError("ordinary network timeout")) is None


async def test_crawler_timeout_retains_partial_results():
    class Client(FakeClient):
        async def get(self, url, **kwargs):
            if self.calls:
                await asyncio.sleep(10)
            return await super().get(url, **kwargs)

    client = Client(payload("smartrecruiters", [job("smartrecruiters")], total=2))
    registry = create_adapter_registry(client)
    orchestrator = CrawlerOrchestrator(
        None,
        registry,
        # The owned timeout remains authoritative even with a frozen accounting
        # clock, avoiding platform-dependent rounding at the timer boundary.
        budget_factory=lambda: AcquisitionBudget(max_seconds=0.2, clock=lambda: 0),
    )
    result = await orchestrator._acquire(
        registry.get_adapter("smartrecruiters"),
        replace(source("smartrecruiters"), pagination_config={"page_size": 1}),
    )
    assert len(result.jobs) == 1 and not result.is_complete
    assert result.warnings


async def test_external_task_cancellation_is_not_converted_to_partial_success():
    waiting = asyncio.Event()

    class Client(FakeClient):
        async def get(self, url, **kwargs):
            if self.calls:
                waiting.set()
                await asyncio.sleep(10)
            return await super().get(url, **kwargs)

    client = Client(payload("smartrecruiters", [job("smartrecruiters")], total=2))
    registry = create_adapter_registry(client)
    orchestrator = CrawlerOrchestrator(None, registry)
    task = asyncio.create_task(
        orchestrator._acquire(
            registry.get_adapter("smartrecruiters"),
            replace(source("smartrecruiters"), pagination_config={"page_size": 1}),
        )
    )
    await asyncio.wait_for(waiting.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("cancel", [False, True])
async def test_bounded_acquisition_serial_completion_and_queued_cancellation(cancel):
    first_pair_ready, release = asyncio.Event(), asyncio.Event()
    started, completed, held = [], [], set()
    writes = 0
    cancelled = False

    class Store:
        async def mark_running(self, run_id, unit_id=None):
            pass

        async def detail(self, run_id):
            return {"cancel_requested_at": cancelled}

        async def complete_source(self, run_id, unit_id, src, *args):
            nonlocal writes
            assert src.id in held
            writes += 1
            assert writes == 1
            await asyncio.sleep(0.01)
            completed.append(src.id)
            writes -= 1

        async def finish(self, *args):
            assert not held

    class Guard:
        @asynccontextmanager
        async def hold(self, source_id):
            assert source_id not in held
            held.add(source_id)
            try:
                yield
            finally:
                held.remove(source_id)

    class Adapter:
        async def crawl(self, src):
            started.append(src.id)
            assert len(held) <= 2
            if len(started) == 2:
                first_pair_ready.set()
            await release.wait()
            return CrawlResultDTO(src.id, src.ats_type, is_complete=True)

    adapter = Adapter()
    registry = SimpleNamespace(get_adapter=lambda _type: adapter)
    runner = IngestionRunner(
        Store(), registry, Guard(), AcquisitionBudget, max_concurrent_sources=2
    )
    sources = [replace(source("workday"), id=uuid.uuid4()) for _ in range(3)]
    units = [(uuid.uuid4(), src, PolicySnapshot("TEST")) for src in sources]

    @asynccontextmanager
    async def run_lease():
        yield

    lease = run_lease()
    await lease.__aenter__()
    task = asyncio.create_task(
        runner._execute({"id": uuid.uuid4(), "mode": "PREVIEW"}, units, lease)
    )
    try:
        await asyncio.wait_for(first_pair_ready.wait(), 1)
        assert len(started) == 2  # overlap, not sequential acquisition
        cancelled = cancel
        release.set()
        await asyncio.wait_for(task, 2)
    finally:
        release.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert len(started) == len(completed) == (2 if cancel else 3)
