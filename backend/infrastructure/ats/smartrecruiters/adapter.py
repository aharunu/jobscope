"""Public SmartRecruiters Posting API with offset/total reconciliation."""

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
    mapping,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity, text_value


class SmartRecruitersRuntimeConfig(ProviderRuntimeConfig):
    pass


class SmartRecruitersAdapter:
    ats_type = "smartrecruiters"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, SmartRecruitersRuntimeConfig, self.ats_type)
        requests, coverage, pages = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
            OffsetPages(config),
        )
        endpoint = (
            f"https://api.smartrecruiters.com/v1/companies/{config.board}/postings"
        )
        for page in range(1, config.max_pages + 1):
            root = await requests.json(
                endpoint, params={"limit": config.page_size, "offset": pages.offset}
            )
            rows = require_list(root, "content")
            if root.get("offset", pages.offset) != pages.offset:
                coverage.warn("response_offset_mismatch")
            for item in rows:
                if not isinstance(item, dict) or not (
                    identity := posting_identity(item.get("id"))
                ):
                    coverage.add(None)
                    continue
                detail = None
                info = item
                sections = mapping(mapping(item.get("jobAd")).get("sections"))
                if not sections:
                    detail = await requests.json(f"{endpoint}/{identity}")
                    if posting_identity(detail.get("id")) != identity:
                        coverage.add(None)
                        coverage.warn("detail_identity_mismatch")
                        continue
                    info, sections = (
                        detail,
                        mapping(mapping(detail.get("jobAd")).get("sections")),
                    )
                description = "\n".join(
                    v
                    for entry in sections.values()
                    if (v := text_value(mapping(entry).get("text")))
                )
                if not description:
                    coverage.add(None)
                    coverage.warn("required_detail_description_missing")
                    continue
                url = bound_url(
                    info.get("jobAdUrl")
                    or info.get("applyUrl")
                    or item.get("jobAdUrl")
                    or item.get("applyUrl"),
                    "https://jobs.smartrecruiters.com",
                    prefix=f"/{config.board}/",
                )
                if not url:
                    url = bound_url(
                        info.get("jobAdUrl")
                        or info.get("applyUrl")
                        or item.get("jobAdUrl")
                        or item.get("applyUrl"),
                        "https://www.smartrecruiters.com",
                        prefix=f"/{config.board}/",
                    )
                coverage.add(
                    project(
                        source,
                        {"version": 1, "list": item, "detail": detail}
                        if detail
                        else item,
                        identity=identity,
                        url=url,
                        title=info.get("name") or item.get("name"),
                        description=description,
                        responsibilities=mapping(sections.get("jobDescription")).get(
                            "text"
                        ),
                        location=location(info.get("location"))
                        or location(item.get("location")),
                        country_code=mapping(
                            info.get("location") or item.get("location")
                        ).get("country"),
                        employment_type=employment(
                            mapping(info.get("typeOfEmployment")).get("label")
                            or mapping(item.get("typeOfEmployment")).get("label")
                        ),
                        work_mode=work_mode(
                            None,
                            mapping(info.get("location") or item.get("location")).get(
                                "remote"
                            ),
                        ),
                        published_at=exact_date(
                            info.get("releasedDate") or item.get("releasedDate")
                        ),
                        provider={"list": item, "detail": detail},
                    )
                )
            if not pages.advance(rows, root.get("totalFound"), coverage, page):
                break
        return coverage.result(
            pages.exhausted and pages.total is not None, requests, total=pages.total
        )
