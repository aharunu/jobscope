"""Job domain enums."""

import enum


class JobStatus(enum.StrEnum):
    """Lifecycle status of a canonical job posting."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
