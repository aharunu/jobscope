"""Application domain repository protocols (domain ports)."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
)
from backend.domain.application.enums import ApplicationStatus


@runtime_checkable
class ApplicationRepository(Protocol):
    """Protocol defining persistence operations for Application entities.

    Decoupled from persistence technologies and ORM frameworks.
    """

    async def get_by_id(self, application_id: uuid.UUID) -> Application | None:
        """Retrieve an application by its unique identifier."""
        ...

    async def get_by_id_and_user_id(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Application | None:
        """Retrieve an application strictly scoped to the specified user."""
        ...

    async def get_by_job_and_user(
        self,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Application | None:
        """Retrieve an application for a specific job and user combination."""
        ...

    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Application]:
        """List user applications with optional status filter and pagination."""
        ...

    async def count_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
    ) -> int:
        """Count total applications belonging to a user matching filter criteria."""
        ...

    async def save(self, application: Application) -> Application:
        """Persist or update an application entity."""
        ...

    async def delete(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete an application scoped to user. Returns True if deleted."""
        ...

    async def add_status_history(
        self,
        history: ApplicationStatusHistory,
    ) -> ApplicationStatusHistory:
        """Persist an application status transition history entry."""
        ...

    async def list_status_history(
        self,
        application_id: uuid.UUID,
    ) -> list[ApplicationStatusHistory]:
        """Retrieve chronological status transition history for an application."""
        ...
