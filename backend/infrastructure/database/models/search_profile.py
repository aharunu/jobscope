"""Search profile ORM persistence model."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.search_profile.entities import SearchProfile
from backend.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from backend.infrastructure.database.models.base_profile import (
        BaseProfileModel,
    )


class SearchProfileModel(BaseModel):
    """SQLAlchemy ORM model for the search_profiles table."""

    __tablename__ = "search_profiles"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    target_roles: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_skills: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    locations: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    work_modes: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    industries: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    # Relationship
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="search_profiles",
    )

    def to_domain(self) -> SearchProfile:
        """Convert ORM model to domain entity."""
        return SearchProfile(
            id=self.id,
            base_profile_id=self.base_profile_id,
            name=self.name,
            target_roles=list(self.target_roles) if self.target_roles else [],
            seniority=self.seniority,
            target_skills=list(self.target_skills) if self.target_skills else [],
            locations=list(self.locations) if self.locations else [],
            work_modes=list(self.work_modes) if self.work_modes else [],
            industries=list(self.industries) if self.industries else [],
            salary_min=self.salary_min,
            salary_max=self.salary_max,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, search_profile: SearchProfile) -> SearchProfileModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": search_profile.id,
            "base_profile_id": search_profile.base_profile_id,
            "name": search_profile.name,
            "target_roles": search_profile.target_roles,
            "seniority": search_profile.seniority,
            "target_skills": search_profile.target_skills,
            "locations": search_profile.locations,
            "work_modes": search_profile.work_modes,
            "industries": search_profile.industries,
            "salary_min": search_profile.salary_min,
            "salary_max": search_profile.salary_max,
        }
        if search_profile.created_at is not None:
            kwargs["created_at"] = search_profile.created_at
        if search_profile.updated_at is not None:
            kwargs["updated_at"] = search_profile.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<SearchProfileModel id={self.id} name={self.name!r}>"
