"""Unit and security tests for HttpSafeClient."""

from __future__ import annotations

import socket

import httpx
import pytest

from backend.application.job_discovery.dtos import SafeHttpResponseDTO
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.http.safe_client import HttpSafeClient


@pytest.fixture(autouse=True)
def mock_dns_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock socket.getaddrinfo to ensure 100% offline, deterministic DNS results."""

    def fake_getaddrinfo(
        host: str,
        port: int | str | None,
        *args: object,
        **kwargs: object,
    ) -> list[object]:
        host_str = str(host).lower()
        if host_str in {"localhost", "loopback.local"}:
            return [
                (
                    socket.AF_INET,
                    socket.SOCK_STREAM,
                    6,
                    "",
                    ("127.0.0.1", int(port or 80)),
                )
            ]
        if host_str == "nonexistent.domain.xyz":
            raise socket.gaierror("Name or service not known")
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", int(port or 80)),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)


def test_http_safe_client_blocks_private_and_loopback_ips() -> None:
    """Outbound requests to private or loopback IPs must be immediately rejected."""
    client = HttpSafeClient()

    blocked_targets = [
        "http://127.0.0.1:8080/test",
        "http://localhost:8000/api",
        "http://10.0.0.1/admin",
        "http://192.168.1.1/config",
        "http://169.254.169.254/latest/meta-data/",
    ]

    for target in blocked_targets:
        with pytest.raises(AdapterExecutionError) as exc_info:
            import asyncio

            asyncio.run(client.get(target))

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert "SSRF blocked" in exc_info.value.message


def test_http_safe_client_blocks_unsupported_schemes() -> None:
    """Outbound requests with schemes other than http or https must be rejected."""
    client = HttpSafeClient()

    unsupported_targets = [
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
        "gopher://example.com",
    ]

    for target in unsupported_targets:
        with pytest.raises(AdapterExecutionError) as exc_info:
            import asyncio

            asyncio.run(client.get(target))

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert "SSRF blocked" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_safe_client_successful_response_mapping() -> None:
    """Verify HTTP GET succeeds and fields are mapped to SafeHttpResponseDTO."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("User-Agent") == "CustomUserAgent/1.0"
        assert request.headers.get("X-Test-Header") == "test-value"
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "application/json", "X-Server": "mock"},
            content=b'{"status": "ok"}',
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(
            user_agent="CustomUserAgent/1.0",
            client=mock_httpx,
        )

        response = await client.get(
            "https://api.example.com/v1/jobs",
            headers={"X-Test-Header": "test-value"},
            params={"limit": 50},
        )

        assert isinstance(response, SafeHttpResponseDTO)
        assert response.status_code == 200
        assert response.text == '{"status": "ok"}'
        assert response.content_bytes == b'{"status": "ok"}'
        assert response.headers.get("x-server") == "mock"
        assert "https://api.example.com/v1/jobs" in response.url


@pytest.mark.asyncio
async def test_http_safe_client_follows_safe_redirects() -> None:
    """Verify safe redirect chains are followed up to max_redirects."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if url_str == "https://example.com/old":
            return httpx.Response(
                status_code=301,
                headers={"Location": "https://example.com/new"},
                request=request,
            )
        if url_str == "https://example.com/new":
            return httpx.Response(
                status_code=200,
                headers={"Content-Type": "text/plain"},
                content=b"Landing page reached",
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(client=mock_httpx)
        response = await client.get("https://example.com/old")

        assert response.status_code == 200
        assert response.text == "Landing page reached"
        assert response.url == "https://example.com/new"


@pytest.mark.asyncio
async def test_http_safe_client_blocks_redirect_to_private_ip() -> None:
    """Redirects targeting private/internal network addresses must be rejected."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=302,
            headers={"Location": "http://127.0.0.1:8000/internal"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(client=mock_httpx)

        with pytest.raises(AdapterExecutionError) as exc_info:
            await client.get("https://example.com/login")

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert "SSRF blocked redirect" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_safe_client_detects_redirect_loop() -> None:
    """Redirect loops must be detected and aborted with an AdapterExecutionError."""

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "loop-a" in url_str:
            return httpx.Response(
                302,
                headers={"Location": "https://example.com/loop-b"},
                request=request,
            )
        if "loop-b" in url_str:
            return httpx.Response(
                302,
                headers={"Location": "https://example.com/loop-a"},
                request=request,
            )
        return httpx.Response(404, request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(client=mock_httpx)

        with pytest.raises(AdapterExecutionError) as exc_info:
            await client.get("https://example.com/loop-a")

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert "Redirect loop detected" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_safe_client_exceeds_max_redirects() -> None:
    """Redirect chains exceeding max_redirects must raise AdapterExecutionError."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        step = int(path.replace("/step-", "")) if "step-" in path else 0
        next_step = step + 1
        return httpx.Response(
            302,
            headers={"Location": f"https://example.com/step-{next_step}"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(max_redirects=3, client=mock_httpx)

        with pytest.raises(AdapterExecutionError) as exc_info:
            await client.get("https://example.com/step-0")

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert "Too many redirects" in exc_info.value.message


@pytest.mark.asyncio
async def test_http_safe_client_timeout_handling() -> None:
    """Request timeouts must be converted to AdapterExecutionError with timeout type."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(client=mock_httpx)

        with pytest.raises(AdapterExecutionError) as exc_info:
            await client.get("https://example.com/slow")

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert exc_info.value.details.get("error_type") == "timeout"


@pytest.mark.asyncio
async def test_http_safe_client_network_error_handling() -> None:
    """Network/connection errors must be converted to AdapterExecutionError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Failed to connect to host")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as mock_httpx:
        client = HttpSafeClient(client=mock_httpx)

        with pytest.raises(AdapterExecutionError) as exc_info:
            await client.get("https://example.com/offline")

        assert exc_info.value.code == "ADAPTER_EXECUTION_FAILURE"
        assert exc_info.value.details.get("error_type") == "network_error"


@pytest.mark.asyncio
async def test_http_safe_client_context_manager_and_aclose() -> None:
    """Verify context manager and aclose manage internal client lifecycle."""
    async with HttpSafeClient() as client:
        assert isinstance(client, HttpSafeClient)
    # Post-context manager: aclose() was called without error
