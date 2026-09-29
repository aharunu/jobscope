"""Domain and application exceptions for the matching subsystem."""

from __future__ import annotations


class MatchingError(Exception):
    """Base exception for matching application operations."""


class JobNotFoundError(MatchingError):
    """Raised when the specified Job entity does not exist."""


class SearchProfileNotFoundError(MatchingError):
    """Raised when the specified SearchProfile entity does not exist."""


class BaseProfileNotFoundError(MatchingError):
    """Raised when the related BaseProfile entity does not exist."""
