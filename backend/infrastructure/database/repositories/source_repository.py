"""SQLAlchemy implementation of SourceRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.source.entities import Source
from backend.domain.source.repositories import SourceRepository
from backend.infrastructure.database.models.source import SourceModel


class SQLAlchemySourceRepository(SourceRepository):
    """SQLAlchemy async implementation of the SourceRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        """Retrieve a source by its unique ID."""
        orm_source = await self.session.get(SourceModel, source_id)
        return orm_source.to_domain() if orm_source is not None else None

    async def get_by_url(self, url: str) -> Source | None:
        """Retrieve a source by its exact career page / API URL."""
        stmt = select(SourceModel).where(SourceModel.url == url)
        result = await self.session.execute(stmt)
        orm_source = result.scalars().first()
        return orm_source.to_domain() if orm_source is not None else None

    async def list_all(
        self,
        active_only: bool = False,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        """List sources matching filters and pagination."""
        stmt = select(SourceModel)
        if active_only:
            stmt = stmt.where(SourceModel.active.is_(True))
        if ats_type is not None:
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        stmt = stmt.order_by(SourceModel.name.asc(), SourceModel.created_at.desc())

        if offset > 0:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        orm_sources: Sequence[SourceModel] = result.scalars().all()
        return [s.to_domain() for s in orm_sources]

    async def save(self, source: Source) -> Source:
        """Persist or update a single source entity."""
        orm_source = SourceModel.from_domain(source)
        merged = await self.session.merge(orm_source)
        await self.session.flush()
        return merged.to_domain()

    async def save_bulk(self, sources: list[Source]) -> list[Source]:
        """Persist multiple source entities in batch."""
        saved: list[Source] = []
        for source in sources:
            orm_source = SourceModel.from_domain(source)
            merged = await self.session.merge(orm_source)
            saved.append(merged.to_domain())
        await self.session.flush()
        return saved

    async def count(
        self,
        active_only: bool = False,
        ats_type: str | None = None,
    ) -> int:
        """Count registered sources matching criteria."""
        stmt = select(func.count()).select_from(SourceModel)
        if active_only:
            stmt = stmt.where(SourceModel.active.is_(True))
        if ats_type is not None:
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        result = await self.session.execute(stmt)
        return int(result.scalar_one())
