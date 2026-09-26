"""Crawler and ATS adapter application exceptions."""

from __future__ import annotations

from typing import Any

from backend.application.common.exceptions import JobScopeError


class CrawlerError(JobScopeError):
    """Base exception for all crawler and ATS adapter application failures."""

    def __init__(
        self,
        message: str = "A crawler error occurred",
        code: str = "CRAWLER_ERROR",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class UnsupportedATSError(CrawlerError):
    """Raised when an ATS platform type is unrecognized or unsupported."""

    def __init__(
        self,
        message: str = "Unsupported ATS platform type",
        code: str = "UNSUPPORTED_ATS_TYPE",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class AdapterUnavailableError(CrawlerError):
    """Raised when an ATS platform is recognized, but no adapter is registered."""

    def __init__(
        self,
        message: str = "No adapter is available for this ATS platform",
        code: str = "ADAPTER_UNAVAILABLE",
        status_code: int = 501,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class InvalidSourceConfigurationError(CrawlerError):
    """Raised when source operational configuration is invalid for an adapter."""

    def __init__(
        self,
        message: str = "Invalid source configuration for ATS adapter",
        code: str = "INVALID_SOURCE_CONFIG",
        status_code: int = 422,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class AdapterExecutionError(CrawlerError):
    """Raised when an adapter encounters an operational error during crawl execution."""

    def __init__(
        self,
        message: str = "ATS adapter execution failed",
        code: str = "ADAPTER_EXECUTION_FAILURE",
        status_code: int = 502,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class MalformedAdapterResultError(CrawlerError):
    """Raised when an adapter returns data violating the CrawlResult contract."""

    def __init__(
        self,
        message: str = "Adapter returned malformed result payload",
        code: str = "MALFORMED_ADAPTER_RESULT",
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )
