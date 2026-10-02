"""Application service for candidate Application Tracking use cases."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from backend.application.application_tracking.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationNotFoundError,
    ApplicationValidationError,
    InvalidStatusTransitionError,
    JobNotFoundError,
)
from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
    InvalidDomainTransitionError,
)
from backend.domain.application.enums import ApplicationStatus
from backend.domain.application.repositories import ApplicationRepository
from backend.domain.job.repositories import JobRepository

logger = logging.getLogger(__name__)

MAX_NOTES_LENGTH = 5000


@dataclass(slots=True)
class ApplicationTrackingService:
    """Application orchestration service for candidate Application Tracking.

    Adheres to Clean Architecture:
    - Pure Python application service with zero infrastructure or ORM dependencies.
    - Enforces Candidate User scoping on all queries and mutations.
    - Enforces domain status transition state machine.
    - Manages application lifecycle and transition history audit logs.
    """

    app_repo: ApplicationRepository
    job_repo: JobRepository

    async def track_application(
        self,
        user_id: uuid.UUID,
        job_id: uuid.UUID,
        status: ApplicationStatus = ApplicationStatus.INTERESTED,
        notes: str | None = None,
    ) -> Application:
        """Track a job application for the authenticated user.

        Verifies that the canonical job exists and has not already been tracked
        by the user.
        """
        # 1. Verify referenced job exists
        job = await self.job_repo.get_by_id(job_id)
        if job is None:
            raise JobNotFoundError(f"Job '{job_id}' not found.")

        # 2. Check for duplicate application
        existing = await self.app_repo.get_by_job_and_user(
            job_id=job_id,
            user_id=user_id,
        )
        if existing is not None:
            raise ApplicationAlreadyExistsError(
                f"Job '{job_id}' is already tracked by user '{user_id}'."
            )

        # 3. Validate notes
        cleaned_notes = None
        if notes is not None:
            cleaned_notes = notes.strip()
            if len(cleaned_notes) > MAX_NOTES_LENGTH:
                raise ApplicationValidationError(
                    "Notes exceed maximum allowed length of "
                    f"{MAX_NOTES_LENGTH} characters."
                )
            if not cleaned_notes:
                cleaned_notes = None

        # 4. Construct domain entity and persist
        application = Application(
            job_id=job_id,
            user_id=user_id,
            status=status,
            notes=cleaned_notes,
            job=job,
        )
        saved = await self.app_repo.save(application)
        logger.info(
            "User %s tracked job %s with status %s (app_id: %s)",
            user_id,
            job_id,
            status.value,
            saved.id,
        )
        return saved

    async def list_applications(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Application], int]:
        """List tracked applications with optional status filter and pagination."""
        if limit < 1 or limit > 100:
            raise ApplicationValidationError("Limit must be between 1 and 100.")
        if offset < 0:
            raise ApplicationValidationError("Offset must be non-negative.")

        items = await self.app_repo.list_by_user_id(
            user_id=user_id,
            status=status,
            limit=limit,
            offset=offset,
        )
        total = await self.app_repo.count_by_user_id(
            user_id=user_id,
            status=status,
        )
        return items, total

    async def get_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Application:
        """Retrieve a specific application scoped strictly to the authenticated user."""
        app = await self.app_repo.get_by_id_and_user_id(
            application_id=application_id,
            user_id=user_id,
            for_update=for_update,
        )
        if app is None:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")
        return app

    async def update_status(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        new_status: ApplicationStatus,
    ) -> Application:
        """Update an application's status according to domain transition rules.

        Logs an entry in the application status transition history.
        """
        app = await self.get_application(
            application_id=application_id, user_id=user_id, for_update=True
        )

        if new_status == app.status:
            raise InvalidStatusTransitionError(
                f"Application is already in status '{new_status.value}'.",
                details={
                    "current_status": app.status.value,
                    "requested_status": new_status.value,
                },
            )

        try:
            history_entry = app.transition_to(new_status)
        except InvalidDomainTransitionError as err:
            raise InvalidStatusTransitionError(
                str(err),
                details={
                    "current_status": app.status.value,
                    "requested_status": new_status.value,
                },
            ) from err

        saved_app = await self.app_repo.save(app)
        await self.app_repo.add_status_history(history_entry)
        saved_app.status_history = app.status_history

        logger.info(
            "Application %s transitioned from %s to %s by user %s",
            application_id,
            history_entry.from_status.value,
            new_status.value,
            user_id,
        )
        return saved_app

    async def update_notes(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        notes: str | None,
    ) -> Application:
        """Update candidate notes on an application."""
        app = await self.get_application(
            application_id=application_id, user_id=user_id, for_update=True
        )

        cleaned_notes = None
        if notes is not None:
            cleaned_notes = notes.strip()
            if len(cleaned_notes) > MAX_NOTES_LENGTH:
                raise ApplicationValidationError(
                    "Notes exceed maximum allowed length of "
                    f"{MAX_NOTES_LENGTH} characters."
                )
            if not cleaned_notes:
                cleaned_notes = None

        app.update_notes(cleaned_notes)
        saved = await self.app_repo.save(app)
        logger.info(
            "Application %s notes updated by user %s",
            application_id,
            user_id,
        )
        return saved

    async def delete_application(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Stop tracking an application and remove it completely."""
        # Ensure user ownership first
        await self.get_application(application_id=application_id, user_id=user_id)

        deleted = await self.app_repo.delete(
            application_id=application_id,
            user_id=user_id,
        )
        logger.info(
            "Application %s removed by user %s (success: %s)",
            application_id,
            user_id,
            deleted,
        )
        return deleted

    async def get_status_history(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ApplicationStatusHistory]:
        """Retrieve the chronological status history for an owned application."""
        # Ensure user ownership first
        await self.get_application(application_id=application_id, user_id=user_id)

        return await self.app_repo.list_status_history(application_id=application_id)
