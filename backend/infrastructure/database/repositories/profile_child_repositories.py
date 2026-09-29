"""SQLAlchemy implementations of child profile repository protocols."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.profile.entities import (
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.domain.profile.repositories import (
    ProfileEducationRepository,
    ProfileExperienceRepository,
    ProfileProjectRepository,
    ProfileSkillRepository,
)
from backend.infrastructure.database.models.base_profile import (
    ProfileEducationModel,
    ProfileExperienceModel,
    ProfileProjectModel,
    ProfileSkillModel,
)


class SQLAlchemyProfileSkillRepository(ProfileSkillRepository):
    """SQLAlchemy async implementation of ProfileSkillRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileSkill]:
        """List all skills for a base profile, ordered deterministically."""
        stmt = (
            select(ProfileSkillModel)
            .where(ProfileSkillModel.base_profile_id == base_profile_id)
            .order_by(ProfileSkillModel.created_at.asc(), ProfileSkillModel.id.asc())
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def get_by_id_and_profile_id(
        self, skill_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileSkill | None:
        """Retrieve a single skill strictly scoped to its base profile."""
        stmt = select(ProfileSkillModel).where(
            ProfileSkillModel.id == skill_id,
            ProfileSkillModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        orm_item = result.scalars().first()
        return orm_item.to_domain() if orm_item is not None else None

    async def save(self, skill: ProfileSkill) -> ProfileSkill:
        """Persist or update a skill entity."""
        orm_item = ProfileSkillModel.from_domain(skill)
        merged = await self.session.merge(orm_item)
        await self.session.flush()
        return merged.to_domain()

    async def delete(self, skill_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete a skill scoped to a base profile. Returns True if deleted."""
        stmt = delete(ProfileSkillModel).where(
            ProfileSkillModel.id == skill_id,
            ProfileSkillModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


class SQLAlchemyProfileExperienceRepository(ProfileExperienceRepository):
    """SQLAlchemy async implementation of ProfileExperienceRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileExperience]:
        """List all experiences for a base profile, ordered by current then date."""
        stmt = (
            select(ProfileExperienceModel)
            .where(ProfileExperienceModel.base_profile_id == base_profile_id)
            .order_by(
                ProfileExperienceModel.is_current.desc(),
                ProfileExperienceModel.start_date.desc(),
                ProfileExperienceModel.id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def get_by_id_and_profile_id(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileExperience | None:
        """Retrieve a single experience strictly scoped to its base profile."""
        stmt = select(ProfileExperienceModel).where(
            ProfileExperienceModel.id == experience_id,
            ProfileExperienceModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        orm_item = result.scalars().first()
        return orm_item.to_domain() if orm_item is not None else None

    async def save(self, experience: ProfileExperience) -> ProfileExperience:
        """Persist or update an experience entity."""
        orm_item = ProfileExperienceModel.from_domain(experience)
        merged = await self.session.merge(orm_item)
        await self.session.flush()
        return merged.to_domain()

    async def delete(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        """Delete an experience scoped to a base profile. Returns True if deleted."""
        stmt = delete(ProfileExperienceModel).where(
            ProfileExperienceModel.id == experience_id,
            ProfileExperienceModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


class SQLAlchemyProfileEducationRepository(ProfileEducationRepository):
    """SQLAlchemy async implementation of ProfileEducationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileEducation]:
        """List all education records for a base profile."""
        stmt = (
            select(ProfileEducationModel)
            .where(ProfileEducationModel.base_profile_id == base_profile_id)
            .order_by(
                ProfileEducationModel.start_year.desc().nullslast(),
                ProfileEducationModel.id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def get_by_id_and_profile_id(
        self, education_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileEducation | None:
        """Retrieve a single education record strictly scoped to its base profile."""
        stmt = select(ProfileEducationModel).where(
            ProfileEducationModel.id == education_id,
            ProfileEducationModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        orm_item = result.scalars().first()
        return orm_item.to_domain() if orm_item is not None else None

    async def save(self, education: ProfileEducation) -> ProfileEducation:
        """Persist or update an education entity."""
        orm_item = ProfileEducationModel.from_domain(education)
        merged = await self.session.merge(orm_item)
        await self.session.flush()
        return merged.to_domain()

    async def delete(self, education_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete an education record. Returns True if deleted."""
        stmt = delete(ProfileEducationModel).where(
            ProfileEducationModel.id == education_id,
            ProfileEducationModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0


class SQLAlchemyProfileProjectRepository(ProfileProjectRepository):
    """SQLAlchemy async implementation of ProfileProjectRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileProject]:
        """List all project items for a base profile."""
        stmt = (
            select(ProfileProjectModel)
            .where(ProfileProjectModel.base_profile_id == base_profile_id)
            .order_by(
                ProfileProjectModel.created_at.asc(), ProfileProjectModel.id.asc()
            )
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def get_by_id_and_profile_id(
        self, project_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileProject | None:
        """Retrieve a single project item strictly scoped to its base profile."""
        stmt = select(ProfileProjectModel).where(
            ProfileProjectModel.id == project_id,
            ProfileProjectModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        orm_item = result.scalars().first()
        return orm_item.to_domain() if orm_item is not None else None

    async def save(self, project: ProfileProject) -> ProfileProject:
        """Persist or update a project entity."""
        orm_item = ProfileProjectModel.from_domain(project)
        merged = await self.session.merge(orm_item)
        await self.session.flush()
        return merged.to_domain()

    async def delete(self, project_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete a project item scoped to a base profile. Returns True if deleted."""
        stmt = delete(ProfileProjectModel).where(
            ProfileProjectModel.id == project_id,
            ProfileProjectModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
