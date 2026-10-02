"""Domain and application exceptions for the matching subsystem."""

from __future__ import annotations

from typing import Any

from backend.application.common.exceptions import JobScopeError


class MatchingError(JobScopeError):
    """Base exception for matching application operations."""

    def __init__(
        self,
        message: str = "Matching operation failed",
        code: str = "MATCHING_ERROR",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class MatchResultNotFoundError(MatchingError):
    """No saved calculation exists for the requested owned job/profile pair."""

    def __init__(self) -> None:
        super().__init__(
            "No saved match result yet", code="MATCH_RESULT_NOT_FOUND", status_code=404
        )


class JobNotFoundError(MatchingError):
    """Raised when the specified Job entity does not exist."""

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


class SearchProfileNotFoundError(MatchingError):
    """Raised when the specified SearchProfile entity does not exist."""

    def __init__(
        self,
        message: str = "Search profile not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="SEARCH_PROFILE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class BaseProfileNotFoundError(MatchingError):
    """Raised when the related BaseProfile entity does not exist."""

    def __init__(
        self,
        message: str = "Base profile not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="BASE_PROFILE_NOT_FOUND",
            status_code=404,
            details=details,
        )
