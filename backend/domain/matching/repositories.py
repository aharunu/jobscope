"""Matching domain repository protocols."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.matching.entities import MatchResult


@runtime_checkable
class MatchResultRepository(Protocol):
    """Protocol defining persistence operations for MatchResult domain entities."""

    async def get_by_id(self, match_result_id: uuid.UUID) -> MatchResult | None:
        """Retrieve a match result by its unique identifier."""
        ...

    async def get_by_job_and_search_profile(
        self,
        job_id: uuid.UUID,
        search_profile_id: uuid.UUID,
    ) -> MatchResult | None:
        """Retrieve match result for a unique job and search profile combination."""
        ...

    async def save(self, match_result: MatchResult) -> MatchResult:
        """Persist or atomically overwrite a match result and requirement matches."""
        ...
