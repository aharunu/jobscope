"""SQLAlchemy implementation of JobRequirementRepository."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.entities import JobRequirement
from backend.domain.job.repositories import JobRequirementRepository
from backend.infrastructure.database.models.job import JobRequirementModel


class SQLAlchemyJobRequirementRepository(JobRequirementRepository):
    """SQLAlchemy async implementation of JobRequirementRepository.

    Transaction boundary note:
    This repository executes within an active AsyncSession transaction.
    It calls session.flush() to synchronize state with the database,
    and NEVER calls session.commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_job_id(self, job_id: uuid.UUID) -> list[JobRequirement]:
        """Retrieve all requirements associated with a canonical job.

        Ordered deterministically by type, normalized_skill, and id.
        """
        stmt = (
            select(JobRequirementModel)
            .where(JobRequirementModel.job_id == job_id)
            .order_by(
                JobRequirementModel.type,
                JobRequirementModel.normalized_skill,
                JobRequirementModel.id,
            )
        )
        result = await self.session.execute(stmt)
        return [orm_req.to_domain() for orm_req in result.scalars().all()]

    async def save_requirements(
        self,
        job_id: uuid.UUID,
        requirements: list[JobRequirement],
    ) -> list[JobRequirement]:
        """Atomically replace and persist requirements for a canonical job.

        Existing requirements for the job are removed before inserting the new
        structured requirements, ensuring idempotency and zero duplicates on
        reprocessing.
        """
        # 1. Remove existing requirements for this job
        stmt = sa.delete(JobRequirementModel).where(
            JobRequirementModel.job_id == job_id
        )
        await self.session.execute(stmt)

        # 2. Insert new structured requirements
        saved: list[JobRequirement] = []
        for req in requirements:
            req_domain = JobRequirement(
                id=req.id if req.id is not None else uuid.uuid4(),
                job_id=job_id,
                type=req.type,
                description=req.description,
                normalized_skill=req.normalized_skill,
                required_level=req.required_level,
                importance=req.importance,
                criticality=req.criticality,
                evidence=req.evidence,
                created_at=req.created_at,
                updated_at=req.updated_at,
            )
            orm_req = JobRequirementModel.from_domain(req_domain)
            self.session.add(orm_req)
            saved.append(req_domain)

        await self.session.flush()
        return saved

    async def delete_by_job_id(self, job_id: uuid.UUID) -> int:
        """Delete all requirements associated with a canonical job."""
        stmt = sa.delete(JobRequirementModel).where(
            JobRequirementModel.job_id == job_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return int(result.rowcount or 0)
