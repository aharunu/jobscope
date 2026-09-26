"""FastAPI dependencies for the Crawler & ATS Adapter subsystem."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.ports import (
    RuntimeSourceProvider,
    SafeHttpClient,
)
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.http.safe_client import HttpSafeClient
from backend.interfaces.api.dependencies.sources import get_source_registry_service


def get_safe_http_client(request: Request) -> SafeHttpClient:
    """Retrieve the managed SafeHttpClient from application state."""
    client = getattr(request.app.state, "http_safe_client", None)
    if client is None:
        # Fallback for isolated unit tests or non-lifespan contexts
        return HttpSafeClient()
    return client


SafeHttpClientDep = Annotated[SafeHttpClient, Depends(get_safe_http_client)]


def get_adapter_registry(
    request: Request,
    http_client: SafeHttpClientDep,
) -> ATSAdapterRegistry:
    """Retrieve the ATSAdapterRegistry from application state."""
    registry = getattr(request.app.state, "adapter_registry", None)
    if registry is None:
        return create_adapter_registry(http_client)
    return registry


ATSAdapterRegistryDep = Annotated[ATSAdapterRegistry, Depends(get_adapter_registry)]


def get_crawler_orchestrator(
    source_provider: Annotated[
        RuntimeSourceProvider, Depends(get_source_registry_service)
    ],
    adapter_registry: ATSAdapterRegistryDep,
) -> CrawlerOrchestrator:
    """Yield a CrawlerOrchestrator injected with runtime source provider
    and adapter registry.
    """
    return CrawlerOrchestrator(
        source_provider=source_provider,
        adapter_registry=adapter_registry,
    )


CrawlerOrchestratorDep = Annotated[
    CrawlerOrchestrator, Depends(get_crawler_orchestrator)
]

__all__ = [
    "ATSAdapterRegistryDep",
    "CrawlerOrchestratorDep",
    "SafeHttpClientDep",
    "get_adapter_registry",
    "get_crawler_orchestrator",
    "get_safe_http_client",
]
