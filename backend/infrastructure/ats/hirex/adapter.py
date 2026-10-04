"""Public Hirex board JSON-LD, always non-authoritative for absence closure."""

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    bound_url,
    employment,
    exact_date,
    path_identity,
    project,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.structured_html import (
    job_postings,
    structured_identifier,
    structured_location,
)


class HirexRuntimeConfig(ProviderRuntimeConfig):
    pass


class HirexAdapter:
    ats_type = "hirex"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, HirexRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        base = f"https://app.gethirex.com/o/{config.board}/"
        response = await requests.response(base)
        postings, malformed = job_postings(response.text)
        if malformed:
            coverage.warn("malformed_json_ld_block")
        for item in postings:
            url = bound_url(item.get("url"), base, prefix=f"/o/{config.board}/")
            identity = structured_identifier(item) or path_identity(
                url, base, f"/o/{config.board}/"
            )
            coverage.add(
                project(
                    source,
                    item,
                    identity=identity,
                    url=url,
                    title=item.get("title"),
                    description=item.get("description"),
                    location=structured_location(item),
                    responsibilities=item.get("responsibilities"),
                    employment_type=employment(item.get("employmentType")),
                    work_mode=work_mode(item.get("jobLocationType")),
                    published_at=exact_date(item.get("datePosted")),
                    provider=item,
                )
            )
        coverage.warn("html_json_ld_board_coverage_unverified")
        return coverage.result(False, requests)
