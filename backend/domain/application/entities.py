"""Application domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.domain.application.enums import ApplicationStatus

if TYPE_CHECKING:
    from backend.domain.job.entities import Job


VALID_STATUS_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.INTERESTED: {
        ApplicationStatus.APPLYING,
        ApplicationStatus.APPLIED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.APPLYING: {
        ApplicationStatus.INTERESTED,
        ApplicationStatus.APPLIED,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.APPLIED: {
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.INTERVIEW: {
        ApplicationStatus.APPLIED,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.OFFER: {
        ApplicationStatus.REJECTED,
    },
    ApplicationStatus.REJECTED: {
        ApplicationStatus.INTERESTED,
        ApplicationStatus.APPLYING,
        ApplicationStatus.APPLIED,
        ApplicationStatus.INTERVIEW,
    },
}


class InvalidDomainTransitionError(ValueError):
    """Domain exception raised when an invalid status transition is attempted."""

    def __init__(
        self,
        from_status: ApplicationStatus,
        to_status: ApplicationStatus,
    ) -> None:
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(
            f"Cannot transition application status from '{from_status.value}' "
            f"to '{to_status.value}'."
        )


@dataclass(slots=True)
class Application:
    """Domain entity representing a user's tracked application for a job.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    job_id: uuid.UUID
    user_id: uuid.UUID
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ApplicationStatus = ApplicationStatus.INTERESTED
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    job: Job | None = None
    status_history: list[ApplicationStatusHistory] = field(default_factory=list)

    def can_transition_to(self, new_status: ApplicationStatus) -> bool:
        """Check whether transition to target status is permitted by domain rules."""
        if new_status == self.status:
            return False
        allowed = VALID_STATUS_TRANSITIONS.get(self.status, set())
        return new_status in allowed

    def transition_to(
        self,
        new_status: ApplicationStatus,
        changed_at: datetime | None = None,
    ) -> ApplicationStatusHistory:
        """Transition application to a new status and record the status history entry.

        Raises InvalidDomainTransitionError if the requested transition is illegal.
        """
        if new_status == self.status:
            raise InvalidDomainTransitionError(self.status, new_status)

        if not self.can_transition_to(new_status):
            raise InvalidDomainTransitionError(self.status, new_status)

        old_status = self.status
        transition_time = changed_at or datetime.now(UTC)

        self.status = new_status
        self.updated_at = transition_time

        history_entry = ApplicationStatusHistory(
            application_id=self.id,
            from_status=old_status,
            to_status=new_status,
            changed_at=transition_time,
        )
        self.status_history.append(history_entry)
        return history_entry

    def update_notes(
        self,
        new_notes: str | None,
        updated_at: datetime | None = None,
    ) -> None:
        """Update candidate private notes and touch updated_at."""
        self.notes = new_notes
        self.updated_at = updated_at or datetime.now(UTC)


@dataclass(slots=True)
class ApplicationStatusHistory:
    """Domain entity logging a historical status transition for an application.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    application_id: uuid.UUID
    from_status: ApplicationStatus
    to_status: ApplicationStatus
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    changed_at: datetime | None = None
