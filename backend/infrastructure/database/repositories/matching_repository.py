"""SQLAlchemy implementation of MatchResultRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.domain.matching.entities import AIAnalysis, MatchResult
from backend.domain.matching.repositories import MatchResultRepository
from backend.infrastructure.database.models.base_profile import BaseProfileModel
from backend.infrastructure.database.models.matching import (
    AIAnalysisModel,
    AIEvidenceModel,
    MatchResultModel,
    RequirementMatchModel,
)
from backend.infrastructure.database.models.search_profile import SearchProfileModel


class SQLAlchemyMatchResultRepository(MatchResultRepository):
    """SQLAlchemy async implementation of MatchResultRepository.

    Transaction boundary note:
    Executes within an active AsyncSession transaction. It calls session.flush()
    to synchronize state and enforce uniqueness constraints, and NEVER calls
    session.commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _loads():
        return (
            selectinload(MatchResultModel.requirement_matches),
            selectinload(MatchResultModel.ai_analysis).selectinload(
                AIAnalysisModel.evidence_list
            ),
        )

    async def get_owned_for_update(
        self, match_result_id: uuid.UUID, user_id: uuid.UUID
    ) -> MatchResult | None:
        statement = (
            select(MatchResultModel)
            .join(
                BaseProfileModel,
                MatchResultModel.base_profile_id == BaseProfileModel.id,
            )
            .join(
                SearchProfileModel,
                sa.and_(
                    MatchResultModel.search_profile_id == SearchProfileModel.id,
                    SearchProfileModel.base_profile_id == BaseProfileModel.id,
                ),
            )
            .where(
                MatchResultModel.id == match_result_id,
                BaseProfileModel.user_id == user_id,
            )
            .options(*self._loads())
            .with_for_update(of=MatchResultModel)
            .execution_options(populate_existing=True)
        )
        row = (await self.session.execute(statement)).scalar_one_or_none()
        return row.to_domain() if row else None

    async def save_ai_analysis(
        self, match_result: MatchResult, analysis: AIAnalysis
    ) -> MatchResult:
        row = await self.session.get(MatchResultModel, match_result.id)
        existing = (
            await self.session.execute(
                select(AIAnalysisModel).where(
                    AIAnalysisModel.match_result_id == match_result.id
                )
            )
        ).scalar_one_or_none()
        if existing:
            await self.session.delete(existing)
            await self.session.flush()
        saved = AIAnalysisModel.from_domain(analysis)
        self.session.add(saved)
        await self.session.flush()
        for evidence in analysis.evidence:
            self.session.add(AIEvidenceModel.from_domain(evidence))
        row.ai_score = match_result.ai_score
        row.ai_adjustment = match_result.ai_adjustment
        row.final_score = match_result.final_score
        row.confidence = match_result.confidence
        row.updated_at = datetime.now(UTC)
        await self.session.flush()
        persisted = await self.get_by_id(match_result.id)
        assert persisted is not None
        return persisted

    async def get_by_id(self, match_result_id: uuid.UUID) -> MatchResult | None:
        """Retrieve match result by primary key with requirement matches loaded."""
        stmt = (
            select(MatchResultModel)
            .options(*self._loads())
            .where(MatchResultModel.id == match_result_id)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        orm_res = result.scalars().first()
        return orm_res.to_domain() if orm_res is not None else None

    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
        search_profile_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MatchResult], int]:
        stmt = (
            select(MatchResultModel)
            .join(
                BaseProfileModel,
                MatchResultModel.base_profile_id == BaseProfileModel.id,
            )
            .join(
                SearchProfileModel,
                sa.and_(
                    MatchResultModel.search_profile_id == SearchProfileModel.id,
                    SearchProfileModel.base_profile_id == BaseProfileModel.id,
                ),
            )
            .where(BaseProfileModel.user_id == user_id)
        )
        if job_id is not None:
            stmt = stmt.where(MatchResultModel.job_id == job_id)
        if search_profile_id is not None:
            stmt = stmt.where(MatchResultModel.search_profile_id == search_profile_id)
        total = (
            await self.session.execute(
                select(sa.func.count()).select_from(stmt.subquery())
            )
        ).scalar_one()
        rows = await self.session.execute(
            stmt.options(*self._loads())
            .order_by(MatchResultModel.updated_at.desc(), MatchResultModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [row.to_domain() for row in rows.scalars().all()], total

    async def get_by_job_and_search_profile(
        self,
        job_id: uuid.UUID,
        search_profile_id: uuid.UUID,
    ) -> MatchResult | None:
        """Retrieve match result for a unique job and search profile combination."""
        stmt = (
            select(MatchResultModel)
            .options(*self._loads())
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
        stmt = (
            select(MatchResultModel)
            .where(
                MatchResultModel.job_id == match_result.job_id,
                MatchResultModel.base_profile_id == match_result.base_profile_id,
                MatchResultModel.search_profile_id == match_result.search_profile_id,
            )
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        existing = result.scalars().first()

        target_id = existing.id if existing is not None else match_result.id
        now = datetime.now(UTC)
        snapshot = MatchResultModel.from_domain(match_result)

        if existing is not None:
            # Recalculation resets the AI projection and cache in the same transaction.
            await self.session.execute(
                sa.delete(AIAnalysisModel).where(
                    AIAnalysisModel.match_result_id == target_id
                )
            )
            # Overwrite existing record attributes
            existing.deterministic_score = match_result.deterministic_score
            existing.final_score = match_result.final_score
            existing.confidence = match_result.confidence
            existing.ai_score = match_result.ai_score
            existing.ai_adjustment = match_result.ai_adjustment
            existing.updated_at = now
            existing.category_scores = snapshot.category_scores
            existing.explanation = snapshot.explanation

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
                category_scores=snapshot.category_scores,
                explanation=snapshot.explanation,
            )
            self.session.add(orm_mr)

        # 2. Insert child requirement matches
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

        await self.session.flush()

        persisted = await self.get_by_id(target_id)
        assert persisted is not None
        return persisted
