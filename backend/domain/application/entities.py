"""Application domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from backend.domain.application.enums import ApplicationStatus


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
