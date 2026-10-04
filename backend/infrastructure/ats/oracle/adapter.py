"""Oracle hosted Candidate Experience finder, board-wide and bounded."""

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    OffsetPages,
    ProviderRuntimeConfig,
    employment,
    exact_date,
    malformed,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity


class OracleRuntimeConfig(ProviderRuntimeConfig):
    pass


class OracleAdapter:
    ats_type = "oracle"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, OracleRuntimeConfig, self.ats_type)
        requests, coverage, pages = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
            OffsetPages(config),
        )
        base = f"https://{config.host}"
        endpoint = f"{base}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        for page in range(1, config.max_pages + 1):
            root = await requests.json(
                endpoint,
                params={
                    "onlyData": "true",
                    "expand": "requisitionList",
                    "finder": (
                        f"findReqs;siteNumber={config.site},limit={config.page_size},"
                        f"offset={pages.offset},sortBy=POSTING_DATES_DESC"
                    ),
                },
            )
            wrappers = require_list(root, "items")
            if len(wrappers) != 1 or not isinstance(wrappers[0], dict):
                raise malformed("Unexpected Oracle requisition wrapper.")
            wrapper = wrappers[0]
            rows = require_list(wrapper, "requisitionList")
            for item in rows:
                if not isinstance(item, dict):
                    coverage.add(None)
                    continue
                identity = posting_identity(item.get("Id"))
                description = item.get("ExternalDescriptionStr") or item.get(
                    "DescriptionStr"
                )
                if not description:
                    coverage.warn("oracle_full_description_unavailable")
                coverage.add(
                    project(
                        source,
                        item,
                        identity=identity,
                        url=f"{base}/hcmUI/CandidateExperience/{config.locale}/sites/{config.site}/job/{identity}"
                        if identity
                        else None,
                        title=item.get("Title"),
                        description=description,
                        plain=item.get("ShortDescriptionStr"),
                        description_available=bool(description),
                        location=item.get("PrimaryLocation"),
                        employment_type=employment(
                            item.get("EmploymentType") or item.get("JobSchedule")
                        ),
                        work_mode=work_mode(item.get("WorkplaceTypeCode"))
                        or work_mode(item.get("WorkplaceType")),
                        published_at=exact_date(item.get("PostedDate")),
                        provider=item,
                    )
                )
            if not pages.advance(rows, wrapper.get("TotalJobsCount"), coverage, page):
                break
        coverage.warn("oracle_internal_ce_contract_requires_live_verification")
        return coverage.result(
            False, requests, total=pages.total, list_exhausted=pages.exhausted
        )
