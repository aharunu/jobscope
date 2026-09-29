"""Deterministic matching application service."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from backend.application.matching.exceptions import (
    JobNotFoundError,
    SearchProfileNotFoundError,
)
from backend.domain.job.repositories import JobRepository
from backend.domain.matching.deterministic_engine import (
    DeterministicMatchEngine,
)
from backend.domain.matching.entities import MatchResult
from backend.domain.matching.repositories import MatchResultRepository
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.repositories import SearchProfileRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MatchingService:
    """Application orchestration service for deterministic job matching.

    Coordinates retrieval of canonical jobs, user profiles, and search targets,
    invokes the pure deterministic engine, and persists the result.
    """

    job_repo: JobRepository
    base_profile_repo: BaseProfileRepository
    search_profile_repo: SearchProfileRepository
    match_result_repo: MatchResultRepository
    engine: DeterministicMatchEngine = field(default_factory=DeterministicMatchEngine)

    async def match_job(
        self,
        job_id: uuid.UUID,
        search_profile_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MatchResult:
        """Execute deterministic match evaluation and persist outcome.

        Enforces candidate ownership invariant:
            user_id -> owned BaseProfile -> owned SearchProfile -> Job -> MatchResult
        """
        # 1. Load canonical job with structured requirements
        job = await self.job_repo.get_job_detail(job_id)
        if job is None:
            job = await self.job_repo.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found")

        # 2. Ownership verification: user_id -> owned BaseProfile
        base_profile = await self.base_profile_repo.get_by_user_id(user_id)
        if base_profile is None:
            raise SearchProfileNotFoundError(
                f"Search profile with ID '{search_profile_id}' not found"
            )

        # 3. Ownership verification: owned BaseProfile -> owned SearchProfile
        search_profile = await self.search_profile_repo.get_by_id_and_base_profile_id(
            search_profile_id=search_profile_id,
            base_profile_id=base_profile.id,
        )
        if search_profile is None:
            raise SearchProfileNotFoundError(
                f"Search profile with ID '{search_profile_id}' not found"
            )

        # 4. Execute deterministic matching engine (Pure Python domain)
        match_result = self.engine.evaluate(
            job=job,
            base_profile=base_profile,
            search_profile=search_profile,
            requirements=job.requirements,
        )

        # 5. Persist match result (guaranteeing idempotency and no duplicate rows)
        persisted_result = await self.match_result_repo.save(match_result)

        logger.info(
            "Deterministic match completed for user=%s job=%s profile=%s score=%s "
            "confidence=%s",
            user_id,
            job_id,
            search_profile_id,
            persisted_result.deterministic_score,
            persisted_result.confidence,
        )

        return persisted_result
