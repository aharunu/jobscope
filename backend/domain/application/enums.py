"""Application domain enums."""

import enum


class ApplicationStatus(enum.StrEnum):
    """Lifecycle tracking status of a job application."""

    INTERESTED = "INTERESTED"
    APPLYING = "APPLYING"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
