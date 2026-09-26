"""Composition root factory for ATS adapters and registry."""

from __future__ import annotations

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.lever import LeverAdapter


def create_adapter_registry(http_client: SafeHttpClient) -> ATSAdapterRegistry:
    """Instantiate and register all supported ATS adapters with the HTTP client.

    Args:
        http_client: SafeHttpClient instance to be shared across adapters.

    Returns:
        Populated ATSAdapterRegistry ready for orchestrator consumption.
    """
    lever_adapter = LeverAdapter(http_client=http_client)
    return ATSAdapterRegistry([lever_adapter])
