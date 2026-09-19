"""Search profile domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class SearchProfile:
    """Domain entity representing a configured job search target.

    Built on top of a Base Profile.
    Pure Python representation independent of persistence or ORM frameworks.
    """

    base_profile_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    target_roles: list[str] = field(default_factory=list)
    seniority: str | None = None
    target_skills: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    work_modes: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
