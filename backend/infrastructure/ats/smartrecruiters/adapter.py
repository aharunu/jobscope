"""Public SmartRecruiters Posting API with offset/total reconciliation."""

from urllib.parse import unquote, urlsplit

from backend.application.job_discovery.detail_plan import acquisition_countries
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    OffsetPages,
    ProviderRuntimeConfig,
    bound_url,
    defer_detail,
    employment,
    exact_date,
    location,
    mapping,
    project,
    require_list,
    retain_partial,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity, text_value


def posting_url(value, board):
    """Provider board names are case-insensitive; posting paths are not."""
    for origin in (
        "https://jobs.smartrecruiters.com",
        "https://www.smartrecruiters.com",
    ):
        url = bound_url(value, origin)
        if url:
            parts = urlsplit(url).path.split("/")
            if (
                len(parts) >= 3
                and unquote(parts[1]).casefold() == board.casefold()
                and parts[2]
            ):
                return url
    return None


class SmartRecruitersRuntimeConfig(ProviderRuntimeConfig):
    pass


class SmartRecruitersAdapter:
    ats_type = "smartrecruiters"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, SmartRecruitersRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        countries = acquisition_countries()
        if countries:
            coverage.warn("provider_country_scoped_acquisition")
        retain_partial(coverage, requests)
        totals = []
        exhausted = True
        for country in countries or (None,):
            pages = await self._crawl_country(
                source, config, requests, coverage, country
            )
            exhausted = exhausted and pages.exhausted and pages.total is not None
            totals.append(pages.total)
        return coverage.result(
            exhausted,
            requests,
            total=sum(totals) if all(t is not None for t in totals) else None,
            country_scope=list(countries),
        )

    async def _crawl_country(self, source, config, requests, coverage, country):
        pages = OffsetPages(config)
        previous_countries = frozenset(coverage.seen)
        endpoint = (
            f"https://api.smartrecruiters.com/v1/companies/{config.board}/postings"
        )
        for page in range(1, config.max_pages + 1):
            params = {"limit": config.page_size, "offset": pages.offset}
            if country:
                params["country"] = country.lower()
            root = await requests.json(endpoint, params=params)
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
                if identity in previous_countries:
                    continue  # Same posting can legitimately match two country queries.
                info = item
                sections = mapping(mapping(item.get("jobAd")).get("sections"))
                if not sections:
                    summary_url = posting_url(
                        item.get("jobAdUrl") or item.get("applyUrl"),
                        config.board,
                    ) or bound_url(
                        item.get("ref"),
                        "https://api.smartrecruiters.com",
                        prefix=f"/v1/companies/{config.board}/postings/",
                    )
                    summary = project(
                        source,
                        item,
                        identity=identity,
                        url=summary_url,
                        title=item.get("name"),
                        location=location(item.get("location")),
                        country_code=mapping(item.get("location")).get("country"),
                        employment_type=employment(
                            mapping(item.get("typeOfEmployment")).get("label")
                        ),
                        published_at=exact_date(item.get("releasedDate")),
                        provider={"list": item, "detail": None},
                    )
                    if defer_detail(summary, coverage):
                        continue
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
                url = posting_url(
                    info.get("jobAdUrl")
                    or info.get("applyUrl")
                    or item.get("jobAdUrl")
                    or item.get("applyUrl"),
                    config.board,
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
        return pages
