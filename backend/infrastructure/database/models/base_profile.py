"""Base profile and related child ORM persistence models."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from backend.infrastructure.database.models.search_profile import (
        SearchProfileModel,
    )
    from backend.infrastructure.database.models.user import UserModel


class BaseProfileModel(BaseModel):
    """SQLAlchemy ORM model for the base_profiles table."""

    __tablename__ = "base_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="base_profiles",
    )
    search_profiles: Mapped[list[SearchProfileModel]] = relationship(
        "SearchProfileModel",
        back_populates="base_profile",
        cascade="all, delete-orphan",
    )
    skills: Mapped[list[ProfileSkillModel]] = relationship(
        "ProfileSkillModel",
        back_populates="base_profile",
        cascade="all, delete-orphan",
    )
    experiences: Mapped[list[ProfileExperienceModel]] = relationship(
        "ProfileExperienceModel",
        back_populates="base_profile",
        cascade="all, delete-orphan",
    )
    educations: Mapped[list[ProfileEducationModel]] = relationship(
        "ProfileEducationModel",
        back_populates="base_profile",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[ProfileProjectModel]] = relationship(
        "ProfileProjectModel",
        back_populates="base_profile",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> BaseProfile:
        """Convert ORM model to domain entity."""
        return BaseProfile(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            summary=self.summary,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, base_profile: BaseProfile) -> BaseProfileModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": base_profile.id,
            "user_id": base_profile.user_id,
            "name": base_profile.name,
            "summary": base_profile.summary,
        }
        if base_profile.created_at is not None:
            kwargs["created_at"] = base_profile.created_at
        if base_profile.updated_at is not None:
            kwargs["updated_at"] = base_profile.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<BaseProfileModel id={self.id} name={self.name!r}>"


class ProfileSkillModel(BaseModel):
    """SQLAlchemy ORM model for the profile_skills table."""

    __tablename__ = "profile_skills"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    years_of_experience: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 1),
        nullable=True,
    )
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationship
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="skills",
    )

    def to_domain(self) -> ProfileSkill:
        """Convert ORM model to domain entity."""
        return ProfileSkill(
            id=self.id,
            base_profile_id=self.base_profile_id,
            name=self.name,
            category=self.category,
            years_of_experience=self.years_of_experience,
            level=self.level,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, skill: ProfileSkill) -> ProfileSkillModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": skill.id,
            "base_profile_id": skill.base_profile_id,
            "name": skill.name,
            "category": skill.category,
            "years_of_experience": skill.years_of_experience,
            "level": skill.level,
        }
        if skill.created_at is not None:
            kwargs["created_at"] = skill.created_at
        if skill.updated_at is not None:
            kwargs["updated_at"] = skill.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<ProfileSkillModel id={self.id} name={self.name!r}>"


class ProfileExperienceModel(BaseModel):
    """SQLAlchemy ORM model for the profile_experiences table."""

    __tablename__ = "profile_experiences"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=sa.text("false"),
        nullable=False,
    )
    skills_used: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )

    # Relationship
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="experiences",
    )

    def to_domain(self) -> ProfileExperience:
        """Convert ORM model to domain entity."""
        return ProfileExperience(
            id=self.id,
            base_profile_id=self.base_profile_id,
            company=self.company,
            title=self.title,
            start_date=self.start_date,
            description=self.description,
            end_date=self.end_date,
            is_current=self.is_current,
            skills_used=list(self.skills_used) if self.skills_used else [],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, exp: ProfileExperience) -> ProfileExperienceModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": exp.id,
            "base_profile_id": exp.base_profile_id,
            "company": exp.company,
            "title": exp.title,
            "start_date": exp.start_date,
            "description": exp.description,
            "end_date": exp.end_date,
            "is_current": exp.is_current,
            "skills_used": exp.skills_used,
        }
        if exp.created_at is not None:
            kwargs["created_at"] = exp.created_at
        if exp.updated_at is not None:
            kwargs["updated_at"] = exp.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<ProfileExperienceModel id={self.id} company={self.company!r}>"


class ProfileEducationModel(BaseModel):
    """SQLAlchemy ORM model for the profile_educations table."""

    __tablename__ = "profile_educations"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(100), nullable=False)
    field_of_study: Mapped[str] = mapped_column(String(255), nullable=False)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="educations",
    )

    def to_domain(self) -> ProfileEducation:
        """Convert ORM model to domain entity."""
        return ProfileEducation(
            id=self.id,
            base_profile_id=self.base_profile_id,
            school=self.school,
            degree=self.degree,
            field_of_study=self.field_of_study,
            start_year=self.start_year,
            end_year=self.end_year,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, edu: ProfileEducation) -> ProfileEducationModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": edu.id,
            "base_profile_id": edu.base_profile_id,
            "school": edu.school,
            "degree": edu.degree,
            "field_of_study": edu.field_of_study,
            "start_year": edu.start_year,
            "end_year": edu.end_year,
        }
        if edu.created_at is not None:
            kwargs["created_at"] = edu.created_at
        if edu.updated_at is not None:
            kwargs["updated_at"] = edu.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<ProfileEducationModel id={self.id} school={self.school!r}>"


class ProfileProjectModel(BaseModel):
    """SQLAlchemy ORM model for the profile_projects table."""

    __tablename__ = "profile_projects"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_used: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=sa.text("'[]'::jsonb"),
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="projects",
    )

    def to_domain(self) -> ProfileProject:
        """Convert ORM model to domain entity."""
        return ProfileProject(
            id=self.id,
            base_profile_id=self.base_profile_id,
            title=self.title,
            description=self.description,
            skills_used=list(self.skills_used) if self.skills_used else [],
            url=self.url,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, proj: ProfileProject) -> ProfileProjectModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": proj.id,
            "base_profile_id": proj.base_profile_id,
            "title": proj.title,
            "description": proj.description,
            "skills_used": proj.skills_used,
            "url": proj.url,
        }
        if proj.created_at is not None:
            kwargs["created_at"] = proj.created_at
        if proj.updated_at is not None:
            kwargs["updated_at"] = proj.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<ProfileProjectModel id={self.id} title={self.title!r}>"
