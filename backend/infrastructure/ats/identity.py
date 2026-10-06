"""Narrow provider namespace proof for duplicate catalog board aliases."""

from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.application.job_discovery.exceptions import InvalidSourceConfigurationError
from backend.infrastructure.ats.acquisition import ProviderRuntimeConfig, runtime_config
from backend.infrastructure.ats.runtime_config import LEVER_BASES, lever_runtime_config


def provider_namespace(source) -> tuple | None:
    runtime = RuntimeSourceDTO.from_domain(source.to_domain())
    try:
        if runtime.ats_type == "lever":
            config = lever_runtime_config(runtime, LEVER_BASES["global"])
            return ("lever", config.base_url, config.site_token)
        if runtime.ats_type in {"workday", "smartrecruiters"}:
            config = runtime_config(runtime, ProviderRuntimeConfig, runtime.ats_type)
            if runtime.ats_type == "workday":
                return ("workday", config.host, config.tenant, config.site)
            return ("smartrecruiters", config.board.casefold())
    except InvalidSourceConfigurationError:
        return None
    return None
