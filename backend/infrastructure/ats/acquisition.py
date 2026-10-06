"""Provider-neutral validation, HTTP handling and record/coverage accounting."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated
from urllib.parse import unquote, urljoin, urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from backend.application.job_discovery.budget import current_budget
from backend.application.job_discovery.detail_plan import current_detail_plan
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
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.posting import posting_identity, text_value
from backend.infrastructure.ats.source_binding import (
    invalid,
    safe_url,
    source_binding,
    token,
)


class ProviderRuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    host: str
    board: str = ""
    tenant: str = ""
    site: str = ""
    locale: str = ""
    page_size: Annotated[StrictInt, Field(ge=1, le=100)] = 100
    max_pages: Annotated[StrictInt, Field(ge=1, le=1000)] = 100
    delay_seconds: Annotated[
        float, Field(strict=True, ge=0, le=60, allow_inf_nan=False)
    ] = 0.0


def runtime_config(
    source: RuntimeSourceDTO,
    cls: type[ProviderRuntimeConfig],
    provider: str,
    *,
    page_size: int = 100,
):
    binding = source_binding(source.url, provider, source.adapter_config)
    # Overrides may clarify an Oracle root, never move a Source to another board/host.
    for key in ("board", "tenant", "site", "locale", "host"):
        configured = source.adapter_config.get(key, source.endpoint_config.get(key))
        if configured is not None:
            if key != "host":
                token(configured)
            if key in binding and configured != binding[key]:
                raise invalid("Source URL and configured board binding must agree.")
            binding[key] = configured
    for alias in ("board_token", "site_token", "company_slug", "token"):
        if alias in source.adapter_config and source.adapter_config[
            alias
        ] != binding.get("board"):
            raise invalid("Source URL and configured token must agree.")
    if provider == "workday":
        binding.setdefault("locale", "en-US")
    if provider == "oracle" and (not binding.get("site") or not binding.get("locale")):
        raise invalid("Oracle /hcmUI requires explicit site and locale configuration.")
    if provider in {"oracle", "workday"} and not re.fullmatch(
        r"[a-z]{2}(?:-[A-Z]{2})?", binding.get("locale", "en-US")
    ):
        raise invalid("Invalid provider locale configuration.")
    if "base_url" in source.endpoint_config:
        raise invalid(
            "Endpoint base overrides are unsupported; use the validated Source URL."
        )
    mode = source.pagination_config.get("pagination_mode", "offset")
    if not isinstance(mode, str) or mode not in {"offset", "none"}:
        raise invalid("Unsupported provider pagination mode.")
    try:
        return cls(
            **binding,
            page_size=source.pagination_config.get("page_size", page_size),
            max_pages=source.pagination_config.get("max_pages", 100),
            delay_seconds=source.rate_limit_config.get(
                "delay_seconds",
                source.rate_limit_config.get("request_delay_seconds", 0.0),
            ),
        )
    except ValidationError as exc:
        raise invalid("Invalid provider pagination/delay configuration.") from exc


def malformed(message: str):
    return MalformedAdapterResultError(message, status_code=502)


class AcquisitionRequests:
    """Pace every list/detail call; safe layer owns attempts, caps and budgets."""

    def __init__(self, client: SafeHttpClient, delay: float):
        self.client, self.delay, self.count = client, delay, 0

    async def response(self, url: str, *, params=None, body=None):
        if self.count and self.delay:
            await asyncio.sleep(self.delay)
        self.count += 1
        if body is None:
            result = await self.client.get(url, params=params)
        else:
            result = await self.client.post_json(url, json=body)
        if result.status_code != 200:
            raise AdapterExecutionError(
                "Provider acquisition HTTP request failed.",
                details={"status_code": result.status_code},
            )
        requested, final = safe_url(url), safe_url(result.url)
        if (
            requested.scheme != final.scheme
            or requested.hostname != final.hostname
            or requested.path.rstrip("/") != final.path.rstrip("/")
        ):
            raise AdapterExecutionError("Provider redirect changed the board binding.")
        return result

    async def json(self, url: str, *, params=None, body=None):
        response = await self.response(url, params=params, body=body)
        try:
            result = json.loads(response.text)
        except (ValueError, RecursionError) as exc:
            raise malformed("Provider response is not valid JSON.") from exc
        if not isinstance(result, dict):
            raise malformed("Provider response must be an object.")
        return result


def require_list(root: dict, key: str) -> list:
    values = root.get(key)
    if not isinstance(values, list):
        raise malformed("Provider collection is missing or malformed.")
    return values


def count(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def employment(value: object) -> str | None:
    name = text_value(value)
    if not name:
        return None
    key = re.sub(r"[\s_-]+", "", name).casefold()
    return {
        "fulltime": "Full-time",
        "parttime": "Part-time",
        "contract": "Contract",
        "contractor": "Contract",
        "intern": "Internship",
        "internship": "Internship",
    }.get(key)


def work_mode(value: object, remote: object = None) -> str | None:
    name = text_value(value)
    if name:
        key = re.sub(r"[\s_-]+", "", name).casefold()
        return {
            "remote": "Remote",
            "telecommute": "Remote",
            "hybrid": "Hybrid",
            "onsite": "On-site",
        }.get(key)
    # false alone is not proof of onsite (could be hybrid).
    return "Remote" if remote is True else None


def mapping(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def location(value: object) -> str | None:
    if isinstance(value, str):
        return text_value(value)
    item = mapping(value)
    address = mapping(item.get("address")) or item
    return (
        text_value(item.get("fullLocation"))
        or ", ".join(
            filter(
                None,
                (
                    text_value(address.get(key))
                    for key in (
                        "addressLocality",
                        "city",
                        "addressRegion",
                        "state",
                        "addressCountry",
                        "country",
                    )
                ),
            )
        )
        or None
    )


def exact_date(value: object) -> str | None:
    text = text_value(value)
    if not text or not re.match(r"^\d{4}-\d{2}-\d{2}(?:T|$)", text):
        return None
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return text


def bound_url(value: object, base: str, *, prefix: str = "") -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        resolved = urljoin(base, value)
        p, origin = safe_url(resolved), safe_url(base)
        if (
            p.scheme != "https"
            or p.hostname != origin.hostname
            or p.port not in {None, 443}
            or (prefix and not p.path.startswith(prefix))
        ):
            return None
        return resolved
    except InvalidSourceConfigurationError:
        return None


def path_identity(value: object, base: str, prefix: str) -> str | None:
    url = bound_url(value, base, prefix=prefix)
    if not url:
        return None
    part = unquote(urlsplit(url).path.rstrip("/").split("/")[-1])
    return posting_identity(part)


def project(
    source: RuntimeSourceDTO,
    raw: object,
    *,
    identity: object,
    url: str | None,
    title: object,
    description: object = None,
    plain: object = None,
    **metadata,
) -> DiscoveredJobDTO | None:
    identifier, name = posting_identity(identity), text_value(title)
    if not identifier or not name or not url:
        return None
    # Reject malformed supplied essentials rather than serializing them as prose.
    if description is not None and not isinstance(description, str):
        return None
    if plain is not None and not isinstance(plain, str):
        return None
    html, text = text_value(description), text_value(plain)
    return DiscoveredJobDTO(
        identifier,
        url,
        name,
        json.dumps(raw, ensure_ascii=False),
        "application/json",
        {
            "company": source.company or source.name,
            "title_available": True,
            "description_available": bool(html or text),
            "description": html or text or name,
            "description_plain": text,
            **metadata,
        },
    )


@dataclass
class Coverage:
    source: RuntimeSourceDTO
    jobs: list[DiscoveredJobDTO] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    received: int = 0

    def warn(self, reason: str):
        if reason not in self.warnings:
            self.warnings.append(reason)

    def add(self, job: DiscoveredJobDTO | None) -> bool:
        self.received += 1
        if job is None:
            self.warn("malformed_or_unidentified_posting")
            return False
        if job.external_job_id in self.seen:
            self.warn("duplicate_or_overlapping_page_detected")
            return False
        self.seen.add(job.external_job_id)
        self.jobs.append(job)
        return True

    def result(self, proven: bool, requests: AcquisitionRequests, **diagnostics):
        if not proven:
            self.warn("acquisition_coverage_not_proven")
        return CrawlResultDTO(
            self.source.id,
            self.source.ats_type,
            self.jobs,
            self.received,
            self.warnings,
            {
                "requests": requests.count,
                "received": self.received,
                "unique": len(self.seen),
                "mapped": len(self.jobs),
                **diagnostics,
            },
            proven and not self.warnings,
        )


def retain_partial(coverage: Coverage, requests: AcquisitionRequests):
    """Register validated observations before any budget can interrupt acquisition."""
    budget = current_budget.get()
    if budget is None:
        return

    def snapshot():
        if not coverage.jobs:
            return None
        coverage.warn("acquisition_budget_exhausted_partial_results")
        return coverage.result(False, requests)

    budget.partial_snapshot = snapshot


def defer_detail(summary: DiscoveredJobDTO | None, coverage: Coverage) -> bool:
    plan = current_detail_plan.get()
    reason = plan.defer(summary) if plan else None
    if reason is None:
        return False
    summary.metadata["acquisition_detail_deferred"] = reason
    coverage.add(summary)
    if reason == "PREVIEW":
        coverage.warn("preview_details_deferred_until_persist")
    return True


@dataclass
class OffsetPages:
    """Numeric pagination accounting, independent of record completeness."""

    config: ProviderRuntimeConfig
    offset: int = 0
    total: int | None = None
    exhausted: bool = False

    def advance(
        self, rows: list, total_value: object, coverage: Coverage, page: int
    ) -> bool:
        total = count(total_value)
        if total is None:
            coverage.warn("missing_or_invalid_total")
        elif self.total is not None and total != self.total:
            coverage.warn("total_changed_between_pages")
            return False
        else:
            self.total = total
        if len(rows) > self.config.page_size:
            coverage.warn("unexpected_page_size")
        self.offset += len(rows)
        if self.total is not None and self.offset >= self.total:
            self.exhausted = self.offset == self.total
            if not self.exhausted:
                coverage.warn("total_count_mismatch")
            return False
        if len(rows) < self.config.page_size:
            if self.total is None:
                self.exhausted = True
            else:
                coverage.warn("premature_pagination_exhaustion")
            return False
        if "duplicate_or_overlapping_page_detected" in coverage.warnings:
            return False
        if page == self.config.max_pages:
            coverage.warn("pagination_max_pages_reached")
            return False
        return True
