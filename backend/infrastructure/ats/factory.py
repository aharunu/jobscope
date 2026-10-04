"""Composition root factory for ATS adapters and registry."""

from __future__ import annotations

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.ports import SafeHttpClient
from backend.infrastructure.ats.ashby.adapter import AshbyAdapter
from backend.infrastructure.ats.bamboohr.adapter import BambooHRAdapter
from backend.infrastructure.ats.greenhouse import GreenhouseAdapter
from backend.infrastructure.ats.hirex.adapter import HirexAdapter
from backend.infrastructure.ats.lever import LeverAdapter
from backend.infrastructure.ats.oracle.adapter import OracleAdapter
from backend.infrastructure.ats.personio.adapter import PersonioAdapter
from backend.infrastructure.ats.recruitee.adapter import RecruiteeAdapter
from backend.infrastructure.ats.smartrecruiters.adapter import SmartRecruitersAdapter
from backend.infrastructure.ats.teamtailor.adapter import TeamtailorAdapter
from backend.infrastructure.ats.workable.adapter import WorkableAdapter
from backend.infrastructure.ats.workday.adapter import WorkdayAdapter


def create_adapter_registry(http_client: SafeHttpClient) -> ATSAdapterRegistry:
    """Instantiate and register all supported ATS adapters with the HTTP client.

    Args:
        http_client: SafeHttpClient instance to be shared across adapters.

    Returns:
        Populated ATSAdapterRegistry ready for orchestrator consumption.
    """
    lever_adapter = LeverAdapter(http_client=http_client)
    greenhouse_adapter = GreenhouseAdapter(http_client=http_client)
    return ATSAdapterRegistry(
        [
            lever_adapter,
            greenhouse_adapter,
            *[
                cls(http_client)
                for cls in (
                    AshbyAdapter,
                    WorkdayAdapter,
                    SmartRecruitersAdapter,
                    RecruiteeAdapter,
                    PersonioAdapter,
                    TeamtailorAdapter,
                    WorkableAdapter,
                    HirexAdapter,
                    BambooHRAdapter,
                    OracleAdapter,
                )
            ],
        ]
    )
