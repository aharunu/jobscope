"""HTTP-based source health probing implementation with SSRF prevention."""

from __future__ import annotations

import asyncio
import logging
import ssl
import time
import urllib.parse
import uuid
from collections.abc import Sequence

import httpx

from backend.application.job_discovery.dtos import (
    SourceBatchProbeResultDTO,
    SourceProbeResultDTO,
)
from backend.application.job_discovery.ports import SourceHealthProbe
from backend.infrastructure.http.ssrf import validate_target_url_safety

logger = logging.getLogger(__name__)

REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})


class HttpSourceHealthProbe(SourceHealthProbe):
    """Source health probe using streaming HTTP requests with SSRF guards."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        user_agent: str = "JobScope/0.1.0 (source-health-probe)",
        max_redirects: int = 5,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._max_redirects = max_redirects
        self._client = client

    async def probe(
        self,
        url: str,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> SourceProbeResultDTO:
        """Probe an individual source URL and return diagnostic metrics."""
        start_time = time.perf_counter()
        current_url = url
        visited_urls = {current_url}

        # Initial SSRF & scheme validation
        is_safe, error_type, error_msg = validate_target_url_safety(current_url)
        if not is_safe:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return SourceProbeResultDTO(
                source_id=source_id,
                url=url,
                is_reachable=False,
                status_code=None,
                latency_ms=latency_ms,
                final_url=current_url,
                redirect_count=0,
                error_type=error_type,
                error_message=error_msg,
                ats_type=ats_type,
            )

        active_client = client or self._client
        if active_client is not None:
            return await self._execute_probe_loop(
                active_client=active_client,
                original_url=url,
                start_url=current_url,
                source_id=source_id,
                ats_type=ats_type,
                start_time=start_time,
                visited_urls=visited_urls,
            )

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            verify=True,
        ) as local_client:
            return await self._execute_probe_loop(
                active_client=local_client,
                original_url=url,
                start_url=current_url,
                source_id=source_id,
                ats_type=ats_type,
                start_time=start_time,
                visited_urls=visited_urls,
            )

    async def _execute_probe_loop(
        self,
        active_client: httpx.AsyncClient,
        original_url: str,
        start_url: str,
        source_id: uuid.UUID | None,
        ats_type: str | None,
        start_time: float,
        visited_urls: set[str],
    ) -> SourceProbeResultDTO:
        current_url = start_url
        redirect_count = 0

        while True:
            try:
                async with active_client.stream(
                    "GET",
                    current_url,
                    headers={
                        "User-Agent": self._user_agent,
                        "Accept": "*/*",
                    },
                ) as response:
                    status = response.status_code

                    # Check for redirect
                    if (
                        status in REDIRECT_STATUS_CODES
                        and "location" in response.headers
                    ):
                        redirect_count += 1
                        if redirect_count > self._max_redirects:
                            latency_ms = round(
                                (time.perf_counter() - start_time) * 1000, 2
                            )
                            return SourceProbeResultDTO(
                                source_id=source_id,
                                url=original_url,
                                is_reachable=False,
                                status_code=status,
                                latency_ms=latency_ms,
                                final_url=current_url,
                                redirect_count=redirect_count - 1,
                                error_type="too_many_redirects",
                                error_message=(
                                    f"Exceeded maximum redirects "
                                    f"({self._max_redirects})"
                                ),
                                ats_type=ats_type,
                            )

                        raw_location = response.headers["location"]
                        next_url = urllib.parse.urljoin(current_url, raw_location)

                        if next_url in visited_urls:
                            latency_ms = round(
                                (time.perf_counter() - start_time) * 1000, 2
                            )
                            return SourceProbeResultDTO(
                                source_id=source_id,
                                url=original_url,
                                is_reachable=False,
                                status_code=status,
                                latency_ms=latency_ms,
                                final_url=next_url,
                                redirect_count=redirect_count,
                                error_type="too_many_redirects",
                                error_message="Detected redirect loop",
                                ats_type=ats_type,
                            )

                        visited_urls.add(next_url)

                        # Validate next URL against SSRF
                        is_safe, err_type, err_msg = validate_target_url_safety(
                            next_url
                        )
                        if not is_safe:
                            latency_ms = round(
                                (time.perf_counter() - start_time) * 1000, 2
                            )
                            return SourceProbeResultDTO(
                                source_id=source_id,
                                url=original_url,
                                is_reachable=False,
                                status_code=None,
                                latency_ms=latency_ms,
                                final_url=next_url,
                                redirect_count=redirect_count,
                                error_type=err_type,
                                error_message=f"Redirect blocked: {err_msg}",
                                ats_type=ats_type,
                            )

                        current_url = next_url
                        continue

                    # Terminal response reached
                    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    is_reachable = 200 <= status < 400
                    error_type: str | None = None
                    error_msg: str | None = None

                    if status >= 500:
                        error_type = "server_error"
                        error_msg = f"HTTP server error: {status}"
                    elif status >= 400:
                        error_type = "client_error"
                        error_msg = f"HTTP client error: {status}"
                    elif status < 200:
                        error_type = "informational"
                        error_msg = f"HTTP informational response: {status}"

                    return SourceProbeResultDTO(
                        source_id=source_id,
                        url=original_url,
                        is_reachable=is_reachable,
                        status_code=status,
                        latency_ms=latency_ms,
                        final_url=current_url,
                        redirect_count=redirect_count,
                        error_type=error_type,
                        error_message=error_msg,
                        ats_type=ats_type,
                    )

            except httpx.TimeoutException:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return SourceProbeResultDTO(
                    source_id=source_id,
                    url=original_url,
                    is_reachable=False,
                    status_code=None,
                    latency_ms=latency_ms,
                    final_url=current_url,
                    redirect_count=redirect_count,
                    error_type="timeout",
                    error_message=(f"Request timed out after {self._timeout_seconds}s"),
                    ats_type=ats_type,
                )
            except (httpx.ConnectError, ssl.SSLError) as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                msg_lower = str(exc).lower()
                if "ssl" in msg_lower or "certificate" in msg_lower:
                    err_type = "ssl_error"
                else:
                    err_type = "connection_failed"
                return SourceProbeResultDTO(
                    source_id=source_id,
                    url=original_url,
                    is_reachable=False,
                    status_code=None,
                    latency_ms=latency_ms,
                    final_url=current_url,
                    redirect_count=redirect_count,
                    error_type=err_type,
                    error_message=f"Connection error: {exc}",
                    ats_type=ats_type,
                )
            except httpx.HTTPError as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return SourceProbeResultDTO(
                    source_id=source_id,
                    url=original_url,
                    is_reachable=False,
                    status_code=None,
                    latency_ms=latency_ms,
                    final_url=current_url,
                    redirect_count=redirect_count,
                    error_type="http_error",
                    error_message=f"HTTP error during probe: {exc}",
                    ats_type=ats_type,
                )
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return SourceProbeResultDTO(
                    source_id=source_id,
                    url=original_url,
                    is_reachable=False,
                    status_code=None,
                    latency_ms=latency_ms,
                    final_url=current_url,
                    redirect_count=redirect_count,
                    error_type="unknown_error",
                    error_message=str(exc),
                    ats_type=ats_type,
                )

    async def probe_batch(
        self,
        sources: Sequence[tuple[uuid.UUID, str, str | None]],
        max_concurrency: int = 10,
    ) -> SourceBatchProbeResultDTO:
        """Probe multiple sources concurrently with bounded concurrency."""
        if not sources:
            return SourceBatchProbeResultDTO(
                total_probed=0,
                reachable_count=0,
                unreachable_count=0,
                results=[],
            )

        sem = asyncio.Semaphore(max(1, max_concurrency))

        active_client = self._client
        if active_client is not None:
            return await self._execute_batch(
                client=active_client,
                sources=sources,
                sem=sem,
            )

        async with httpx.AsyncClient(
            timeout=self._timeout_seconds,
            follow_redirects=False,
            verify=True,
        ) as local_client:
            return await self._execute_batch(
                client=local_client,
                sources=sources,
                sem=sem,
            )

    async def _execute_batch(
        self,
        client: httpx.AsyncClient,
        sources: Sequence[tuple[uuid.UUID, str, str | None]],
        sem: asyncio.Semaphore,
    ) -> SourceBatchProbeResultDTO:
        async def _probe_worker(
            item: tuple[uuid.UUID, str, str | None],
        ) -> SourceProbeResultDTO:
            source_id, url, ats_type = item
            async with sem:
                return await self.probe(
                    url=url,
                    source_id=source_id,
                    ats_type=ats_type,
                    client=client,
                )

        results = await asyncio.gather(
            *[_probe_worker(s) for s in sources],
            return_exceptions=False,
        )

        reachable_count = sum(1 for r in results if r.is_reachable)
        total_probed = len(results)
        unreachable_count = total_probed - reachable_count

        return SourceBatchProbeResultDTO(
            total_probed=total_probed,
            reachable_count=reachable_count,
            unreachable_count=unreachable_count,
            results=list(results),
        )
