"""Greenhouse ATS adapter implementing the ATSAdapter application port."""

from __future__ import annotations

import asyncio
import hashlib
import html
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

DEFAULT_GREENHOUSE_API_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 10


def extract_greenhouse_board_token(source: RuntimeSourceDTO) -> str:
    """Extract and validate the Greenhouse board token from source config or URL.

    Checks adapter_config overrides first, then parses the URL path and query
    for recognized Greenhouse hostnames (e.g. boards.greenhouse.io,
    job-boards.greenhouse.io, boards-api.greenhouse.io, or EU equivalents).
    Rejects non-Greenhouse domains to prevent false positives.

    Raises:
        InvalidSourceConfigurationError: If no valid token can be resolved.
    """
    # 1. Explicit configuration overrides
    for key in ("board_token", "site_token", "token", "company_slug"):
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

    # Reject non-Greenhouse hostnames
    if hostname != "greenhouse.io" and not hostname.endswith(".greenhouse.io"):
        raise InvalidSourceConfigurationError(
            f"URL '{source.url}' does not belong to Greenhouse "
            f"(hostname: '{hostname}').",
            details={
                "source_id": str(source.id),
                "url": source.url,
                "hostname": hostname,
            },
        )

    # Check query params for embed board links like: /embed/job_board?for=twitch
    if parsed.query:
        query_params = urllib.parse.parse_qs(parsed.query)
        for_param = query_params.get("for")
        if for_param and for_param[0].strip():
            candidate = for_param[0].strip()
            if not candidate.startswith("<"):
                return candidate

    path_segments = [p for p in parsed.path.strip("/").split("/") if p]

    # Pattern: boards-api.greenhouse.io/v1/boards/{board_token}/jobs
    if hostname.startswith("boards-api."):
        if "boards" in path_segments:
            idx = path_segments.index("boards")
            if idx + 1 < len(path_segments):
                candidate = path_segments[idx + 1].strip()
                if candidate and not candidate.startswith("<"):
                    return candidate
    else:
        # Pattern: boards.greenhouse.io/{board_token} or
        # job-boards.greenhouse.io/{board_token}
        if path_segments:
            if path_segments[0] == "embed":
                if len(path_segments) > 1:
                    candidate = path_segments[1].strip()
                    if candidate and not candidate.startswith("<"):
                        return candidate
            else:
                candidate = path_segments[0].strip()
                if candidate and not candidate.startswith("<"):
                    return candidate

    raise InvalidSourceConfigurationError(
        f"Cannot resolve Greenhouse board token from source '{source.name}' "
        f"({source.id}) URL: '{source.url}'",
        details={"source_id": str(source.id), "url": source.url},
    )


