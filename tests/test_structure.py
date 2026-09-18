"""Architecture and package structure verification tests."""

import importlib


def test_package_structure_imports() -> None:
    """Verify that all modular monolith packages import cleanly without side-effects."""
    packages = [
        "backend",
        # Domain Layer
        "backend.domain",
        "backend.domain.user",
        "backend.domain.profile",
        "backend.domain.search_profile",
        "backend.domain.job",
        "backend.domain.source",
        "backend.domain.application",
        "backend.domain.matching",
        # Application Layer
        "backend.application",
        "backend.application.job_discovery",
        "backend.application.job_processing",
        "backend.application.job_matching",
        "backend.application.profile_management",
        "backend.application.application_tracking",
        "backend.application.system",
        # Infrastructure Layer
        "backend.infrastructure",
        "backend.infrastructure.config",
        "backend.infrastructure.database",
        "backend.infrastructure.database.models",
        "backend.infrastructure.database.repositories",
        "backend.infrastructure.database.migrations",
        "backend.infrastructure.ats",
        "backend.infrastructure.ats.lever",
        "backend.infrastructure.ats.greenhouse",
        "backend.infrastructure.ats.workday",
        "backend.infrastructure.ats.ashby",
        "backend.infrastructure.parsers",
        "backend.infrastructure.llm",
        "backend.infrastructure.logging",
        # Interfaces Layer
        "backend.interfaces",
        "backend.interfaces.api",
        "backend.interfaces.api.routes",
    ]

    for pkg in packages:
        module = importlib.import_module(pkg)
        assert module is not None, f"Failed to import package: {pkg}"
