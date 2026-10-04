"""Greenhouse ATS adapter implementing the ATSAdapter application port."""

from __future__ import annotations

import hashlib
import html
import json
import logging
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
from backend.infrastructure.ats.posting import (
    posting_identity,
    text_value,
    valid_posting_fields,
)
from backend.infrastructure.ats.runtime_config import (
    extract_token,
    greenhouse_runtime_config,
)

logger = logging.getLogger(__name__)

DEFAULT_GREENHOUSE_API_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"


def extract_greenhouse_board_token(source: RuntimeSourceDTO) -> str:
    """Resolve a validated Greenhouse token from config or supported board URL."""
    return extract_token(source, "greenhouse")


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
        config = greenhouse_runtime_config(source, self._default_base_url)
        board_token = config.board_token
        endpoint_url = f"{config.base_url}/{board_token}/jobs"
        jobs: list[DiscoveredJobDTO] = []
        warnings: list[str] = []
        seen_job_ids: set[str] = set()
        params: dict[str, Any] = {"content": "true"}

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
                f"Unexpected HTTP status {response.status_code} from Greenhouse API.",
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
                    "provider": "greenhouse",
                },
            ) from exc

        if not isinstance(data, dict):
            raise MalformedAdapterResultError(
                f"Expected JSON object from Greenhouse API, got {type(data).__name__}.",
                details={"source_id": str(source.id)},
            )

        if "jobs" not in data or not isinstance(data["jobs"], list):
            raise MalformedAdapterResultError(
                "Expected 'jobs' list in Greenhouse API response.",
                details={"source_id": str(source.id)},
            )

        raw_jobs = data["jobs"]
        raw_payload_count = len(raw_jobs)
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        total = meta.get("total")
        valid_total = type(total) is int and total >= 0
        if not valid_total:
            warnings.append("missing_or_invalid_total")
        elif total != raw_payload_count:
            warnings.append("total_count_mismatch")

        for idx, item in enumerate(raw_jobs):
            if not isinstance(item, dict):
                warnings.append(f"Skipped non-dict item at page 1 index {idx}")
                continue

            job_id = posting_identity(item.get("id"))
            if not job_id:
                warnings.append(
                    f"Skipped posting without valid ID at page 1 index {idx}"
                )
                continue

            # Duplicate IDs within the full board undermine coverage proof.
            if job_id in seen_job_ids:
                warnings.append(f"Duplicate posting ID at index {idx}")
                continue

            seen_job_ids.add(job_id)
            if not valid_posting_fields(
                item,
                "title",
                "absolute_url",
                text_keys=("content",),
            ):
                warnings.append(f"Skipped malformed posting at index {idx}")
                continue

            job_url = text_value(item.get("absolute_url"))
            if not job_url:
                job_url = f"https://boards.greenhouse.io/{board_token}/jobs/{job_id}"

            raw_title = item.get("title")
            title = text_value(raw_title) or "Untitled"

            raw_content = json.dumps(item, ensure_ascii=False)
            payload_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

            raw_desc = item.get("content")
            clean_desc = (
                html.unescape(raw_desc).strip() if isinstance(raw_desc, str) else None
            )

            loc_obj = item.get("location")
            if isinstance(loc_obj, dict):
                location = text_value(loc_obj.get("name"))
            elif isinstance(loc_obj, str):
                location = loc_obj.strip() or None
            else:
                location = None

            metadata: dict[str, Any] = {
                "title_available": bool(text_value(raw_title)),
                "company": source.company or source.name,
                "location": location,
                "board_token": board_token,
                "payload_hash": payload_hash,
                "updated_at_upstream": item.get("updated_at"),
                "description": clean_desc or title,
                "description_available": bool(clean_desc),
                "provider_metadata": item.get("metadata"),
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

        is_complete = (
            valid_total
            and total == raw_payload_count == len(seen_job_ids) == len(jobs)
            and not warnings
        )

        return CrawlResultDTO(
            source_id=source.id,
            ats_type=self.ats_type,
            jobs=jobs,
            raw_payload_count=raw_payload_count,
            warnings=warnings,
            metadata={
                "board_token": board_token,
                "pages_fetched": 1,
                "total_available": total if valid_total else None,
                "unique_identities": len(seen_job_ids),
                "total_discovered": len(jobs),
            },
            is_complete=is_complete,
        )
