"""Shared validation for manually supplied profile data; no sentinel dates."""

from datetime import date
from decimal import Decimal

from backend.application.profile_management.exceptions import ProfileValidationError

MIN_EXPERIENCE_DATE = date(1900, 1, 1)
MAX_SKILL_YEARS = Decimal("50")


def validate_experience_dates(start: date | None, end: date | None) -> None:
    if start is None:
        raise ProfileValidationError("Start date is required")
    today = date.today()
    if start < MIN_EXPERIENCE_DATE:
        raise ProfileValidationError("Start date must be on or after 1900-01-01")
    if start > today:
        raise ProfileValidationError("Start date cannot be in the future")
    if end is not None:
        if end < start:
            raise ProfileValidationError("End date cannot precede start date")
        if end > today:
            raise ProfileValidationError("End date cannot be in the future")


def validate_skill_years(years: Decimal | None) -> None:
    if years is not None and years.is_finite() and years < 0:
        raise ProfileValidationError("Years of experience cannot be negative")
    if years is not None and (
        not years.is_finite() or not 0 <= years <= MAX_SKILL_YEARS
    ):
        raise ProfileValidationError("Years of experience must be between 0 and 50")
