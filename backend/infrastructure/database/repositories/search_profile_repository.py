"""SQLAlchemy implementation of SearchProfileRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.database.models.search_profile import (
    SearchProfileModel,
)


class SQLAlchemySearchProfileRepository(SearchProfileRepository):
    """SQLAlchemy async implementation of SearchProfileRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, search_profile_id: uuid.UUID) -> SearchProfile | None:
        """Retrieve a search profile by its ID."""
        orm_sp = await self.session.get(SearchProfileModel, search_profile_id)
        return orm_sp.to_domain() if orm_sp is not None else None

    async def get_by_id_and_base_profile_id(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> SearchProfile | None:
        """Retrieve a search profile strictly scoped to its base profile."""
        stmt = select(SearchProfileModel).where(
            SearchProfileModel.id == search_profile_id,
            SearchProfileModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        orm_sp = result.scalars().first()
        return orm_sp.to_domain() if orm_sp is not None else None

    async def list_by_base_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[SearchProfile]:
        """List all search profiles belonging to a given base profile."""
        stmt = (
            select(SearchProfileModel)
            .where(SearchProfileModel.base_profile_id == base_profile_id)
            .order_by(SearchProfileModel.created_at.asc(), SearchProfileModel.id.asc())
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def save(self, search_profile: SearchProfile) -> SearchProfile:
        """Persist or update a search profile entity."""
        orm_sp = SearchProfileModel.from_domain(search_profile)
        merged = await self.session.merge(orm_sp)
        await self.session.flush()
        return merged.to_domain()

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        """Delete a search profile scoped to base profile. Returns True if deleted."""
        stmt = delete(SearchProfileModel).where(
            SearchProfileModel.id == search_profile_id,
            SearchProfileModel.base_profile_id == base_profile_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
