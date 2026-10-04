"""Published widget details, conservative account-dependent coverage."""

from urllib.parse import urlsplit

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    bound_url,
    employment,
    exact_date,
    location,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity


def posting_url(item, base, board):
    """Accept public shortcode links only when they match this widget's record."""
    for value in (item.get("url"), item.get("shortlink")):
        url = bound_url(value, base, prefix=f"/{board}/")
        if url:
            return url
        shortcode = posting_identity(item.get("shortcode"))
        url = bound_url(value, base, prefix="/j/")
        if shortcode and url and urlsplit(url).path.rstrip("/") == f"/j/{shortcode}":
            return url
    return None


class WorkableRuntimeConfig(ProviderRuntimeConfig):
    pass


class WorkableAdapter:
    ats_type = "workable"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, WorkableRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        base = "https://apply.workable.com"
        root = await requests.json(
            f"{base}/api/v1/widget/accounts/{config.board}", params={"details": "true"}
        )
        for item in require_list(root, "jobs"):
            if not isinstance(item, dict):
                coverage.add(None)
                continue
            description, requirements = (
                item.get("description"),
                item.get("requirements"),
            )
            if isinstance(description, str) and isinstance(requirements, str):
                description += "\n" + requirements
            coverage.add(
                project(
                    source,
                    item,
                    identity=item.get("id") or item.get("shortcode"),
                    url=posting_url(item, base, config.board),
                    title=item.get("title"),
                    description=description,
                    location=location(item.get("location"))
                    or ", ".join(
                        v
                        for v in (item.get("city"), item.get("country"))
                        if isinstance(v, str) and v
                    ),
                    employment_type=employment(
                        item.get("employment_type") or item.get("type")
                    ),
                    work_mode=work_mode(
                        item.get("workplace_type"), item.get("telecommuting")
                    ),
                    published_at=exact_date(item.get("published_on")),
                    provider=item,
                )
            )
        if any(root.get(k) for k in ("next", "next_url", "hasMore")):
            coverage.warn("unsupported_widget_continuation")
        coverage.warn("workable_widget_account_coverage_unverified")
        return coverage.result(False, requests, reported_total=root.get("total"))
