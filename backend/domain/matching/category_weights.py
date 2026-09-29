"""Roadmap-defined deterministic category weights for job matching."""

from __future__ import annotations

from decimal import Decimal

# Roadmap-defined deterministic weights summing to 100% (1.00)
ROLE_WEIGHT = Decimal("0.20")
SKILLS_WEIGHT = Decimal("0.30")
EXPERIENCE_WEIGHT = Decimal("0.20")
LOCATION_WORK_MODE_WEIGHT = Decimal("0.10")
EDUCATION_WEIGHT = Decimal("0.10")
OTHER_WEIGHT = Decimal("0.10")

CATEGORY_WEIGHTS: dict[str, Decimal] = {
    "ROLE": ROLE_WEIGHT,
    "SKILLS": SKILLS_WEIGHT,
    "EXPERIENCE": EXPERIENCE_WEIGHT,
    "LOCATION_WORK_MODE": LOCATION_WORK_MODE_WEIGHT,
    "EDUCATION": EDUCATION_WEIGHT,
    "OTHER": OTHER_WEIGHT,
}
