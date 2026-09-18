"""Health and system status application service.

Keeps system status checks decoupled from the API transport layer.
"""

from typing import Any


class HealthService:
    """Provides application health and operational status information."""

    def __init__(self, app_name: str, app_version: str, environment: str) -> None:
        self.app_name = app_name
        self.app_version = app_version
        self.environment = environment

    def get_health_status(self) -> dict[str, Any]:
        """Return the basic health status of the application."""
        return {
            "status": "healthy",
            "app": self.app_name,
            "environment": self.environment,
            "version": self.app_version,
        }
