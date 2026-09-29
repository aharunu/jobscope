"""SQLAlchemy implementation of MatchResultRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.domain.matching.entities import MatchResult
from backend.domain.matching.repositories import MatchResultRepository
from backend.infrastructure.database.models.matching import (
    MatchResultModel,
    RequirementMatchModel,
)


class SQLAlchemyMatchResultRepository(MatchResultRepository):
    """SQLAlchemy async implementation of MatchResultRepository.

    Transaction boundary note:
    Executes within an active AsyncSession transaction. It calls session.flush()
    to synchronize state and enforce uniqueness constraints, and NEVER calls
    session.commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, match_result_id: uuid.UUID) -> MatchResult | None:
        """Retrieve match result by primary key with requirement matches loaded."""
        stmt = (
            select(MatchResultModel)
            .options(selectinload(MatchResultModel.requirement_matches))
            .where(MatchResultModel.id == match_result_id)
        )
        result = await self.session.execute(stmt)
        orm_res = result.scalars().first()
        return orm_res.to_domain() if orm_res is not None else None

    async def get_by_job_and_search_profile(
        self,
        job_id: uuid.UUID,
        search_profile_id: uuid.UUID,
    ) -> MatchResult | None:
        """Retrieve match result for a unique job and search profile combination."""
        stmt = (
            select(MatchResultModel)
            .options(selectinload(MatchResultModel.requirement_matches))
            .where(
                MatchResultModel.job_id == job_id,
                MatchResultModel.search_profile_id == search_profile_id,
            )
        )
        result = await self.session.execute(stmt)
        orm_res = result.scalars().first()
        return orm_res.to_domain() if orm_res is not None else None

    async def save(self, match_result: MatchResult) -> MatchResult:
        """Persist or atomically overwrite a match result to enforce idempotency.

        Guarantees:
        - Unique constraint uq_match_results_job_base_search is honored.
        - Previous requirement matches are atomically replaced.
        """
        # 1. Check for existing record matching (job, base_profile, search_profile)
        stmt = select(MatchResultModel).where(
            MatchResultModel.job_id == match_result.job_id,
            MatchResultModel.base_profile_id == match_result.base_profile_id,
            MatchResultModel.search_profile_id == match_result.search_profile_id,
        )
        result = await self.session.execute(stmt)
        existing = result.scalars().first()

        target_id = existing.id if existing is not None else match_result.id
        now = datetime.now(UTC)

        if existing is not None:
            # Overwrite existing record attributes
            existing.deterministic_score = match_result.deterministic_score
            existing.final_score = match_result.final_score
            existing.confidence = match_result.confidence
            existing.ai_score = match_result.ai_score
            existing.ai_adjustment = match_result.ai_adjustment
            existing.updated_at = now

            # Cleanly replace child requirement matches
            del_stmt = sa.delete(RequirementMatchModel).where(
                RequirementMatchModel.match_result_id == target_id
            )
            await self.session.execute(del_stmt)
        else:
            # Insert new MatchResultModel
            orm_mr = MatchResultModel(
                id=target_id,
                job_id=match_result.job_id,
                base_profile_id=match_result.base_profile_id,
                search_profile_id=match_result.search_profile_id,
                deterministic_score=match_result.deterministic_score,
                final_score=match_result.final_score,
                confidence=match_result.confidence,
                ai_score=match_result.ai_score,
                ai_adjustment=match_result.ai_adjustment,
                created_at=match_result.created_at or now,
                updated_at=now,
            )
            self.session.add(orm_mr)

        # 2. Insert child requirement matches
        saved_req_matches = []
        for req_match in match_result.requirement_matches:
            orm_rm = RequirementMatchModel(
                id=req_match.id if req_match.id else uuid.uuid4(),
                match_result_id=target_id,
                requirement_id=req_match.requirement_id,
                match_status=req_match.match_status,
                score=req_match.score,
                evidence=req_match.evidence,
                reason=req_match.reason,
                is_blocker=req_match.is_blocker,
            )
            self.session.add(orm_rm)
            saved_req_matches.append(orm_rm.to_domain())

        await self.session.flush()

        return MatchResult(
            id=target_id,
            job_id=match_result.job_id,
            base_profile_id=match_result.base_profile_id,
            search_profile_id=match_result.search_profile_id,
            deterministic_score=match_result.deterministic_score,
            final_score=match_result.final_score,
            confidence=match_result.confidence,
            ai_score=match_result.ai_score,
            ai_adjustment=match_result.ai_adjustment,
            category_scores=match_result.category_scores,
            requirement_matches=saved_req_matches,
            explanation=match_result.explanation,
            created_at=match_result.created_at or now,
            updated_at=now,
        )
