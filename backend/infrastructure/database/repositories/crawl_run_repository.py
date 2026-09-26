"""SQLAlchemy implementation of CrawlRunRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.infrastructure.database.models.crawl_run import (
    CrawlRunJobModel,
    CrawlRunModel,
)


class SQLAlchemyCrawlRunRepository(CrawlRunRepository):
    """SQLAlchemy async implementation of the CrawlRunRepository protocol."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, run: CrawlRun) -> CrawlRun:
        """Persist a new crawl run record."""
        orm_run = CrawlRunModel.from_domain(run)
        self.session.add(orm_run)
        await self.session.flush()
        return orm_run.to_domain()

    async def update_run(self, run: CrawlRun) -> CrawlRun:
        """Update an existing crawl run record."""
        orm_run = CrawlRunModel.from_domain(run)
        merged = await self.session.merge(orm_run)
        await self.session.flush()
        return merged.to_domain()

    async def get_by_id(self, run_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve a crawl run by its primary key ID."""
        orm_run = await self.session.get(CrawlRunModel, run_id)
        return orm_run.to_domain() if orm_run is not None else None

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve the most recent crawl run for a source."""
        stmt = (
            select(CrawlRunModel)
            .where(CrawlRunModel.source_id == source_id)
            .order_by(CrawlRunModel.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm_run = result.scalars().first()
        return orm_run.to_domain() if orm_run is not None else None

    async def record_job_action(
        self,
        run_id: uuid.UUID,
        job_id: uuid.UUID,
        action: CrawlJobAction,
    ) -> None:
        """Record an action performed on a job during a crawl run."""
        link = CrawlRunJobModel(
            crawl_run_id=run_id,
            job_id=job_id,
            action=action,
        )
        await self.session.merge(link)
        await self.session.flush()

    async def record_job_actions(self, links: list[CrawlRunJob]) -> None:
        """Record multiple job actions in batch."""
        for link in links:
            orm_link = CrawlRunJobModel.from_domain(link)
            await self.session.merge(orm_link)
        await self.session.flush()
