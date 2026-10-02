"""SQLAlchemy implementation of ApplicationRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.application.application_tracking.exceptions import (
    ApplicationAlreadyExistsError,
)
from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
)
from backend.domain.application.enums import ApplicationStatus
from backend.domain.application.repositories import ApplicationRepository
from backend.infrastructure.database.models.application import (
    ApplicationModel,
    ApplicationStatusHistoryModel,
)
from backend.infrastructure.database.models.job import JobModel


class SQLAlchemyApplicationRepository(ApplicationRepository):
    """SQLAlchemy async implementation of ApplicationRepository.

    Transaction boundary note:
    Executes within an active AsyncSession transaction. It calls session.flush()
    to synchronize state and enforce uniqueness constraints, and NEVER calls
    session.commit().
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, application_id: uuid.UUID) -> Application | None:
        """Retrieve an application by its unique identifier."""
        stmt = (
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.job).selectinload(JobModel.source),
                selectinload(ApplicationModel.status_history),
            )
            .where(ApplicationModel.id == application_id)
        )
        result = await self.session.execute(stmt)
        orm_app = result.scalars().first()
        return orm_app.to_domain() if orm_app is not None else None

    async def get_by_id_and_user_id(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Application | None:
        """Retrieve an application strictly scoped to the specified user."""
        stmt = (
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.job).selectinload(JobModel.source),
                selectinload(ApplicationModel.status_history),
            )
            .where(
                ApplicationModel.id == application_id,
                ApplicationModel.user_id == user_id,
            )
        )
        if for_update:
            # Refresh cached state after acquiring the lock: another request may
            # have committed a transition while this transaction was waiting.
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        result = await self.session.execute(stmt)
        orm_app = result.scalars().first()
        return orm_app.to_domain() if orm_app is not None else None

    async def get_by_job_and_user(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Application | None:
        """Retrieve an application for a specific job and user combination."""
        stmt = (
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.job).selectinload(JobModel.source),
                selectinload(ApplicationModel.status_history),
            )
            .where(
                ApplicationModel.job_id == job_id,
                ApplicationModel.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        orm_app = result.scalars().first()
        return orm_app.to_domain() if orm_app is not None else None

    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Application]:
        """List user applications with optional status filter and pagination."""
        stmt = (
            select(ApplicationModel)
            .options(
                selectinload(ApplicationModel.job).selectinload(JobModel.source),
                selectinload(ApplicationModel.status_history),
            )
            .where(ApplicationModel.user_id == user_id)
        )
        if status is not None:
            stmt = stmt.where(ApplicationModel.status == status)

        stmt = stmt.order_by(
            ApplicationModel.created_at.desc(),
            ApplicationModel.id.desc(),
        )
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]

    async def count_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
    ) -> int:
        """Count total applications belonging to a user matching filter criteria."""
        stmt = select(func.count(ApplicationModel.id)).where(
            ApplicationModel.user_id == user_id
        )
        if status is not None:
            stmt = stmt.where(ApplicationModel.status == status)

        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def save(self, application: Application) -> Application:
        """Persist or update an application entity."""
        orm_app = await self.session.get(ApplicationModel, application.id)
        now = datetime.now(UTC)

        if orm_app is not None:
            orm_app.status = application.status
            orm_app.notes = application.notes
            orm_app.updated_at = application.updated_at or now
        else:
            orm_app = ApplicationModel(
                id=application.id,
                job_id=application.job_id,
                user_id=application.user_id,
                status=application.status,
                notes=application.notes,
                created_at=application.created_at or now,
                updated_at=application.updated_at or now,
            )
            self.session.add(orm_app)

        try:
            await self.session.flush()
        except IntegrityError as exc:
            original = exc.orig
            cause = getattr(original, "__cause__", None)
            diagnostic = getattr(original, "diag", None)
            constraint = (
                getattr(original, "constraint_name", None)
                or getattr(cause, "constraint_name", None)
                or getattr(diagnostic, "constraint_name", None)
            )
            if constraint == "uq_applications_job_user":
                # The request session owner rolls back the failed transaction.
                raise ApplicationAlreadyExistsError() from exc
            raise
        return await self.get_by_id(orm_app.id) or orm_app.to_domain()

    async def delete(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an application scoped to user. Returns True if deleted."""
        stmt = delete(ApplicationModel).where(
            ApplicationModel.id == application_id,
            ApplicationModel.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0

    async def add_status_history(
        self,
        history: ApplicationStatusHistory,
    ) -> ApplicationStatusHistory:
        """Persist an application status transition history entry."""
        orm_hist = ApplicationStatusHistoryModel(
            id=history.id,
            application_id=history.application_id,
            from_status=history.from_status,
            to_status=history.to_status,
            changed_at=history.changed_at or datetime.now(UTC),
        )
        self.session.add(orm_hist)
        await self.session.flush()
        return orm_hist.to_domain()

    async def list_status_history(
        self,
        application_id: uuid.UUID,
    ) -> list[ApplicationStatusHistory]:
        """Retrieve chronological status transition history for an application."""
        stmt = (
            select(ApplicationStatusHistoryModel)
            .where(ApplicationStatusHistoryModel.application_id == application_id)
            .order_by(
                ApplicationStatusHistoryModel.changed_at.asc(),
                ApplicationStatusHistoryModel.id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return [m.to_domain() for m in result.scalars().all()]
