"""BambooHR public list plus minimum description from public posting JSON-LD."""

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    employment,
    exact_date,
    location,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity, text_value
from backend.infrastructure.ats.structured_html import (
    job_postings,
    structured_identifier,
    structured_location,
)


class BambooHRRuntimeConfig(ProviderRuntimeConfig):
    pass


class BambooHRAdapter:
    ats_type = "bamboohr"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, BambooHRRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        base = f"https://{config.host}"
        root = await requests.json(f"{base}/careers/list")
        for item in require_list(root, "result"):
            if not isinstance(item, dict) or not (
                identity := posting_identity(item.get("id"))
            ):
                coverage.add(None)
                continue
            url = f"{base}/careers/{identity}"
            description = item.get("jobDescription") or item.get("description")
            raw = item
            detail_posting = {}
            if not text_value(description):
                response = await requests.response(url)
                postings, malformed = job_postings(response.text)
                matching = [
                    p
                    for p in postings
                    if str(structured_identifier(p)) == identity or p.get("url") == url
                ]
                if len(matching) == 1 and not malformed:
                    detail_posting = matching[0]
                    description = matching[0].get("description")
                    raw = {"version": 1, "list": item, "detail_json_ld": matching[0]}
                else:
                    coverage.warn("public_detail_description_unavailable")
            coverage.add(
                project(
                    source,
                    raw,
                    identity=identity,
                    url=url,
                    title=item.get("jobOpeningName"),
                    description=description,
                    location=location(item.get("location"))
                    or structured_location(detail_posting),
                    employment_type=employment(
                        item.get("employmentStatus")
                        or item.get("employmentType")
                        or item.get("employmentStatusLabel")
                        or detail_posting.get("employmentType")
                    ),
                    work_mode=work_mode(
                        detail_posting.get("jobLocationType"), item.get("isRemote")
                    ),
                    published_at=exact_date(
                        item.get("datePosted") or detail_posting.get("datePosted")
                    ),
                    provider={"list": item, "detail": detail_posting},
                )
            )
        if any(root.get(k) for k in ("next", "next_url", "hasMore")):
            coverage.warn("unsupported_public_list_continuation")
        coverage.warn("bamboohr_public_careers_list_coverage_unverified")
        return coverage.result(False, requests, reported_total=root.get("total"))
