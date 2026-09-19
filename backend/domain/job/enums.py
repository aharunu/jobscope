"""Job domain enums."""

import enum


class JobStatus(enum.StrEnum):
    """Lifecycle status of a canonical job posting."""

    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class RequirementType(enum.StrEnum):
    """Categorical classification of a job requirement."""

    SKILL = "SKILL"
    EXPERIENCE = "EXPERIENCE"
    EDUCATION = "EDUCATION"
    LANGUAGE = "LANGUAGE"
    CERTIFICATION = "CERTIFICATION"
    OTHER = "OTHER"


class RequirementLevel(enum.StrEnum):
    """Necessity level of a job requirement."""

    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
