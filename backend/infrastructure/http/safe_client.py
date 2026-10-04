"""SSRF-guarded HTTP client implementing the SafeHttpClient application port."""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Any

import httpx

from backend.application.job_discovery.budget import current_budget
from backend.application.job_discovery.dtos import SafeHttpResponseDTO
from backend.application.job_discovery.exceptions import AdapterExecutionError
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.http.ssrf import validate_target_url_safety

logger = logging.getLogger(__name__)

REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
TRANSIENT_STATUS_CODES = frozenset({502, 503, 504})


class HttpSafeClient(SafeHttpClient):
    """Outbound HTTP client enforcing SSRF protection, safe redirects, and retries."""

    def __init__(
        self,
        timeout_seconds: float = 15.0,
        user_agent: str = "JobScope/0.1.0 (crawler; safe-http-client)",
        max_redirects: int = 5,
        max_retries: int = 2,
        retry_delay: float = 0.5,
        client: httpx.AsyncClient | None = None,
        max_response_bytes: int = 15 * 1024 * 1024,
    ) -> None:
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be a positive integer")
        self._max_response_bytes = max_response_bytes
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._max_redirects = max_redirects
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._injected_client = client
        self._local_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Return the active HTTP client instance, creating a managed one if needed."""
        if self._injected_client is not None:
            return self._injected_client

        if self._local_client is None or self._local_client.is_closed:
            self._local_client = httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=False,
                verify=True,
            )
        return self._local_client

    async def aclose(self) -> None:
        """Explicitly close the managed HTTP client session during shutdown."""
        if self._local_client is not None and not self._local_client.is_closed:
            await self._local_client.aclose()
            self._local_client = None

    async def __aenter__(self) -> HttpSafeClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.aclose()

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        return await self._request(
            "GET", url, headers=headers, params=params, timeout=timeout
        )

    async def post_json(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        """Adapter-owned read/search operations only, never mutations."""
        return await self._request(
            "POST", url, headers=headers, json=json, timeout=timeout
        )

    async def _read_response(self, response: httpx.Response) -> SafeHttpResponseDTO:
        body = bytearray()
        budget = current_budget.get()
        try:
            async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                if budget is not None:
                    budget.consume_bytes(len(chunk))
                if len(body) + len(chunk) > self._max_response_bytes:
                    raise AdapterExecutionError(
                        message="Provider response exceeded the response body limit",
                        code="RESPONSE_BODY_LIMIT_EXCEEDED",
                        details={"limit_bytes": self._max_response_bytes},
                    )
                body.extend(chunk)
            content = bytes(body)
            return SafeHttpResponseDTO(
                status_code=response.status_code,
                url=str(response.url),
                headers=dict(response.headers),
                content_bytes=content,
                text=content.decode(response.encoding or "utf-8", errors="replace"),
            )
        finally:
            await response.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        """Perform an SSRF-validated GET request with manual redirect following.

        Args:
            url: Target URL to request.
            headers: Optional HTTP headers to include.
            params: Optional query parameters to append.
            timeout: Optional per-request timeout in seconds.

        Returns:
            SafeHttpResponseDTO containing response status, URL, headers, and body.

        Raises:
            AdapterExecutionError: On SSRF block, timeout, network error,
                or redirect loop.
        """
        # 1. Resolve full URL including query parameters for SSRF check
        request_obj = httpx.Request(method, url, params=params)
        target_url = str(request_obj.url)

        is_safe, error_type, error_msg = validate_target_url_safety(target_url)
        if not is_safe or urllib.parse.urlsplit(target_url).username is not None:
            raise AdapterExecutionError(
                message="SSRF blocked outbound request",
                code="ADAPTER_EXECUTION_FAILURE",
                details={
                    "error_type": error_type,
                },
            )

        req_headers = {"User-Agent": self._user_agent}
        if headers:
            req_headers.update(headers)

        active_client = await self._get_client()
        req_timeout = timeout if timeout is not None else self._timeout_seconds

        current_url = target_url
        visited_urls = {current_url}
        redirect_count = 0
        budget = current_budget.get()

        while True:
            attempt = 0
            while True:
                # SSRF validation before every attempt (including retries)
                is_safe, error_type, error_msg = validate_target_url_safety(current_url)
                if not is_safe:
                    raise AdapterExecutionError(
                        message="SSRF blocked outbound request",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={
                            "error_type": error_type,
                        },
                    )

                if budget is not None:
                    budget.before_request()
                    req_timeout = min(req_timeout, budget.remaining_seconds())
                try:
                    request = active_client.build_request(
                        method,
                        current_url,
                        headers=req_headers,
                        json=json,
                        timeout=req_timeout,
                    )
                    streamed = await active_client.send(
                        request, stream=True, follow_redirects=False
                    )
                    response = await self._read_response(streamed)
                    if (
                        response.status_code in TRANSIENT_STATUS_CODES
                        and attempt < self._max_retries
                    ):
                        attempt += 1
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Transient HTTP %s. Retrying attempt %s/%s",
                            response.status_code,
                            attempt,
                            self._max_retries,
                        )
                        if budget is not None and delay >= budget.remaining_seconds():
                            budget.exhausted("duration")
                        if delay > 0:
                            await asyncio.sleep(delay)
                        continue
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    if attempt < self._max_retries:
                        attempt += 1
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Transient connection error. Retrying attempt %s/%s",
                            attempt,
                            self._max_retries,
                        )
                        if budget is not None and delay >= budget.remaining_seconds():
                            budget.exhausted("duration")
                        if delay > 0:
                            await asyncio.sleep(delay)
                        continue
                    raise AdapterExecutionError(
                        message="Network error during provider request",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"error_type": "network_error"},
                    ) from exc
                except httpx.TimeoutException as exc:
                    raise AdapterExecutionError(
                        message="Provider request timed out",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"error_type": "timeout"},
                    ) from exc
                except (httpx.NetworkError, httpx.RequestError) as exc:
                    raise AdapterExecutionError(
                        message="Network error during provider request",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"error_type": "network_error"},
                    ) from exc

            # Check for redirect status
            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("location")
                if not location:
                    return response

                if method == "POST" and response.status_code not in {307, 308}:
                    raise AdapterExecutionError(
                        message="Ambiguous read-only POST redirect rejected"
                    )
                redirect_count += 1
                if redirect_count > self._max_redirects:
                    raise AdapterExecutionError(
                        message=(
                            f"Too many redirects ({redirect_count}) "
                            f"exceeded limit of {self._max_redirects}."
                        ),
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"redirect_count": redirect_count},
                    )

                next_url = urllib.parse.urljoin(current_url, location)

                if next_url in visited_urls:
                    raise AdapterExecutionError(
                        message="Redirect loop detected",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"redirect_count": redirect_count},
                    )

                is_next_safe, next_err_type, next_err_msg = validate_target_url_safety(
                    next_url
                )
                if (
                    not is_next_safe
                    or urllib.parse.urlsplit(next_url).username is not None
                ):
                    raise AdapterExecutionError(
                        message="SSRF blocked redirect",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={
                            "error_type": next_err_type,
                        },
                    )

                old_url, new_url = httpx.URL(current_url), httpx.URL(next_url)
                same_origin = (old_url.scheme, old_url.host, old_url.port) == (
                    new_url.scheme,
                    new_url.host,
                    new_url.port,
                )
                if method == "POST" and not same_origin:
                    raise AdapterExecutionError(
                        message="Cross-origin read-only POST redirect rejected"
                    )
                if not same_origin:
                    req_headers = {"User-Agent": self._user_agent}
                visited_urls.add(next_url)
                current_url = next_url
                continue

            return response
