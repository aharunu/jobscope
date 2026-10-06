"""Operational crawler pacing without live requests or real sleeps."""

import asyncio
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import ValidationError

from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.http import safe_client as module
from backend.interfaces.api.dependencies.crawler import get_safe_http_client
from backend.interfaces.api.main import create_app, lifespan


@pytest.fixture
def clock(monkeypatch):
    state = SimpleNamespace(now=100.0, sleeps=[], calls=[])

    async def sleep(seconds):
        state.sleeps.append(seconds)
        state.now += seconds

    monkeypatch.setattr(module.asyncio, "sleep", sleep)
    monkeypatch.setattr(
        module, "validate_target_url_safety", lambda _: (True, None, None)
    )
    return state


def client(clock, handler=None):
    def respond(request):
        clock.calls.append((request.method, str(request.url), clock.now))
        return handler(request) if handler else httpx.Response(200, text="ok")

    transport = httpx.AsyncClient(transport=httpx.MockTransport(respond))
    safe = module.HttpSafeClient(
        client=transport, min_request_interval_seconds=1, retry_delay=0
    )
    safe._clock = lambda: clock.now
    return safe, transport


async def test_same_host_page_detail_post_and_other_source_share_interval(clock):
    safe, transport = client(clock)
    async with transport:
        await safe.get("https://example.com/page")
        await safe.get("https://example.com/detail")
        await safe.post_json("https://example.com/search", json={"searchText": ""})
        await safe.get("https://example.com/another-board")
    assert [call[2] for call in clock.calls] == [100, 101, 102, 103]


async def test_unrelated_host_does_not_wait_and_existing_long_delay_is_not_added(clock):
    safe, transport = client(clock)
    async with transport:
        await safe.get("https://example.com/page")
        await safe.get("https://other.example/page")
        clock.now += 3  # An adapter's longer Source delay already elapsed.
        await safe.get("https://example.com/detail")
    assert not clock.sleeps


async def test_concurrent_same_host_calls_are_spaced(clock):
    safe, transport = client(clock)
    async with transport:
        await asyncio.gather(*(safe.get(f"https://example.com/{n}") for n in range(4)))
    assert [call[2] for call in clock.calls] == [100, 101, 102, 103]


async def test_retries_and_redirects_also_wait(clock):
    responses = iter(
        [
            httpx.Response(503),
            httpx.Response(302, headers={"location": "/detail"}),
            httpx.Response(200, text="ok"),
        ]
    )
    safe, transport = client(clock, lambda _: next(responses))
    async with transport:
        assert (await safe.get("https://example.com/list")).status_code == 200
    assert [call[2] for call in clock.calls] == [100, 101, 102]


@pytest.mark.parametrize("status", [429, 503])
async def test_retry_after_seconds_delays_next_request_without_new_429_retry(
    clock, status
):
    responses = iter(
        [
            httpx.Response(status, headers={"Retry-After": "5"}),
            httpx.Response(200),
        ]
    )
    safe, transport = client(clock, lambda _: next(responses))
    async with transport:
        first = await safe.get("https://example.com/list")
        if status == 429:
            assert first.status_code == 429 and len(clock.calls) == 1
            await safe.get("https://example.com/another-source")
    assert [call[2] for call in clock.calls] == [100, 105]


async def test_retry_after_http_date_is_respected(clock):
    future = format_datetime(datetime.now(UTC) + timedelta(seconds=10), usegmt=True)
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": future}), httpx.Response(200)]
    )
    safe, transport = client(clock, lambda _: next(responses))
    async with transport:
        await safe.get("https://example.com/list")
        await safe.get("https://example.com/next")
    assert 8 < clock.calls[1][2] - clock.calls[0][2] <= 10


@pytest.mark.parametrize("header", ["invalid", "-1", "NaN", "Infinity"])
async def test_invalid_retry_after_keeps_operational_minimum(clock, header):
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": header}), httpx.Response(200)]
    )
    safe, transport = client(clock, lambda _: next(responses))
    async with transport:
        await safe.get("https://example.com/list")
        await safe.get("https://example.com/next")
    assert [call[2] for call in clock.calls] == [100, 101]


async def test_pacing_cannot_exceed_source_budget_or_send_early(clock):
    safe, transport = client(clock)
    budget = AcquisitionBudget(max_seconds=0.5, clock=lambda: clock.now)
    async with transport:
        with acquisition_scope(budget):
            await safe.get("https://example.com/list")
            with pytest.raises(AdapterExecutionError, match="budget exhausted"):
                await safe.get("https://example.com/next")
    assert len(clock.calls) == budget.requests == 1
    assert not clock.sleeps


@pytest.mark.parametrize("interval", [0, -1, 0.1, 61, float("inf"), float("nan")])
def test_normal_settings_cannot_disable_pacing(interval):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, crawler_min_request_interval_seconds=interval)


async def test_normal_application_and_dependency_fallback_enable_minimum(monkeypatch):
    settings = Settings(_env_file=None)
    assert settings.crawler_min_request_interval_seconds == 1
    app = create_app(settings=settings, engine=AsyncMock())
    app.state.ingestion_runner = AsyncMock()
    monkeypatch.setattr("backend.interfaces.api.main.dispose_engine", AsyncMock())
    async with lifespan(app):
        assert app.state.http_safe_client._min_request_interval == 1
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings))
    )
    fallback = get_safe_http_client(request)
    assert fallback._min_request_interval == 1
    await fallback.aclose()
