"""Unfiltered Workday CXS search with conditional required description detail."""

import re

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    OffsetPages,
    ProviderRuntimeConfig,
    bound_url,
    employment,
    exact_date,
    location,
    malformed,
    mapping,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import text_value


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
        for page in range(1, config.max_pages + 1):
            root = await requests.json(
                f"{cxs}/jobs",
                body={
                    "limit": config.page_size,
                    "offset": pages.offset,
                    "searchText": "",
                    "appliedFacets": {},
                },
            )
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
                identity = path.rstrip("/").split("/")[-1]
                detail = None
                info = item
                if not text_value(item.get("jobDescription")):
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
            if not pages.advance(rows, root.get("total"), coverage, page):
                break
        # Hosted CXS has no published universal contract/snapshot guarantee.
        coverage.warn("workday_hosted_cxs_coverage_requires_live_contract_verification")
        return coverage.result(
            False, requests, total=pages.total, list_exhausted=pages.exhausted
        )
