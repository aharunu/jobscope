"""Validated runtime views of existing Lever/Greenhouse Source JSON maps."""

from __future__ import annotations

import re
from typing import Annotated, Literal, NoReturn
from urllib.parse import SplitResult, parse_qs, unquote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.application.job_discovery.exceptions import InvalidSourceConfigurationError

LEVER_BASES = {
    "global": "https://api.lever.co/v0/postings",
    "eu": "https://api.eu.lever.co/v0/postings",
}
GREENHOUSE_BASE = "https://boards-api.greenhouse.io/v1/boards"
LEVER_HOSTS = {
    "lever.co",
    "jobs.lever.co",
    "api.lever.co",
    "jobs.eu.lever.co",
    "api.eu.lever.co",
}
GREENHOUSE_HOSTS = {
    "greenhouse.io",
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "boards-api.greenhouse.io",
    "boards.eu.greenhouse.io",
    "job-boards.eu.greenhouse.io",
}
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,254}\Z")


def _invalid(source: RuntimeSourceDTO, message: str) -> InvalidSourceConfigurationError:
    return InvalidSourceConfigurationError(
        message, details={"source_id": str(source.id)}
    )


def _source_url(source: RuntimeSourceDTO) -> SplitResult:
    if not source.url:
        raise _invalid(source, "Source has no URL configured.")
    try:
        parsed = urlsplit(source.url)
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and parsed.username is None
            and parsed.password is None
            and parsed.port in {None, 80, 443}
        )
    except ValueError as exc:
        raise _invalid(source, "Invalid Source URL.") from exc
    if not valid:
        raise _invalid(source, "Invalid Source URL: use HTTP(S) without credentials.")
    return parsed


def extract_token(source: RuntimeSourceDTO, provider: str) -> str:
    """Resolve a safe path component; retain explicit token override compatibility."""
    keys = ("site_token", "board_token", "token", "company_slug")
    if provider == "greenhouse":
        keys = ("board_token", "site_token", "token", "company_slug")
    for key in keys:
        if key in source.adapter_config:
            value = source.adapter_config[key]
            if isinstance(value, str) and TOKEN_PATTERN.fullmatch(value.strip()):
                return value.strip()
            raise _invalid(source, f"Invalid {provider} token in adapter_config.{key}.")

    parsed = _source_url(source)
    hosts = LEVER_HOSTS if provider == "lever" else GREENHOUSE_HOSTS
    if parsed.hostname not in hosts:
        raise _invalid(source, f"Source URL does not belong to {provider.title()}.")
    parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
    candidate = None
    if provider == "lever":
        if parsed.hostname in {"api.lever.co", "api.eu.lever.co"}:
            if len(parts) >= 3 and parts[:2] == ["v0", "postings"]:
                candidate = parts[2]
        elif parts:
            candidate = parts[0]
    else:
        query_token = parse_qs(parsed.query).get("for")
        if query_token:
            candidate = query_token[0]
        elif parsed.hostname == "boards-api.greenhouse.io":
            if len(parts) >= 3 and parts[:2] == ["v1", "boards"]:
                candidate = parts[2]
        elif parts:
            candidate = parts[1] if parts[0] == "embed" and len(parts) > 1 else parts[0]
    if isinstance(candidate, str) and TOKEN_PATTERN.fullmatch(candidate):
        return candidate
    label = "Lever site token" if provider == "lever" else "Greenhouse board token"
    raise _invalid(source, f"Cannot resolve {label} from Source URL.")


class _RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    delay_seconds: Annotated[
        float, Field(strict=True, ge=0, le=60, allow_inf_nan=False)
    ]


class LeverRuntimeConfig(_RuntimeConfig):
    site_token: str
    region: Literal["global", "eu"]
    base_url: str
    page_size: Annotated[StrictInt, Field(ge=1, le=1000)] = 100
    max_pages: Annotated[StrictInt, Field(ge=1, le=1000)] = 10
    pagination_mode: Literal["offset"] = "offset"


class GreenhouseRuntimeConfig(_RuntimeConfig):
    board_token: str
    base_url: str


def _delay(source: RuntimeSourceDTO) -> object:
    # Explicit zero wins over the alternative key; no truthiness-based override.
    config = source.rate_limit_config
    return config.get("delay_seconds", config.get("request_delay_seconds", 0.0))


def _base(source: RuntimeSourceDTO, default: str, allowed: set[str]) -> str:
    value = source.endpoint_config.get("base_url", default)
    if not isinstance(value, str) or value.rstrip("/") not in allowed:
        raise _invalid(
            source, "endpoint_config.base_url must be a supported provider API base."
        )
    return value.rstrip("/")


def _validation_error(source: RuntimeSourceDTO, exc: ValidationError) -> NoReturn:
    # Pydantic's normal error rendering includes input values; expose field names only.
    fields = ", ".join(str(e["loc"][0]) for e in exc.errors())
    raise _invalid(
        source, f"Invalid acquisition configuration fields: {fields}."
    ) from exc


def lever_runtime_config(
    source: RuntimeSourceDTO, default_base: str
) -> LeverRuntimeConfig:
    token = extract_token(source, "lever")
    parsed = _source_url(source)
    url_region = None
    if parsed.hostname in LEVER_HOSTS:
        url_region = "eu" if ".eu.lever.co" in parsed.hostname else "global"
    region = source.adapter_config.get("region")
    if region is not None and (
        not isinstance(region, str) or region not in LEVER_BASES
    ):
        raise _invalid(source, "Lever region must be 'global' or 'eu'.")
    inferred_base = default_base
    if region:
        inferred_base = LEVER_BASES[region]
    elif url_region == "eu" and default_base == LEVER_BASES["global"]:
        inferred_base = LEVER_BASES["eu"]
    base = _base(source, inferred_base, set(LEVER_BASES.values()))
    base_region = next(key for key, value in LEVER_BASES.items() if value == base)
    if (region and region != base_region) or (url_region and url_region != base_region):
        raise _invalid(source, "Lever Source URL, region and API base must agree.")
    if source.pagination_config.get("pagination_mode", "offset") != "offset":
        raise _invalid(
            source,
            "Lever pagination_mode must be 'offset'; "
            "remove legacy 'cursor' or set 'offset'.",
        )
    try:
        return LeverRuntimeConfig(
            site_token=token,
            region=base_region,
            base_url=base,
            page_size=source.pagination_config.get("page_size", 100),
            max_pages=source.pagination_config.get("max_pages", 10),
            delay_seconds=_delay(source),
        )
    except ValidationError as exc:
        _validation_error(source, exc)


def greenhouse_runtime_config(
    source: RuntimeSourceDTO, default_base: str
) -> GreenhouseRuntimeConfig:
    token = extract_token(source, "greenhouse")
    _source_url(source)
    base = _base(source, default_base, {GREENHOUSE_BASE})
    # Existing pagination JSON is intentionally retained but never interpreted.
    try:
        return GreenhouseRuntimeConfig(
            board_token=token, base_url=base, delay_seconds=_delay(source)
        )
    except ValidationError as exc:
        _validation_error(source, exc)