class GreenhouseAdapter(ATSAdapter):
    """Adapter for crawling job postings from the Greenhouse public Job Board API."""

    def __init__(
        self,
        http_client: SafeHttpClient,
        default_base_url: str = DEFAULT_GREENHOUSE_API_BASE_URL,
    ) -> None:
        self._http_client = http_client
        self._default_base_url = default_base_url.rstrip("/")

    @property
    def ats_type(self) -> str:
        return "greenhouse"

    async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
        """Crawl open postings from Greenhouse for the given runtime source."""
        board_token = extract_greenhouse_board_token(source)

        base_url = (
            source.endpoint_config.get("base_url") or self._default_base_url
        ).rstrip("/")
        endpoint_url = f"{base_url}/{board_token}/jobs"

        page_size = int(source.pagination_config.get("page_size", DEFAULT_PAGE_SIZE))
        max_pages = int(source.pagination_config.get("max_pages", DEFAULT_MAX_PAGES))
        pagination_mode = source.pagination_config.get("pagination_mode", "page")

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
        current_page = 1
        seen_job_ids: set[str] = set()
        is_complete = False

        while True:
            if pages_fetched > 0 and delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            params: dict[str, Any] = {"content": "true"}
            if pagination_mode != "none":
                params["page"] = current_page
                params["per_page"] = page_size

            response = await self._http_client.get(endpoint_url, params=params)

            if response.status_code == 404:
                raise InvalidSourceConfigurationError(
                    f"Greenhouse board '{board_token}' not found (HTTP 404).",
                    details={
                        "source_id": str(source.id),
                        "status_code": 404,
                        "board_token": board_token,
                    },
                )
            if response.status_code == 429:
                raise AdapterExecutionError(
                    f"Rate limited by Greenhouse API (HTTP 429) for '{board_token}'.",
                    code="ADAPTER_EXECUTION_FAILURE",
                    details={"source_id": str(source.id), "status_code": 429},
                )
            if response.status_code >= 500:
                raise AdapterExecutionError(
                    f"Greenhouse upstream server error (HTTP {response.status_code}).",
                    code="ADAPTER_EXECUTION_FAILURE",
                    details={
                        "source_id": str(source.id),
                        "status_code": response.status_code,
                    },
                )
            if response.status_code != 200:
                raise AdapterExecutionError(
                    f"Unexpected HTTP status {response.status_code} "
                    "from Greenhouse API.",
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
                    f"Greenhouse API response is not valid JSON: {exc}",
                    details={
                        "source_id": str(source.id),
                        "response_preview": response.text[:200],
                    },
                ) from exc

            if not isinstance(data, dict):
                raise MalformedAdapterResultError(
                    "Expected JSON object from Greenhouse API, "
                    f"got {type(data).__name__}.",
                    details={"source_id": str(source.id)},
                )

            if "jobs" not in data or not isinstance(data["jobs"], list):
                raise MalformedAdapterResultError(
                    "Expected 'jobs' list in Greenhouse API response.",
                    details={"source_id": str(source.id)},
                )

            raw_jobs = data["jobs"]
            raw_payload_count += len(raw_jobs)
            pages_fetched += 1
            new_jobs_on_page = 0

            for idx, item in enumerate(raw_jobs):
                if not isinstance(item, dict):
                    warnings.append(
                        f"Skipped non-dict item at page {pages_fetched} index {idx}"
                    )
                    continue

                raw_job_id = item.get("id")
                job_id = str(raw_job_id).strip() if raw_job_id is not None else None
                if not job_id:
                    warnings.append(
                        "Skipped posting without valid ID at page "
                        f"{pages_fetched} index {idx}"
                    )
                    continue

                # Cross-page duplicate prevention within single crawl
                if job_id in seen_job_ids:
                    continue

                seen_job_ids.add(job_id)
                new_jobs_on_page += 1

                job_url = item.get("absolute_url")
                if not job_url:
                    job_url = (
                        f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"
                    )

                raw_title = item.get("title")
                title = str(raw_title).strip() if raw_title else "Untitled"

                raw_content = json.dumps(item, ensure_ascii=False)
                payload_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

                raw_desc = item.get("content")
                clean_desc = (
                    html.unescape(raw_desc).strip()
                    if isinstance(raw_desc, str)
                    else None
                )

                loc_obj = item.get("location")
                if isinstance(loc_obj, dict):
                    location = loc_obj.get("name")
                elif isinstance(loc_obj, str):
                    location = loc_obj.strip() or None
                else:
                    location = None

                metadata: dict[str, Any] = {
                    "company": source.company or source.name,
                    "location": location,
                    "board_token": board_token,
                    "payload_hash": payload_hash,
                    "updated_at_upstream": item.get("updated_at"),
                    "created_at_upstream": item.get("updated_at"),
                    "published_at": item.get("updated_at"),
                    "description": clean_desc,
                    "departments": item.get("departments"),
                    "offices": item.get("offices"),
                    "requisition_id": item.get("requisition_id"),
                    "internal_job_id": item.get("internal_job_id"),
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

            # Pagination termination & completeness evaluation
            if pagination_mode == "none":
                is_complete = True
                break

            # Natural exhaustion: page has fewer items than page_size
            # (or 0 items on empty board / subsequent page)
            if len(raw_jobs) < page_size:
                is_complete = True
                break

            # Server returned unpaginated list (larger than requested page_size)
            if len(raw_jobs) > page_size:
                is_complete = True
                break

            # Check meta.total if available from upstream response
            meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
            total_meta = meta.get("total")
            if isinstance(total_meta, int) and len(seen_job_ids) >= total_meta:
                is_complete = True
                break

            # Infinite loop protection: non-empty page produced zero new jobs
            if len(raw_jobs) > 0 and new_jobs_on_page == 0:
                warnings.append("duplicate_page_detected")
                is_complete = False
                break

            # Max pages check
            if pages_fetched >= max_pages:
                warnings.append("pagination_max_pages_reached")
                is_complete = False
                break

            current_page += 1

        return CrawlResultDTO(
            source_id=source.id,
            ats_type=self.ats_type,
            jobs=jobs,
            raw_payload_count=raw_payload_count,
            warnings=warnings,
            metadata={
                "board_token": board_token,
                "pages_fetched": pages_fetched,
                "total_discovered": len(jobs),
            },
            is_complete=is_complete,
        )
