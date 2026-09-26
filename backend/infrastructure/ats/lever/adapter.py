"""Lever ATS adapter implementing the ATSAdapter application port."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import urllib.parse
from typing import Any

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    DiscoveredJobDTO,
    RuntimeSourceDTO,
)
from backend.application.job_discovery.exceptions import (
    AdapterExecutionError,
    InvalidSourceConfigurationError,
    MalformedAdapterResultError,
)
from backend.application.job_discovery.ports import ATSAdapter, SafeHttpClient

logger = logging.getLogger(__name__)

DEFAULT_LEVER_API_BASE_URL = "https://api.lever.co/v0/postings"
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 10


def extract_lever_site_token(source: RuntimeSourceDTO) -> str:
    """Extract and validate the Lever site token from source config or URL.

    Checks adapter_config overrides first, then parses the URL path for
    recognized Lever hostnames (jobs.lever.co or api.lever.co). Rejects non-Lever
    domains (such as careers.unilever.com) to prevent false positives.

    Raises:
        InvalidSourceConfigurationError: If no valid token can be resolved.
    """
    # 1. Explicit configuration overrides
    for key in ("site_token", "board_token", "token", "company_slug"):
        val = source.adapter_config.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()

    # 2. Extract from URL
    if not source.url:
        raise InvalidSourceConfigurationError(
            f"Source '{source.name}' ({source.id}) has no URL configured.",
            details={"source_id": str(source.id)},
        )

    try:
        parsed = urllib.parse.urlsplit(source.url)
    except Exception as exc:
        raise InvalidSourceConfigurationError(
            f"Failed to parse source URL '{source.url}': {exc}",
            details={"source_id": str(source.id), "url": source.url},
        ) from exc

    hostname = (parsed.hostname or "").lower()

    # Reject non-Lever hostnames (e.g. unilever.com)
    if hostname != "lever.co" and not hostname.endswith(".lever.co"):
        raise InvalidSourceConfigurationError(
            f"URL '{source.url}' does not belong to Lever (hostname: '{hostname}').",
            details={
                "source_id": str(source.id),
                "url": source.url,
                "hostname": hostname,
            },
        )

    path_segments = [p for p in parsed.path.strip("/").split("/") if p]

    if hostname == "api.lever.co":
        # Pattern: /v0/postings/{site_token}
        if "postings" in path_segments:
            idx = path_segments.index("postings")
            if idx + 1 < len(path_segments):
                candidate = path_segments[idx + 1].strip()
                if candidate and not candidate.startswith("<"):
                    return candidate
    else:
        # Pattern: jobs.lever.co/{site_token} (or /{site_token}/{job_id})
        if path_segments:
            candidate = path_segments[0].strip()
            if candidate and not candidate.startswith("<"):
                return candidate

    raise InvalidSourceConfigurationError(
        f"Cannot resolve Lever site token from source '{source.name}' "
        f"({source.id}) URL: '{source.url}'",
        details={"source_id": str(source.id), "url": source.url},
    )


class LeverAdapter(ATSAdapter):
    """Adapter for crawling job postings from the Lever public postings API."""

    def __init__(
        self,
        http_client: SafeHttpClient,
        default_base_url: str = DEFAULT_LEVER_API_BASE_URL,
    ) -> None:
        self._http_client = http_client
        self._default_base_url = default_base_url.rstrip("/")

    @property
    def ats_type(self) -> str:
        return "lever"

    async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
        """Crawl open postings from Lever for the given runtime source."""
        site_token = extract_lever_site_token(source)

        base_url = (
            source.endpoint_config.get("base_url") or self._default_base_url
        ).rstrip("/")
        endpoint_url = f"{base_url}/{site_token}"

        page_size = int(source.pagination_config.get("page_size", DEFAULT_PAGE_SIZE))
        max_pages = int(source.pagination_config.get("max_pages", DEFAULT_MAX_PAGES))
        pagination_mode = source.pagination_config.get("pagination_mode", "cursor")

        # Rate limiting: minimal delay between pagination calls
        delay_seconds = float(
            source.rate_limit_config.get("delay_seconds")
            or source.rate_limit_config.get("request_delay_seconds")
            or 0.0
        )

        jobs: list[DiscoveredJobDTO] = []
        warnings: list[str] = []
        raw_payload_count = 0
        pages_fetched = 0
        current_skip: str | int | None = None
        is_complete = False

        while True:
            if pages_fetched > 0 and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            params: dict[str, Any] = {"mode": "json", "limit": page_size}
            if current_skip is not None:
                params["skip"] = current_skip

            response = await self._http_client.get(endpoint_url, params=params)

            if response.status_code == 404:
                raise InvalidSourceConfigurationError(
                    f"Lever board '{site_token}' not found (HTTP 404).",
                    details={
                        "source_id": str(source.id),
                        "status_code": 404,
                        "site_token": site_token,
                    },
                )
            if response.status_code == 429:
                raise AdapterExecutionError(
                    f"Rate limited by Lever API (HTTP 429) for '{site_token}'.",
                    code="ADAPTER_EXECUTION_FAILURE",
                    details={"source_id": str(source.id), "status_code": 429},
                )
            if response.status_code >= 500:
                raise AdapterExecutionError(
                    f"Lever upstream server error (HTTP {response.status_code}).",
                    code="ADAPTER_EXECUTION_FAILURE",
                    details={
                        "source_id": str(source.id),
                        "status_code": response.status_code,
                    },
                )
            if response.status_code != 200:
                raise AdapterExecutionError(
                    f"Unexpected HTTP status {response.status_code} from Lever API.",
                    code="ADAPTER_EXECUTION_FAILURE",
                    details={
                        "source_id": str(source.id),
                        "status_code": response.status_code,
                    },
                )

            try:
                data = json.loads(response.text)
            except json.JSONDecodeError as exc:
                raise MalformedAdapterResultError(
                    f"Lever API response is not valid JSON: {exc}",
                    details={
                        "source_id": str(source.id),
                        "response_preview": response.text[:200],
                    },
                ) from exc

            if not isinstance(data, list):
                raise MalformedAdapterResultError(
                    f"Expected JSON list from Lever API, got {type(data).__name__}.",
                    details={"source_id": str(source.id)},
                )

            raw_payload_count += len(data)
            pages_fetched += 1

            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    warnings.append(
                        f"Skipped non-dict item at page {pages_fetched} index {idx}"
                    )
                    continue

                raw_job_id = item.get("id")
                job_id = str(raw_job_id).strip() if raw_job_id else None

                job_url = item.get("hostedUrl") or item.get("applyUrl")
                if not job_url and job_id:
                    job_url = f"https://jobs.lever.co/{site_token}/{job_id}"

                if not job_url:
                    warnings.append(
                        f"Skipped posting without URL (id: {job_id}) "
                        f"on page {pages_fetched}"
                    )
                    continue

                raw_title = item.get("text")
                title = str(raw_title).strip() if raw_title else "Untitled"

                raw_content = json.dumps(item, ensure_ascii=False)
                payload_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

                categories = (
                    item.get("categories")
                    if isinstance(item.get("categories"), dict)
                    else {}
                )
                location = categories.get("location") or item.get("country")

                metadata: dict[str, Any] = {
                    "company": source.company or source.name,
                    "location": location,
                    "categories": categories,
                    "workplace_type": item.get("workplaceType"),
                    "created_at_upstream": item.get("createdAt"),
                    "payload_hash": payload_hash,
                    "site_token": site_token,
                }

                jobs.append(
                    DiscoveredJobDTO(
                        external_job_id=job_id,
                        url=str(job_url),
                        title=title,
                        raw_content=raw_content,
                        content_type="application/json",
                        metadata=metadata,
                    )
                )

            # Check pagination termination
            if len(data) < page_size:
                # All postings retrieved naturally
                is_complete = True
                break

            if pages_fetched >= max_pages:
                warnings.append("pagination_max_pages_reached")
                is_complete = False
                break

            # Calculate next cursor/offset
            if pagination_mode == "offset":
                current_skip = (
                    int(current_skip) if current_skip is not None else 0
                ) + len(data)
            else:
                last_item = data[-1] if data else None
                if not isinstance(last_item, dict) or not last_item.get("id"):
                    is_complete = False
                    break
                current_skip = str(last_item["id"])

        return CrawlResultDTO(
            source_id=source.id,
            ats_type=self.ats_type,
            jobs=jobs,
            raw_payload_count=raw_payload_count,
            warnings=warnings,
            metadata={
                "site_token": site_token,
                "pages_fetched": pages_fetched,
                "total_discovered": len(jobs),
            },
            is_complete=is_complete,
        )
