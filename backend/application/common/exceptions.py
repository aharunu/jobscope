"""Base application exceptions for JobScope."""

from typing import Any


class JobScopeError(Exception):
    """Base exception for all domain and application errors in JobScope."""

    def __init__(
        self,
        message: str,
        code: str = "APPLICATION_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class InfrastructureError(JobScopeError):
    """Base exception for infrastructure and external dependency failures."""

    def __init__(
        self,
        message: str = "An infrastructure error occurred",
        code: str = "INFRASTRUCTURE_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )
