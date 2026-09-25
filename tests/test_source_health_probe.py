"""Unit tests for HttpSourceHealthProbe and SSRF security validation."""

from __future__ import annotations

import socket
import uuid

import httpx
import pytest

from backend.application.job_discovery.ports import SourceHealthProbe
from backend.infrastructure.http.source_probe import HttpSourceHealthProbe
from backend.infrastructure.http.ssrf import validate_target_url_safety


def test_probe_protocol_conformance() -> None:
    """Verify HttpSourceHealthProbe implements application SourceHealthProbe port."""
    probe = HttpSourceHealthProbe()
    assert isinstance(probe, SourceHealthProbe)


@pytest.mark.parametrize(
    "blocked_url",
    [
        "http://127.0.0.1/jobs",
        "http://127.0.0.2:8080/careers",
        "http://10.0.0.1/jobs",
        "http://172.16.0.1/jobs",
        "http://192.168.1.1/jobs",
        "http://169.254.169.254/latest/meta-data",
        "http://100.64.0.1/jobs",
        "http://[::1]/jobs",
        "http://[fe80::1]/jobs",
    ],
)
def test_ssrf_validator_blocks_internal_ips(blocked_url: str) -> None:
    """Verify SSRF validator blocks private, loopback, link-local, and NAT IPs."""
    is_safe, err_type, err_msg = validate_target_url_safety(blocked_url)
    assert not is_safe
    assert err_type == "ssrf_blocked"
    assert err_msg is not None


@pytest.mark.parametrize(
    "invalid_url,expected_error",
    [
        ("ftp://example.com/jobs", "unsupported_scheme"),
        ("file:///etc/passwd", "unsupported_scheme"),
        ("gopher://example.com", "unsupported_scheme"),
        ("http://", "invalid_url"),
        ("not-a-url", "unsupported_scheme"),
    ],
)
def test_ssrf_validator_rejects_unsupported_schemes_and_syntax(
    invalid_url: str,
    expected_error: str,
) -> None:
    """Verify schemes other than http/https and invalid URLs are rejected."""
    is_safe, err_type, _ = validate_target_url_safety(invalid_url)
    assert not is_safe
    assert err_type == expected_error


def test_ssrf_validator_handles_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify DNS resolution failure produces dns_resolution_failed error."""

    def mock_getaddrinfo(*args: object, **kwargs: object) -> list[object]:
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
    is_safe, err_type, err_msg = validate_target_url_safety(
        "http://nonexistent.domain.xyz"
    )
    assert not is_safe
    assert err_type == "dns_resolution_failed"
    assert "DNS resolution failed" in (err_msg or "")


@pytest.mark.asyncio
async def test_probe_direct_ssrf_blocked() -> None:
    """Verify direct request to private IP returns ssrf_blocked without HTTP call."""
    probe = HttpSourceHealthProbe()
    result = await probe.probe(
        url="http://127.0.0.1/jobs",
        source_id=uuid.uuid4(),
        ats_type="greenhouse",
    )
    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "ssrf_blocked"
    assert result.redirect_count == 0


@pytest.mark.asyncio
async def test_probe_success_200_ok() -> None:
    """Verify reaching a 200 OK endpoint returns reachable with metrics."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="OK")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        source_id = uuid.uuid4()
        result = await probe.probe(
            url="http://93.184.216.34/careers",
            source_id=source_id,
            ats_type="greenhouse",
        )

    assert result.is_reachable
    assert result.status_code == 200
    assert result.error_type is None
    assert result.error_message is None
    assert result.redirect_count == 0
    assert result.final_url == "http://93.184.216.34/careers"
    assert result.source_id == source_id
    assert result.ats_type == "greenhouse"
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_probe_redirect_followed_safely() -> None:
    """Verify safe public redirect is followed and reports final URL and count."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "http://93.184.216.34/jobs":
            return httpx.Response(
                302,
                headers={"Location": "http://93.184.216.35/careers"},
            )
        return httpx.Response(200, text="Careers Home")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/jobs")

    assert result.is_reachable
    assert result.status_code == 200
    assert result.redirect_count == 1
    assert result.final_url == "http://93.184.216.35/careers"


@pytest.mark.asyncio
async def test_probe_redirect_to_private_ip_is_blocked() -> None:
    """Verify redirect to 127.0.0.1 is blocked before execution."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1:8000/internal-admin"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/jobs")

    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "ssrf_blocked"
    assert "Redirect blocked" in (result.error_message or "")
    assert result.final_url == "http://127.0.0.1:8000/internal-admin"
    assert result.redirect_count == 1


