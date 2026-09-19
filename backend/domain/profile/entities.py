"""Profile domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


@dataclass(slots=True)
class BaseProfile:
    """Domain entity representing a candidate's stable career profile.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    user_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    summary: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ProfileSkill:
    """Domain entity representing an individual skill linked to a base profile."""

    base_profile_id: uuid.UUID
    name: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    category: str | None = None
    years_of_experience: Decimal | None = None
    level: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ProfileExperience:
    """Domain entity for work experience linked to a base profile."""

    base_profile_id: uuid.UUID
    company: str
    title: str
    start_date: date
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str | None = None
    end_date: date | None = None
    is_current: bool = False
    skills_used: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ProfileEducation:
    """Domain entity representing educational background linked to a base profile."""

    base_profile_id: uuid.UUID
    school: str
    degree: str
    field_of_study: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    start_year: int | None = None
    end_year: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ProfileProject:
    """Domain entity representing a project portfolio item linked to a base profile."""

    base_profile_id: uuid.UUID
    title: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    description: str | None = None
    skills_used: list[str] = field(default_factory=list)
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
