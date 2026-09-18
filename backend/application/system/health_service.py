"""Health and system status application service.

Keeps system status checks decoupled from the API transport layer.
"""

from collections.abc import Awaitable, Callable
from typing import Any


class HealthService:
    """Provides application health and operational status information."""

    def __init__(self, app_name: str, app_version: str, environment: str) -> None:
        self.app_name = app_name
        self.app_version = app_version
        self.environment = environment

    def get_health_status(self) -> dict[str, Any]:
        """Return the basic liveness health status of the application."""
        return {
            "status": "healthy",
            "app": self.app_name,
            "environment": self.environment,
            "version": self.app_version,
        }

    async def get_database_readiness(
        self,
        checker_fn: Callable[[], Awaitable[dict[str, Any]]],
    ) -> tuple[bool, dict[str, Any]]:
        """Evaluate database connectivity readiness using the provided checker.

        Returns a tuple of (is_ready, sanitized_payload) avoiding credential leakage.
        """
        result = await checker_fn()
        is_ready = result.get("status") == "healthy"

        payload = {
            "status": "ready" if is_ready else "not_ready",
            "database": "connected" if is_ready else "disconnected",
        }
        return is_ready, payload
