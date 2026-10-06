"""Workday CXS acquisition with board-resolved optional country facets."""

import re

from backend.application.job_discovery.detail_plan import acquisition_countries
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    OffsetPages,
    ProviderRuntimeConfig,
    bound_url,
    count,
    defer_detail,
    employment,
    exact_date,
    location,
    malformed,
    mapping,
    project,
    require_list,
    retain_partial,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity, text_value
from backend.infrastructure.ats.workday.country_facets import country_facets


class WorkdayRuntimeConfig(ProviderRuntimeConfig):
    pass


class WorkdayAdapter:
    ats_type = "workday"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(
            source, WorkdayRuntimeConfig, self.ats_type, page_size=20
        )
        requests, coverage, pages = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
            OffsetPages(config),
        )
        origin = f"https://{config.host}"
        cxs = f"{origin}/wday/cxs/{config.tenant}/{config.site}"
        retain_partial(coverage, requests)
        countries = acquisition_countries()
        facets = {}
        initial = None
        if countries:
            initial = await requests.json(
                f"{cxs}/jobs",
                body={
                    "limit": config.page_size,
                    "offset": 0,
                    "searchText": "",
                    "appliedFacets": {},
                },
            )
            require_list(initial, "jobPostings")
            resolved = country_facets(initial, countries)
            if resolved is not None:
                coverage.warn("provider_country_scoped_acquisition")
                if not resolved:
                    return coverage.result(
                        False, requests, country_scope=list(countries), filtered_total=0
                    )
                facets, initial = resolved, None
            else:
                coverage.warn("provider_country_filter_unavailable_unfiltered_fallback")
        for page in range(1, config.max_pages + 1):
            root = (
                initial
                if initial is not None
                else await requests.json(
                    f"{cxs}/jobs",
                    body={
                        "limit": config.page_size,
                        "offset": pages.offset,
                        "searchText": "",
                        "appliedFacets": facets,
                    },
                )
            )
            initial = None
            rows = require_list(root, "jobPostings")
            for item in rows:
                if not isinstance(item, dict):
                    coverage.add(None)
                    continue
                path = text_value(item.get("externalPath"))
                # externalPath identifies a posting independently of requisition ID.
                if (
                    not path
                    or not re.fullmatch(r"/job/[A-Za-z0-9_/%.-]+", path)
                    or not bound_url(path, origin, prefix="/job/")
                ):
                    coverage.add(None)
                    continue
                identity = posting_identity(path.rstrip("/").split("/")[-1])
                if identity is None:
                    coverage.add(None)
                    continue
                detail = None
                info = item
                if not text_value(item.get("jobDescription")):
                    summary = project(
                        source,
                        {"version": 1, "list": item, "detail": None},
                        identity=identity,
                        url=f"{origin}/{config.locale}/{config.site}{path}",
                        title=item.get("title"),
                        location=item.get("locationsText"),
                        provider={"list": item, "detail": None},
                    )
                    if defer_detail(summary, coverage):
                        continue
                    detail = await requests.json(f"{cxs}{path}")
                    info = mapping(detail.get("jobPostingInfo"))
                description = info.get("jobDescription")
                if not text_value(description):
                    raise malformed("Workday required detail lacks a full description.")
                coverage.add(
                    project(
                        source,
                        {"version": 1, "list": item, "detail": detail},
                        identity=identity,
                        url=f"{origin}/{config.locale}/{config.site}{path}",
                        title=info.get("title") or item.get("title"),
                        description=description,
                        location=location(info.get("location"))
                        or item.get("locationsText"),
                        employment_type=employment(
                            info.get("timeType") or item.get("timeType")
                        ),
                        work_mode=work_mode(
                            info.get("workplaceType") or item.get("workplaceType")
                        ),
                        published_at=exact_date(
                            info.get("postedOn") or item.get("postedOn")
                        ),
                        provider={
                            "list": item,
                            "detail": detail,
                            "tenant": config.tenant,
                            "site": config.site,
                            "locale": config.locale,
                            "identity_origin": "externalPath_posting_reference",
                        },
                    )
                )
            # CXS boards can return total=0 on noninitial pages that still
            # contain jobs. Keep the initial count and prove exhaustion from
            # rows; a nonzero changed total remains a coverage defect.
            total = root.get("total")
            if pages.offset and count(total) == 0 and pages.total is not None:
                total = pages.total
            if not pages.advance(rows, total, coverage, page):
                break
        # Hosted CXS has no published universal contract/snapshot guarantee.
        coverage.warn("workday_hosted_cxs_coverage_requires_live_contract_verification")
        return coverage.result(
            False,
            requests,
            total=pages.total,
            list_exhausted=pages.exhausted,
            country_scope=list(countries) if facets else [],
        )
