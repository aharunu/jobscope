"""Host-bound acquisition identifiers; catalog detection never performs I/O."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlsplit

from backend.application.job_discovery.exceptions import InvalidSourceConfigurationError
from backend.infrastructure.ats.runtime_config import TOKEN_PATTERN

NEW_PROVIDERS = (
    "ashby",
    "workday",
    "smartrecruiters",
    "recruitee",
    "personio",
    "teamtailor",
    "workable",
    "hirex",
    "bamboohr",
    "oracle",
)
LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"


def invalid(message: str = "Source URL/config does not identify a supported board."):
    return InvalidSourceConfigurationError(message)


def safe_url(value: str):
    try:
        p = urlsplit(value)
        if (
            p.scheme not in {"http", "https"}
            or not p.hostname
            or p.username is not None
            or p.password is not None
            or p.port not in {None, 80, 443}
            or p.fragment
            or any(unquote(s) in {".", ".."} for s in p.path.split("/"))
            or "\\" in unquote(p.path)
        ):
            raise invalid()
        return p
    except (ValueError, TypeError) as exc:
        raise invalid() from exc


def token(value: object) -> str:
    if not isinstance(value, str) or not TOKEN_PATTERN.fullmatch(value):
        raise invalid("Board identifiers must be nonempty bounded path components.")
    return value


def source_binding(
    url: str, provider: str, explicit: dict | None = None
) -> dict[str, str]:
    """Only observed provider host/path relationships qualify; no domain fallback."""
    p = safe_url(url)
    host = p.hostname or ""
    parts = [unquote(v) for v in p.path.strip("/").split("/") if v]
    result: dict[str, str] = {"host": host}
    board = None
    if provider == "ashby":
        if host == "jobs.ashbyhq.com" and len(parts) == 1:
            board = parts[0]
        elif (
            host == "api.ashbyhq.com"
            and len(parts) == 3
            and parts[:2] == ["posting-api", "job-board"]
        ):
            board = parts[2]
    elif provider == "smartrecruiters":
        if (
            host in {"careers.smartrecruiters.com", "jobs.smartrecruiters.com"}
            and len(parts) == 1
        ):
            board = parts[0]
        elif (
            host == "api.smartrecruiters.com"
            and len(parts) == 4
            and parts[:2] == ["v1", "companies"]
            and parts[3] == "postings"
        ):
            board = parts[2]
    elif provider in {"recruitee", "personio", "teamtailor", "bamboohr"}:
        suffix = {
            "recruitee": r"recruitee\.com",
            "personio": r"jobs\.personio\.(?:com|de)",
            "teamtailor": r"(?:na\.|au\.)?teamtailor\.com",
            "bamboohr": r"bamboohr\.com",
        }[provider]
        match = re.fullmatch(rf"({LABEL})\.{suffix}", host)
        if match:
            allowed = {
                "recruitee": [[], ["api", "offers"]],
                "personio": [[], ["xml"]],
                "teamtailor": [[], ["jobs"], ["jobs.json"]],
                "bamboohr": [[], ["jobs"], ["careers"], ["careers", "list"]],
            }[provider]
            if parts in allowed:
                board = match[1]
    elif provider == "workable":
        if host == "apply.workable.com":
            if len(parts) == 1:
                board = parts[0]
            elif len(parts) == 5 and parts[:4] == ["api", "v1", "widget", "accounts"]:
                board = parts[4]
    elif provider == "hirex":
        if host == "app.gethirex.com" and len(parts) == 2 and parts[0] == "o":
            board = parts[1]
    elif provider == "workday":
        match = re.fullmatch(rf"({LABEL})\.(wd\d+)\.myworkdayjobs\.com", host)
        if match:
            tenant, locale = match[1], None
            if len(parts) == 5 and parts[:2] == ["wday", "cxs"] and parts[4] == "jobs":
                tenant, site = parts[2:4]
            else:
                if parts and re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]):
                    locale, parts = parts[0], parts[1:]
                if not parts and explicit and explicit.get("site"):
                    parts = [token(explicit["site"])]
                if len(parts) != 1:
                    raise invalid(
                        "Workday requires an unambiguous site or CXS board URL."
                    )
                site = parts[0]
                if re.fullmatch(r"[a-zA-Z]{2}-[a-zA-Z]{2}", site):
                    raise invalid("Workday locale alone does not identify a site.")
            binding = {
                "host": host,
                "tenant": token(tenant),
                "site": token(site),
            }
            if locale is not None:
                binding["locale"] = locale
            return binding
    elif provider == "oracle" and re.fullmatch(
        rf"{LABEL}\.fa\.(?:(?:(?:em|us|uk|ap)\d+|ocs)\.)?oraclecloud\.(?:com|eu)", host
    ):
        # /hcmUI/CandidateExperience/{locale}/sites/{site}[/jobs]
        if (
            len(parts) in {5, 6}
            and parts[:2] == ["hcmUI", "CandidateExperience"]
            and parts[3] == "sites"
            and (len(parts) == 5 or parts[5] == "jobs")
        ):
            locale = parts[2]
            if not re.fullmatch(r"[a-z]{2}(?:-[A-Z]{2})?", locale):
                raise invalid("Invalid Oracle locale.")
            return {"host": host, "site": token(parts[4]), "locale": locale}
        # Explicit config can complete a recognized /hcmUI root.
        if parts == ["hcmUI"]:
            return result
    if board is None:
        raise invalid()
    result["board"] = token(board)
    return result
