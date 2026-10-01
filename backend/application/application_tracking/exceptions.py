"""Domain and application exceptions for the application tracking subsystem."""

from __future__ import annotations

from typing import Any

from backend.application.common.exceptions import JobScopeError


class ApplicationError(JobScopeError):
    """Base exception for application tracking operations."""

    def __init__(
        self,
        message: str = "Application tracking operation failed",
        code: str = "APPLICATION_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class ApplicationNotFoundError(ApplicationError):
    """Raised when the specified Application entity does not exist or is
    unauthorized.
    """

    def __init__(
        self,
        message: str = "Application not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="APPLICATION_NOT_FOUND",
            status_code=404,
            details=details,
        )


class JobNotFoundError(ApplicationError):
    """Raised when the specified Job does not exist to track."""

    def __init__(
        self,
        message: str = "Job not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="JOB_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ApplicationAlreadyExistsError(ApplicationError):
    """Raised when a candidate already tracks the specified job."""

    def __init__(
        self,
        message: str = "Application already exists for this job",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="APPLICATION_ALREADY_EXISTS",
            status_code=409,
            details=details,
        )


class InvalidStatusTransitionError(ApplicationError):
    """Raised when an application status transition violates lifecycle rules."""

    def __init__(
        self,
        message: str = "Invalid application status transition",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="INVALID_STATUS_TRANSITION",
            status_code=422,
            details=details,
        )


class ApplicationValidationError(ApplicationError):
    """Raised when application input fails business validation."""

    def __init__(
        self,
        message: str = "Application validation failed",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="APPLICATION_VALIDATION_ERROR",
            status_code=422,
            details=details,
        )
