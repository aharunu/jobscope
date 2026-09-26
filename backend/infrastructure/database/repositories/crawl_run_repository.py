"""SQLAlchemy implementation of CrawlRunRepository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.infrastructure.database.models.crawl_run import (
    CrawlRunJobModel,
    CrawlRunModel,
)
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel


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

    async def get_run_detail(self, run_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve a crawl run by its primary key ID with source joined."""
        stmt = (
            select(CrawlRunModel)
            .options(joinedload(CrawlRunModel.source))
            .where(CrawlRunModel.id == run_id)
        )
        result = await self.session.execute(stmt)
        orm_run = result.scalars().first()
        return orm_run.to_domain() if orm_run is not None else None

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        """Retrieve the most recent crawl run for a source."""
        stmt = (
            select(CrawlRunModel)
            .options(joinedload(CrawlRunModel.source))
            .where(CrawlRunModel.source_id == source_id)
            .order_by(CrawlRunModel.started_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm_run = result.scalars().first()
        return orm_run.to_domain() if orm_run is not None else None

    async def list_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRun]:
        """List crawl runs matching filter criteria with deterministic ordering."""
        stmt = select(CrawlRunModel).options(joinedload(CrawlRunModel.source))
        if ats_type is not None:
            stmt = stmt.join(SourceModel, CrawlRunModel.source_id == SourceModel.id)
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if source_id is not None:
            stmt = stmt.where(CrawlRunModel.source_id == source_id)

        if status is not None:
            stmt = stmt.where(CrawlRunModel.status == status)

        if date_from is not None:
            stmt = stmt.where(CrawlRunModel.created_at >= date_from)

        if date_to is not None:
            stmt = stmt.where(CrawlRunModel.created_at < date_to)

        stmt = (
            stmt.order_by(CrawlRunModel.created_at.desc(), CrawlRunModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [orm_run.to_domain() for orm_run in result.scalars().all()]

    async def count_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        """Count total crawl runs matching filter criteria."""
        stmt = select(func.count(CrawlRunModel.id))
        if ats_type is not None:
            stmt = stmt.join(SourceModel, CrawlRunModel.source_id == SourceModel.id)
            stmt = stmt.where(SourceModel.ats_type == ats_type)

        if source_id is not None:
            stmt = stmt.where(CrawlRunModel.source_id == source_id)

        if status is not None:
            stmt = stmt.where(CrawlRunModel.status == status)

        if date_from is not None:
            stmt = stmt.where(CrawlRunModel.created_at >= date_from)

        if date_to is not None:
            stmt = stmt.where(CrawlRunModel.created_at < date_to)

        result = await self.session.execute(stmt)
        return result.scalar_one()

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

    async def list_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRunJob]:
        """List job actions for a specific crawl run with deterministic ordering."""
        stmt = (
            select(CrawlRunJobModel)
            .options(joinedload(CrawlRunJobModel.job))
            .join(JobModel, CrawlRunJobModel.job_id == JobModel.id)
            .where(CrawlRunJobModel.crawl_run_id == run_id)
        )
        if action is not None:
            stmt = stmt.where(CrawlRunJobModel.action == action)

        stmt = (
            stmt.order_by(
                CrawlRunJobModel.action.asc(),
                JobModel.title.asc(),
                JobModel.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [orm_link.to_domain() for orm_link in result.scalars().all()]

    async def count_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
    ) -> int:
        """Count total job actions for a specific crawl run."""
        stmt = (
            select(func.count())
            .select_from(CrawlRunJobModel)
            .where(CrawlRunJobModel.crawl_run_id == run_id)
        )
        if action is not None:
            stmt = stmt.where(CrawlRunJobModel.action == action)

        result = await self.session.execute(stmt)
        return result.scalar_one()
