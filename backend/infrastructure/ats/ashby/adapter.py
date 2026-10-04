"""Documented public Ashby REST board, never hosted GraphQL fallback."""

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
from backend.infrastructure.ats.posting import posting_identity, text_value


class AshbyRuntimeConfig(ProviderRuntimeConfig):
    pass


class AshbyAdapter:
    ats_type = "ashby"

    def __init__(self, http_client: SafeHttpClient):
        self.client = http_client

    async def crawl(self, source):
        config = runtime_config(source, AshbyRuntimeConfig, self.ats_type)
        requests = AcquisitionRequests(self.client, config.delay_seconds)
        coverage = Coverage(source)
        root = await requests.json(
            f"https://api.ashbyhq.com/posting-api/job-board/{config.board}",
            params={"includeCompensation": "true"},
        )
        base = f"https://jobs.ashbyhq.com/{config.board}/"
        for item in require_list(root, "jobs"):
            if not isinstance(item, dict):
                coverage.add(None)
                continue
            url = bound_url(item.get("jobUrl"), base, prefix=f"/{config.board}/")
            identity = posting_identity(item.get("id")) or path_identity(
                url, base, f"/{config.board}/"
            )
            compensation = mapping(item.get("compensation"))
            coverage.add(
                project(
                    source,
                    item,
                    identity=identity,
                    url=url,
                    title=item.get("title"),
                    description=item.get("descriptionHtml"),
                    plain=item.get("descriptionPlain"),
                    location=item.get("location"),
                    employment_type=employment(item.get("employmentType")),
                    work_mode=work_mode(
                        item.get("workplaceType"), item.get("isRemote")
                    ),
                    published_at=exact_date(item.get("publishedAt")),
                    salary=text_value(
                        compensation.get("scrapeableCompensationSalarySummary")
                    ),
                    provider={
                        **item,
                        "identity_origin": "id"
                        if posting_identity(item.get("id"))
                        else "jobUrl_posting_path",
                    },
                )
            )
        if root.get("apiVersion", "1") != "1" or any(
            root.get(k) for k in ("next", "next_url", "hasMore")
        ):
            coverage.warn("unrecognized_ashby_list_version_or_continuation")
        return coverage.result(True, requests, contract="ashby_public_v1_full_list")
