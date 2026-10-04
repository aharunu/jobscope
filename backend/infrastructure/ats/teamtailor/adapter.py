"""Teamtailor hosted JSON feed; continuation does not prove board coverage."""

from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.acquisition import (
    AcquisitionRequests,
    Coverage,
    ProviderRuntimeConfig,
    bound_url,
    employment,
    exact_date,
    mapping,
    path_identity,
    project,
    require_list,
    runtime_config,
    work_mode,
)
from backend.infrastructure.ats.posting import posting_identity
from backend.infrastructure.ats.structured_html import (
    structured_identifier,
    structured_location,
)


class TeamtailorRuntimeConfig(ProviderRuntimeConfig):
    pass


class TeamtailorAdapter:
    ats_type = "teamtailor"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, TeamtailorRuntimeConfig, self.ats_type)
        requests, coverage = (
            AcquisitionRequests(self.client, config.delay_seconds),
            Coverage(source),
        )
        base = f"https://{config.host}"
        endpoint, visited = f"{base}/jobs.json", set()
        for page in range(1, config.max_pages + 1):
            if endpoint in visited:
                coverage.warn("repeated_continuation_url")
                break
            visited.add(endpoint)
            root = await requests.json(endpoint)
            for item in require_list(root, "items"):
                if not isinstance(item, dict):
                    coverage.add(None)
                    continue
                posting = mapping(item.get("_jobposting"))
                url = bound_url(item.get("url"), base, prefix="/jobs/")
                identity = (
                    posting_identity(item.get("id"))
                    or posting_identity(structured_identifier(posting))
                    or path_identity(url, base, "/jobs/")
                )
                coverage.add(
                    project(
                        source,
                        item,
                        identity=identity,
                        url=url,
                        title=item.get("title"),
                        description=item.get("content_html")
                        or posting.get("description"),
                        plain=item.get("content_text"),
                        location=structured_location(posting),
                        responsibilities=posting.get("responsibilities"),
                        employment_type=employment(posting.get("employmentType")),
                        work_mode=work_mode(posting.get("jobLocationType")),
                        published_at=exact_date(item.get("date_published")),
                        provider=item,
                    )
                )
            next_value = (
                root.get("next_url")
                or root.get("next")
                or mapping(root.get("links")).get("next")
            )
            if not next_value:
                break
            endpoint = bound_url(next_value, base, prefix="/jobs.json")
            if not endpoint:
                coverage.warn("unsafe_or_unrecognized_continuation")
                break
            if "duplicate_or_overlapping_page_detected" in coverage.warnings:
                break
            if page == config.max_pages:
                coverage.warn("pagination_max_pages_reached")
        coverage.warn("hosted_json_feed_board_coverage_unverified")
        return coverage.result(False, requests)
