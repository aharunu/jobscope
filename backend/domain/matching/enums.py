"""Matching domain enums."""

import enum


class MatchStatus(enum.StrEnum):
    """Evaluation status of a job requirement match."""

    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    NOT_MATCHED = "NOT_MATCHED"
    UNKNOWN = "UNKNOWN"