@pytest.mark.asyncio
async def test_probe_redirect_to_metadata_ip_is_blocked() -> None:
    """Verify redirect to AWS metadata 169.254.169.254 is blocked."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            301,
            headers={"Location": "http://169.254.169.254/latest/meta-data"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/jobs")

    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "ssrf_blocked"


@pytest.mark.asyncio
async def test_probe_redirect_to_unsupported_scheme_is_blocked() -> None:
    """Verify redirect to file:/// URL is rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "file:///etc/passwd"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/jobs")

    assert not result.is_reachable
    assert result.error_type == "unsupported_scheme"


@pytest.mark.asyncio
async def test_probe_redirect_loop_detected() -> None:
    """Verify circular redirect loop terminates cleanly."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "http://93.184.216.34/a":
            return httpx.Response(302, headers={"Location": "http://93.184.216.34/b"})
        return httpx.Response(302, headers={"Location": "http://93.184.216.34/a"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/a")

    assert not result.is_reachable
    assert result.error_type == "too_many_redirects"
    assert "loop" in (result.error_message or "").lower()


@pytest.mark.asyncio
async def test_probe_max_redirects_exceeded() -> None:
    """Verify exceeding max redirect hops (5) aborts probe."""
    step = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal step
        step += 1
        return httpx.Response(
            302,
            headers={"Location": f"http://93.184.216.34/step/{step}"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(max_redirects=5, client=client)
        result = await probe.probe(url="http://93.184.216.34/start")

    assert not result.is_reachable
    assert result.error_type == "too_many_redirects"
    assert "maximum redirects" in (result.error_message or "")


@pytest.mark.asyncio
async def test_probe_http_404_not_found() -> None:
    """Verify 404 status marks source as unreachable with client_error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/missing")

    assert not result.is_reachable
    assert result.status_code == 404
    assert result.error_type == "client_error"


@pytest.mark.asyncio
async def test_probe_http_403_forbidden() -> None:
    """Verify 403 status is reported as unreachable client_error per design."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/blocked")

    assert not result.is_reachable
    assert result.status_code == 403
    assert result.error_type == "client_error"


@pytest.mark.asyncio
async def test_probe_http_500_server_error() -> None:
    """Verify 500 status marks source unreachable with server_error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/server-error")

    assert not result.is_reachable
    assert result.status_code == 500
    assert result.error_type == "server_error"


@pytest.mark.asyncio
async def test_probe_timeout() -> None:
    """Verify network timeout returns timeout error."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/slow")

    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "timeout"


@pytest.mark.asyncio
async def test_probe_connection_error() -> None:
    """Verify connection failure returns connection_failed error."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to establish a new connection")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/unreachable")

    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "connection_failed"


@pytest.mark.asyncio
async def test_probe_ssl_error() -> None:
    """Verify SSL certificate failure returns ssl_error."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("SSL: CERTIFICATE_VERIFY_FAILED")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        result = await probe.probe(url="http://93.184.216.34/bad-cert")

    assert not result.is_reachable
    assert result.status_code is None
    assert result.error_type == "ssl_error"


@pytest.mark.asyncio
async def test_probe_batch_empty() -> None:
    """Verify batch probing an empty list returns empty summary."""
    probe = HttpSourceHealthProbe()
    result = await probe.probe_batch([])
    assert result.total_probed == 0
    assert result.reachable_count == 0
    assert result.unreachable_count == 0
    assert result.results == []


@pytest.mark.asyncio
async def test_probe_batch_concurrency() -> None:
    """Verify batch probing multiple sources under concurrency."""
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    id3 = uuid.uuid4()

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "reach" in url_str:
            return httpx.Response(200, text="OK")
        return httpx.Response(404, text="Not Found")

    sources = [
        (id1, "http://93.184.216.34/reach", "greenhouse"),
        (id2, "http://93.184.216.34/miss", "lever"),
        (id3, "http://127.0.0.1/blocked", "custom"),
    ]

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        probe = HttpSourceHealthProbe(client=client)
        batch = await probe.probe_batch(sources, max_concurrency=2)

    assert batch.total_probed == 3
    assert batch.reachable_count == 1
    assert batch.unreachable_count == 2
    assert len(batch.results) == 3
