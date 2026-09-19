"""CV domain enums."""

import enum


class CVStatus(enum.StrEnum):
    """Lifecycle status of an uploaded CV."""

    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
