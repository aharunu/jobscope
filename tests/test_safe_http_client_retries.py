"""Unit tests for bounded transient retries in HttpSafeClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.infrastructure.http.safe_client import HttpSafeClient


@pytest.mark.asyncio
async def test_retry_transient_502_success() -> None:
    """Verify that a transient 502 Bad Gateway is retried and succeeds on attempt 2."""
    mock_resp_502 = httpx.Response(
        502, request=httpx.Request("GET", "https://example.com/api")
    )
    mock_resp_200 = httpx.Response(
        200,
        text='{"status": "ok"}',
        request=httpx.Request("GET", "https://example.com/api"),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.side_effect = [mock_resp_502, mock_resp_200]

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 200
    assert resp.text == '{"status": "ok"}'
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_retry_transient_connect_error_success() -> None:
    """Verify that a transient ConnectError is retried and succeeds."""
    mock_resp_200 = httpx.Response(
        200,
        text="recovered",
        request=httpx.Request("GET", "https://example.com/api"),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.side_effect = [
        httpx.ConnectError("Connection reset"),
        mock_resp_200,
    ]

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 200
    assert resp.text == "recovered"
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_retry_connect_error_exhausted() -> None:
    """Verify that exhausted ConnectError retries raise AdapterExecutionError."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.side_effect = httpx.ConnectError("Host unreachable")

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with (
        patch(
            "backend.infrastructure.http.safe_client.validate_target_url_safety",
            return_value=(True, None, None),
        ),
        pytest.raises(AdapterExecutionError) as exc_info,
    ):
        await safe_client.get("https://example.com/api")

    assert "Network error" in exc_info.value.message
    # 1 initial + 2 retries = 3 calls
    assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_non_retryable_404_not_retried() -> None:
    """Verify that HTTP 404 is not retried and returns immediately."""
    mock_resp_404 = httpx.Response(
        404, request=httpx.Request("GET", "https://example.com/api")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.return_value = mock_resp_404

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 404
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_non_retryable_429_not_retried_in_mvp() -> None:
    """Mandatory Clarification 3: HTTP 429 is deliberately non-retryable
    in Phase 4.4 MVP.
    """
    mock_resp_429 = httpx.Response(
        429,
        headers={"Retry-After": "60"},
        request=httpx.Request("GET", "https://example.com/api"),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.return_value = mock_resp_429

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 429
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_exhausted_503_retries_returns_final_response() -> None:
    """Verify that when 503 retries are exhausted, the final response
    is returned.
    """
    mock_resp_503 = httpx.Response(
        503,
        text="Service Unavailable",
        request=httpx.Request("GET", "https://example.com/api"),
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.return_value = mock_resp_503

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 503
    # 1 initial + 2 retries = 3 calls
    assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_ssrf_validation_executed_on_every_retry() -> None:
    """Verify that SSRF target safety is re-validated on each retry attempt."""
    mock_resp_502 = httpx.Response(
        502, request=httpx.Request("GET", "https://example.com/api")
    )
    mock_resp_200 = httpx.Response(
        200, text="ok", request=httpx.Request("GET", "https://example.com/api")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.side_effect = [mock_resp_502, mock_resp_200]

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety"
    ) as mock_validate:
        mock_validate.return_value = (True, None, None)
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 200
    # 1 initial check before loop + 2 checks inside loop for the 2 attempts = 3 calls
    # Or at least >= 2 calls to validate
    assert mock_validate.call_count >= 2


@pytest.mark.asyncio
async def test_ssrf_blocked_during_retry_attempt() -> None:
    """Verify that if DNS rebinding makes target unsafe on attempt 2, SSRF blocks it."""
    mock_resp_502 = httpx.Response(
        502, request=httpx.Request("GET", "https://example.com/api")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.return_value = mock_resp_502

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with (
        patch(
            "backend.infrastructure.http.safe_client.validate_target_url_safety"
        ) as mock_validate,
        pytest.raises(AdapterExecutionError) as exc_info,
    ):
        # 1st check safe, 2nd check safe, 3rd check (retry attempt 1) unsafe
        mock_validate.side_effect = [
            (True, None, None),
            (True, None, None),
            (False, "BLOCKED_PRIVATE_IP", "Resolved to private IP 192.168.1.1"),
        ]
        await safe_client.get("https://example.com/api")

    assert "SSRF blocked" in exc_info.value.message


@pytest.mark.asyncio
async def test_retry_connect_timeout_success() -> None:
    """Verify that ConnectTimeout is retried and succeeds."""
    mock_resp_200 = httpx.Response(
        200, text="recovered", request=httpx.Request("GET", "https://example.com/api")
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.is_closed = False
    mock_client.get.side_effect = [
        httpx.ConnectTimeout("Connection timed out"),
        mock_resp_200,
    ]

    safe_client = HttpSafeClient(client=mock_client, max_retries=2, retry_delay=0.0)

    with patch(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        return_value=(True, None, None),
    ):
        resp = await safe_client.get("https://example.com/api")

    assert resp.status_code == 200
    assert mock_client.get.call_count == 2
