"""SQLAlchemy implementation of SourceRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.source.entities import Source
from backend.domain.source.normalization import normalize_source_url
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
        """Retrieve a source by its exact or normalized career page / API URL."""
        normalized = normalize_source_url(url)
        stmt = select(SourceModel).where(
            (SourceModel.url == url) | (SourceModel.url == normalized)
        )
        result = await self.session.execute(stmt)
        orm_source = result.scalars().first()
        return orm_source.to_domain() if orm_source is not None else None

    async def list_all(
        self,
        active_only: bool = False,
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        """List sources matching filters and pagination."""
        stmt = select(SourceModel)
        if is_active is not None:
            stmt = stmt.where(SourceModel.active.is_(is_active))
        elif active_only:
            stmt = stmt.where(SourceModel.active.is_(True))

        if ats_type is not None:
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if search_query and search_query.strip():
            pattern = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    SourceModel.name.ilike(pattern),
                    SourceModel.company.ilike(pattern),
                    SourceModel.url.ilike(pattern),
                )
            )

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
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        """Count registered sources matching criteria."""
        stmt = select(func.count()).select_from(SourceModel)
        if is_active is not None:
            stmt = stmt.where(SourceModel.active.is_(is_active))
        elif active_only:
            stmt = stmt.where(SourceModel.active.is_(True))

        if ats_type is not None:
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if search_query and search_query.strip():
            pattern = f"%{search_query.strip()}%"
            stmt = stmt.where(
                or_(
                    SourceModel.name.ilike(pattern),
                    SourceModel.company.ilike(pattern),
                    SourceModel.url.ilike(pattern),
                )
            )

        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_by_ats_type(self) -> dict[str, int]:
        """Aggregate total sources grouped by ATS platform type."""
        stmt = select(SourceModel.ats_type, func.count(SourceModel.id)).group_by(
            SourceModel.ats_type
        )
        result = await self.session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}

    async def count_by_country(self) -> dict[str, int]:
        """Aggregate total sources grouped by country code."""
        country_expr = func.coalesce(SourceModel.country, "Unknown")
        stmt = select(
            country_expr,
            func.count(SourceModel.id),
        ).group_by(country_expr)
        result = await self.session.execute(stmt)
        return {str(row[0]): int(row[1]) for row in result.all()}
