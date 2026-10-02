"""Matching domain repository protocols."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.matching.entities import AIAnalysis, MatchResult


@runtime_checkable
class MatchResultRepository(Protocol):
    async def get_owned_for_update(
        self, match_result_id: uuid.UUID, user_id: uuid.UUID
    ) -> MatchResult | None: ...

    async def save_ai_analysis(
        self, match_result: MatchResult, analysis: AIAnalysis
    ) -> MatchResult: ...

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

    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
        search_profile_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MatchResult], int]:
        """List persisted results scoped through both owned profile relationships."""
        ...
