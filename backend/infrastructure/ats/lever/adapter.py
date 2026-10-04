"""Lever ATS adapter implementing the ATSAdapter application port."""

from __future__ import annotations

import asyncio
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
    lever_runtime_config,
)

logger = logging.getLogger(__name__)

DEFAULT_LEVER_API_BASE_URL = "https://api.lever.co/v0/postings"
DEFAULT_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 10


def extract_lever_site_token(source: RuntimeSourceDTO) -> str:
    """Resolve a validated Lever path token from config or supported board URL."""
    return extract_token(source, "lever")


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
        config = lever_runtime_config(source, self._default_base_url)
        site_token = config.site_token
        endpoint_url = f"{config.base_url}/{site_token}"
        jobs: list[DiscoveredJobDTO] = []
        warnings: list[str] = []
        raw_payload_count = 0
        pages_fetched = 0
        offset = 0
        exhausted = False
        seen_ids: set[str] = set()

        for _ in range(config.max_pages):
            if pages_fetched > 0 and config.delay_seconds > 0:
                await asyncio.sleep(config.delay_seconds)
            params: dict[str, Any] = {
                "mode": "json",
                "limit": config.page_size,
                "skip": offset,
            }

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
                        "page_number": pages_fetched + 1,
                    },
                ) from exc

            if not isinstance(data, list):
                raise MalformedAdapterResultError(
                    f"Expected JSON list from Lever API, got {type(data).__name__}.",
                    details={"source_id": str(source.id)},
                )

            raw_payload_count += len(data)
            pages_fetched += 1

            overlap = False
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    warnings.append(
                        f"Skipped non-dict item at page {pages_fetched} index {idx}"
                    )
                    continue
                job_id = posting_identity(item.get("id"))
                if job_id is None:
                    warnings.append(
                        f"Skipped posting without valid ID at page {pages_fetched} "
                        f"index {idx}"
                    )
                    continue
                if job_id in seen_ids:
                    overlap = True
                    continue
                seen_ids.add(job_id)
                if not valid_posting_fields(
                    item,
                    "text",
                    "hostedUrl",
                    "applyUrl",
                    text_keys=(
                        "description",
                        "descriptionBody",
                        "descriptionPlain",
                        "descriptionBodyPlain",
                        "opening",
                        "openingPlain",
                        "additional",
                        "additionalPlain",
                    ),
                ):
                    warnings.append(
                        f"Skipped malformed posting at page {pages_fetched} index {idx}"
                    )
                    continue
                title = text_value(item.get("text")) or "Untitled"
                board_host = (
                    "jobs.eu.lever.co" if config.region == "eu" else "jobs.lever.co"
                )
                job_url = (
                    text_value(item.get("hostedUrl"))
                    or text_value(item.get("applyUrl"))
                    or f"https://{board_host}/{site_token}/{job_id}"
                )
                categories = (
                    item.get("categories")
                    if isinstance(item.get("categories"), dict)
                    else {}
                )
                desc_html, desc_plain, responsibilities = lever_descriptions(item)
                raw_content = json.dumps(item, ensure_ascii=False)
                metadata: dict[str, Any] = {
                    "title_available": bool(text_value(item.get("text"))),
                    "company": source.company or source.name,
                    "location": text_value(categories.get("location"))
                    or text_value(item.get("country")),
                    "categories": categories,
                    "employment_type": canonical_employment(
                        categories.get("commitment")
                    ),
                    "work_mode": canonical_work_mode(item.get("workplaceType")),
                    # Raw values must not enter the normalizer's fallback aliases.
                    "provider": {
                        "commitment": categories.get("commitment"),
                        "workplace_type": item.get("workplaceType"),
                        "created_at": item.get("createdAt"),
                    },
                    "apply_url": item.get("applyUrl"),
                    "team": categories.get("team"),
                    "department": categories.get("department"),
                    "lists": item.get("lists"),
                    "payload_hash": hashlib.sha256(
                        raw_content.encode("utf-8")
                    ).hexdigest(),
                    "site_token": site_token,
                    "description_plain": desc_plain,
                    "description_available": bool(desc_html or desc_plain),
                    "description": desc_html or desc_plain or title,
                    "responsibilities": responsibilities,
                }
                jobs.append(
                    DiscoveredJobDTO(
                        external_job_id=job_id,
                        url=job_url,
                        title=title,
                        raw_content=raw_content,
                        content_type="application/json",
                        metadata=metadata,
                    )
                )

            if overlap:
                warnings.append("duplicate_or_overlapping_page_detected")
                break
            if len(data) > config.page_size:
                warnings.append("unexpected_page_size")
                break
            if len(data) < config.page_size:
                exhausted = True
                break
            offset += len(data)
        if not exhausted and pages_fetched == config.max_pages:
            warnings.append("pagination_max_pages_reached")

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
                "unique_identities": len(seen_ids),
                "region": config.region,
            },
            is_complete=exhausted and not warnings,
        )


def canonical_employment(value: Any) -> str | None:
    key = text_value(value)
    if key is None:
        return None
    key = key.casefold().replace("-", "").replace(" ", "")
    return {
        "fulltime": "Full-time",
        "parttime": "Part-time",
        "contract": "Contract",
        "intern": "Internship",
        "internship": "Internship",
    }.get(key)


def canonical_work_mode(value: Any) -> str | None:
    key = text_value(value)
    if key is None:
        return None
    key = key.casefold().replace("-", "").replace(" ", "")
    return {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}.get(key)


def lever_descriptions(
    item: dict[str, Any],
) -> tuple[str | None, str | None, str | None]:
    """Keep combined opening/body once, then all sections and closing content."""
    description = text_value(item.get("description"))
    if not description:
        description = "\n".join(
            filter(
                None,
                [
                    text_value(item.get("opening")),
                    text_value(item.get("descriptionBody")),
                ],
            )
        )
    plain = text_value(item.get("descriptionPlain"))
    if not plain:
        plain = "\n".join(
            filter(
                None,
                [
                    text_value(item.get("openingPlain")),
                    text_value(item.get("descriptionBodyPlain")),
                ],
            )
        )
    sections = []
    responsibilities = []
    lists = item.get("lists")
    if isinstance(lists, list):
        for section in lists:
            if not isinstance(section, dict):
                continue
            heading = text_value(section.get("text")) or ""
            content = text_value(section.get("content"))
            if content:
                sections.append(f"<h3>{html.escape(heading)}</h3>\n{content}")
                if "responsibilit" in heading.casefold():
                    responsibilities.append(content)
    # A plain-only opening remains complete even when section content is HTML.
    full = "\n".join(
        filter(
            None,
            [
                description or plain,
                *sections,
                text_value(item.get("additional"))
                or text_value(item.get("additionalPlain")),
            ],
        )
    )
    plain_full = "\n".join(
        filter(None, [plain, text_value(item.get("additionalPlain"))])
    )
    return full or None, plain_full or None, "\n".join(responsibilities) or None
