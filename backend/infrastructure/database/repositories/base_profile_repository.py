"""SQLAlchemy implementation of BaseProfileRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.domain.profile.entities import BaseProfile
from backend.domain.profile.repositories import BaseProfileRepository
from backend.infrastructure.database.models.base_profile import (
    BaseProfileModel,
    ProfileEducationModel,
    ProfileExperienceModel,
    ProfileProjectModel,
    ProfileSkillModel,
)


class SQLAlchemyBaseProfileRepository(BaseProfileRepository):
    """SQLAlchemy async implementation of BaseProfileRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, profile_id: uuid.UUID) -> BaseProfile | None:
        """Retrieve a base profile by its ID with all child collections loaded."""
        stmt = (
            select(BaseProfileModel)
            .options(
                selectinload(BaseProfileModel.skills),
                selectinload(BaseProfileModel.experiences),
                selectinload(BaseProfileModel.educations),
                selectinload(BaseProfileModel.projects),
            )
            .where(BaseProfileModel.id == profile_id)
        )
        result = await self.session.execute(stmt)
        orm_profile = result.scalars().first()
        return orm_profile.to_domain() if orm_profile is not None else None

    async def get_by_user_id(self, user_id: uuid.UUID) -> BaseProfile | None:
        """Retrieve a base profile by owning user ID with child collections loaded."""
        stmt = (
            select(BaseProfileModel)
            .options(
                selectinload(BaseProfileModel.skills),
                selectinload(BaseProfileModel.experiences),
                selectinload(BaseProfileModel.educations),
                selectinload(BaseProfileModel.projects),
            )
            .where(BaseProfileModel.user_id == user_id)
            .order_by(BaseProfileModel.created_at.asc(), BaseProfileModel.id.asc())
        )
        result = await self.session.execute(stmt)
        orm_profile = result.scalars().first()
        return orm_profile.to_domain() if orm_profile is not None else None

    async def save(self, profile: BaseProfile) -> BaseProfile:
        """Persist or update a base profile entity."""
        orm_profile = BaseProfileModel.from_domain(profile)
        merged = await self.session.merge(orm_profile)

        # Save child collections if present on domain entity
        for skill in profile.skills:
            orm_skill = ProfileSkillModel.from_domain(skill)
            await self.session.merge(orm_skill)

        for exp in profile.experiences:
            orm_exp = ProfileExperienceModel.from_domain(exp)
            await self.session.merge(orm_exp)

        for edu in profile.educations:
            orm_edu = ProfileEducationModel.from_domain(edu)
            await self.session.merge(orm_edu)

        for proj in profile.projects:
            orm_proj = ProfileProjectModel.from_domain(proj)
            await self.session.merge(orm_proj)

        await self.session.flush()
        return await self.get_by_id(merged.id) or merged.to_domain()
