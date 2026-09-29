"""Domain and application exceptions for profile management."""

from typing import Any

from backend.application.common.exceptions import JobScopeError


class ProfileNotFoundError(JobScopeError):
    """Raised when a requested profile does not exist."""

    def __init__(
        self,
        message: str = "Profile not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="PROFILE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ProfileValidationError(JobScopeError):
    """Raised when profile data violates domain validation rules."""

    def __init__(
        self,
        message: str = "Invalid profile data",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="PROFILE_VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class ProfileSkillNotFoundError(ProfileNotFoundError):
    """Raised when a requested skill does not exist or does not belong to the user."""

    def __init__(
        self,
        message: str = "Skill not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class ProfileExperienceNotFoundError(ProfileNotFoundError):
    """Raised when an experience does not exist or does not belong to the user."""

    def __init__(
        self,
        message: str = "Experience not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class ProfileEducationNotFoundError(ProfileNotFoundError):
    """Raised when an education record does not exist or does not belong to the user."""

    def __init__(
        self,
        message: str = "Education record not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class ProfileProjectNotFoundError(ProfileNotFoundError):
    """Raised when a project does not exist or does not belong to the user."""

    def __init__(
        self,
        message: str = "Project not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)


class SearchProfileNotFoundError(ProfileNotFoundError):
    """Raised when a search profile does not exist or does not belong to the user."""

    def __init__(
        self,
        message: str = "Search profile not found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.code = "SEARCH_PROFILE_NOT_FOUND"
