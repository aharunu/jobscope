"""Known non-SQL failures that can safely be handled within ingestion."""

from backend.application.common.exceptions import JobScopeError


class JobURLConflictError(JobScopeError):
    def __init__(self) -> None:
        super().__init__(
            message="Canonical URL belongs to another Job",
            code="JOB_URL_OWNERSHIP_CONFLICT",
            status_code=409,
        )


class RequirementExtractionError(Exception):
    """Pure extraction failed before any requirement persistence was attempted."""
