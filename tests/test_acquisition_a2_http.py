"""Offline streamed HTTP safety and source budget contracts."""

import gzip
import json
import socket
from unittest.mock import patch

import httpx
import pytest

from backend.application.job_discovery.budget import (
    AcquisitionBudget,
    acquisition_scope,
)
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.http.safe_client import HttpSafeClient


@pytest.fixture(autouse=True)
def public_dns(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
        ],
    )


class Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.read = 0
        self.closed = False

    async def __aiter__(self):
        for chunk in self.chunks:
            self.read += 1
            yield chunk

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("size", [9, 10, 11])
async def test_body_boundary(method, size):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, content=b"x" * size)
        )
    ) as client:
        safe = HttpSafeClient(client=client, max_response_bytes=10)
        operation = safe.get if method == "GET" else safe.post_json
        kwargs = {} if method == "GET" else {"json": {"search": ""}}
        if size > 10:
            with pytest.raises(AdapterExecutionError, match="body limit") as error:
                await operation("https://example.com/jobs", **kwargs)
            assert error.value.code == "RESPONSE_BODY_LIMIT_EXCEEDED"
        else:
            result = await operation("https://example.com/jobs", **kwargs)
            assert result.content_bytes == b"x" * size


@pytest.mark.asyncio
async def test_stream_aborts_early_and_closes_without_leaking(caplog):
    stream = Chunks([b"sensitive" * 10000] * 10)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=stream))
    ) as client:
        safe = HttpSafeClient(client=client, max_response_bytes=65536)
        with pytest.raises(AdapterExecutionError) as error:
            await safe.post_json(
                "https://example.com/jobs", json={"private": "secret-body"}
            )
    assert stream.read < 10 and stream.closed
    assert "sensitive" not in str(error.value) + caplog.text
    assert "secret-body" not in str(error.value) + caplog.text


@pytest.mark.asyncio
async def test_decompressed_body_is_bounded():
    encoded = gzip.compress(b"x" * 100000)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-encoding": "gzip"}, stream=Chunks([encoded])
            )
        )
    ) as client:
        with pytest.raises(AdapterExecutionError, match="body limit"):
            await HttpSafeClient(client=client, max_response_bytes=65536).get(
                "https://example.com/jobs"
            )


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
async def test_post_redirect_contract(status):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/jobs":
            return httpx.Response(status, headers={"location": "/final"})
        return httpx.Response(200, json={"jobs": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        safe = HttpSafeClient(client=client)
        if status in (307, 308):
            result = await safe.post_json(
                "https://example.com/jobs", json={"search": ""}
            )
            assert json.loads(result.text) == {"jobs": []}
            assert [r.method for r in requests] == ["POST", "POST"]
            assert requests[0].content == requests[1].content == b'{"search":""}'
        else:
            with pytest.raises(AdapterExecutionError, match="Ambiguous"):
                await safe.post_json("https://example.com/jobs", json={})
            assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "target",
    [
        "http://127.0.0.1/jobs",
        "http://10.0.0.1/jobs",
        "http://169.254.169.254/jobs",
        "file:///secret",
        "https://user:password@example.com/jobs",
    ],
)
async def test_post_rejects_unsafe_target(target):
    with pytest.raises(AdapterExecutionError, match="SSRF") as error:
        await HttpSafeClient().post_json(target, json={})
    assert "password" not in str(error.value) + str(error.value.details)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location", ["http://127.0.0.1/jobs", "https://other.example/jobs"]
)
async def test_post_rejects_unsafe_or_cross_origin_redirect(location):
    requests = []

    def handler(r):
        requests.append(r)
        return httpx.Response(307, headers={"location": location})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdapterExecutionError):
            await HttpSafeClient(client=client).post_json(
                "https://example.com/jobs", json={}
            )
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_redirect_and_retry_body_limits_and_budget():
    calls = []

    def handler(r):
        calls.append(r)
        if len(calls) == 1:
            return httpx.Response(503, content=b"retry")
        if len(calls) == 2:
            return httpx.Response(307, headers={"location": "/final"}, content=b"hop")
        return httpx.Response(200, content=b"done")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        safe = HttpSafeClient(client=client, retry_delay=0)
        budget = AcquisitionBudget(max_requests=3, max_bytes=12)
        with acquisition_scope(budget):
            result = await safe.post_json("https://example.com/jobs", json={})
        assert result.text == "done"
        assert budget.requests == 3 and budget.bytes_read == 12


@pytest.mark.asyncio
@pytest.mark.parametrize("budget", ["requests", "bytes"])
async def test_budget_cannot_reset_between_calls(budget):
    counter = AcquisitionBudget(
        max_requests=1 if budget == "requests" else 10, max_bytes=5
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"abc"))
    ) as client:
        with acquisition_scope(counter):
            await HttpSafeClient(client=client).get("https://example.com/jobs")
            with pytest.raises(AdapterExecutionError) as error:
                await HttpSafeClient(client=client).get("https://example.com/next")
            assert error.value.code == "ACQUISITION_BUDGET_EXHAUSTED"
            assert error.value.details["reason"] == budget
            with (
                pytest.raises(RuntimeError, match="cannot be reset"),
                acquisition_scope(AcquisitionBudget()),
            ):
                pass
        with acquisition_scope(AcquisitionBudget()) as other:
            await HttpSafeClient(client=client).get("https://example.com/jobs")
            assert other.requests == 1 and other.bytes_read == 3


def test_budget_deadline_uses_monotonic_clock():
    now = [0.0]
    budget = AcquisitionBudget(max_seconds=10, clock=lambda: now[0])
    budget.before_request()
    now[0] = 10
    with pytest.raises(AdapterExecutionError, match="duration"):
        budget.consume_bytes(1)


@pytest.mark.asyncio
async def test_final_redirect_response_also_bounded_and_get_drops_custom_headers():
    requests = []

    def handler(r):
        requests.append(r)
        if len(requests) == 1:
            return httpx.Response(
                302, headers={"location": "https://other.example/final"}
            )
        assert "authorization" not in r.headers and "x-api-key" not in r.headers
        return httpx.Response(200, content=b"x" * 11)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AdapterExecutionError, match="body limit"):
            await HttpSafeClient(client=client, max_response_bytes=10).get(
                "https://example.com/jobs",
                headers={"Authorization": "secret", "X-API-Key": "secret"},
            )


@pytest.mark.asyncio
async def test_managed_client_retains_tls_and_manual_redirects():
    real_client = httpx.AsyncClient
    with patch(
        "backend.infrastructure.http.safe_client.httpx.AsyncClient", wraps=real_client
    ) as constructor:
        async with HttpSafeClient() as safe:
            await safe._get_client()
        assert constructor.call_args.kwargs["verify"] is True
        assert constructor.call_args.kwargs["follow_redirects"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("crawler_max_response_bytes", 0),
        ("crawler_max_source_requests", 10001),
        ("crawler_max_source_bytes", 2**31),
        ("crawler_max_source_seconds", float("inf")),
    ],
)
def test_operational_settings_bounded(field, value):
    with pytest.raises(ValueError):
        Settings(_env_file=None, **{field: value})
