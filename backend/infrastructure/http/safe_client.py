"""SSRF-guarded HTTP client implementing the SafeHttpClient application port."""

from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Any

import httpx

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
    ) -> None:
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
        request_obj = httpx.Request("GET", url, params=params)
        target_url = str(request_obj.url)

        is_safe, error_type, error_msg = validate_target_url_safety(target_url)
        if not is_safe:
            raise AdapterExecutionError(
                message=f"SSRF blocked outbound request to '{target_url}': {error_msg}",
                code="ADAPTER_EXECUTION_FAILURE",
                details={
                    "url": target_url,
                    "error_type": error_type,
                    "error_message": error_msg,
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

        while True:
            attempt = 0
            while True:
                # SSRF validation before every attempt (including retries)
                is_safe, error_type, error_msg = validate_target_url_safety(current_url)
                if not is_safe:
                    raise AdapterExecutionError(
                        message=(
                            f"SSRF blocked outbound request to '{current_url}': "
                            f"{error_msg}"
                        ),
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={
                            "url": current_url,
                            "error_type": error_type,
                            "error_message": error_msg,
                        },
                    )

                try:
                    response = await active_client.get(
                        current_url,
                        headers=req_headers,
                        timeout=req_timeout,
                    )
                    if (
                        response.status_code in TRANSIENT_STATUS_CODES
                        and attempt < self._max_retries
                    ):
                        attempt += 1
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Transient HTTP %s from '%s'. Retrying attempt %s/%s",
                            response.status_code,
                            current_url,
                            attempt,
                            self._max_retries,
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)
                        continue
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                    if attempt < self._max_retries:
                        attempt += 1
                        delay = self._retry_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Transient connection error requesting '%s'. "
                            "Retrying attempt %s/%s",
                            current_url,
                            attempt,
                            self._max_retries,
                        )
                        if delay > 0:
                            await asyncio.sleep(delay)
                        continue
                    raise AdapterExecutionError(
                        message=f"Network error requesting '{current_url}': {exc}",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"url": current_url, "error_type": "network_error"},
                    ) from exc
                except httpx.TimeoutException as exc:
                    raise AdapterExecutionError(
                        message=f"Request to '{current_url}' timed out: {exc}",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"url": current_url, "error_type": "timeout"},
                    ) from exc
                except (httpx.NetworkError, httpx.RequestError) as exc:
                    raise AdapterExecutionError(
                        message=f"Network error requesting '{current_url}': {exc}",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"url": current_url, "error_type": "network_error"},
                    ) from exc

            # Check for redirect status
            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("location")
                if not location:
                    break

                redirect_count += 1
                if redirect_count > self._max_redirects:
                    raise AdapterExecutionError(
                        message=(
                            f"Too many redirects ({redirect_count}) "
                            f"exceeded limit of {self._max_redirects}."
                        ),
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"url": current_url, "redirect_count": redirect_count},
                    )

                next_url = urllib.parse.urljoin(current_url, location)

                if next_url in visited_urls:
                    raise AdapterExecutionError(
                        message=f"Redirect loop detected at '{next_url}'.",
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={"url": next_url, "cycle": list(visited_urls)},
                    )

                is_next_safe, next_err_type, next_err_msg = validate_target_url_safety(
                    next_url
                )
                if not is_next_safe:
                    raise AdapterExecutionError(
                        message=(
                            f"SSRF blocked redirect to '{next_url}': {next_err_msg}"
                        ),
                        code="ADAPTER_EXECUTION_FAILURE",
                        details={
                            "url": next_url,
                            "error_type": next_err_type,
                            "error_message": next_err_msg,
                        },
                    )

                visited_urls.add(next_url)
                current_url = next_url
                continue

            return SafeHttpResponseDTO(
                status_code=response.status_code,
                url=str(response.url),
                headers=dict(response.headers),
                text=response.text,
                content_bytes=response.content,
            )
