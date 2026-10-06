"""Public Careers Site offers; unknown coverage is explicitly PARTIAL."""

from datetime import UTC, datetime

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    bound_url,
    employment,
    exact_date,
    project,
    require_list,
    runtime_config,
    work_mode,
)


def offer_employment(item):
    value = item.get("employment_type_code") or item.get("employment_type")
    # Observed Careers Site code specifies both schedule and tenure.
    return "Full-time" if value == "fulltime_permanent" else employment(value)


def offer_work_mode(item):
    structured = work_mode(item.get("workplace_type"))
    if structured:
        return structured
    modes = [
        label
        for key, label in (
            ("remote", "Remote"),
            ("hybrid", "Hybrid"),
            ("on_site", "On-site"),
        )
        if item.get(key) is True
    ]
    return modes[0] if len(modes) == 1 else None


def offer_publication(value):
    parsed = exact_date(value)
    if parsed is not None:
        return parsed
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
        except ValueError:
            pass
    return None


class RecruiteeRuntimeConfig(ProviderRuntimeConfig):
    pass


class RecruiteeAdapter:
    ats_type = "recruitee"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, RecruiteeRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        base = f"https://{config.host}"
        root = await requests.json(f"{base}/api/offers/")
        for item in require_list(root, "offers"):
            if not isinstance(item, dict):
                coverage.add(None)
                continue
            description = item.get("description")
            requirements = item.get("requirements")
            if isinstance(description, str) and isinstance(requirements, str):
                description += "\n" + requirements
            coverage.add(
                project(
                    source,
                    item,
                    identity=item.get("id"),
                    url=bound_url(item.get("careers_url"), base),
                    title=item.get("title"),
                    description=description,
                    country_code=item.get("country_code"),
                    location=", ".join(
                        v
                        for v in (item.get("city"), item.get("country"))
                        if isinstance(v, str) and v
                    ),
                    employment_type=offer_employment(item),
                    work_mode=offer_work_mode(item),
                    published_at=offer_publication(item.get("published_at")),
                    provider=item,
                )
            )
        coverage.warn("recruitee_offers_coverage_and_future_auth_contract_unverified")
        if any(root.get(k) for k in ("next", "next_url", "hasMore")):
            coverage.warn("unsupported_offers_continuation")
        return coverage.result(False, requests, reported_total=root.get("total"))
