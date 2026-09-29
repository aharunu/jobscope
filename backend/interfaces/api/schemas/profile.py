"""Pydantic schemas for Base Profile and child career components."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ============================================================================
# Response Schemas
# ============================================================================


class ProfileSkillResponse(BaseModel):
    """Schema representing an individual skill response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_profile_id: uuid.UUID
    name: str
    category: str | None = None
    years_of_experience: Decimal | None = None
    level: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Alias for backward compatibility
ProfileSkillSummaryResponse = ProfileSkillResponse


class ProfileExperienceResponse(BaseModel):
    """Schema representing an individual work experience response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_profile_id: uuid.UUID
    company: str
    title: str
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    skills_used: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Alias for backward compatibility
ProfileExperienceSummaryResponse = ProfileExperienceResponse


class ProfileEducationResponse(BaseModel):
    """Schema representing educational background response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_profile_id: uuid.UUID
    school: str
    degree: str
    field_of_study: str
    start_year: int | None = None
    end_year: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Alias for backward compatibility
ProfileEducationSummaryResponse = ProfileEducationResponse


class ProfileProjectResponse(BaseModel):
    """Schema representing a portfolio project response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_profile_id: uuid.UUID
    title: str
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)
    url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# Alias for backward compatibility
ProfileProjectSummaryResponse = ProfileProjectResponse


class BaseProfileResponse(BaseModel):
    """Full candidate Base Profile representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    summary: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    skills: list[ProfileSkillResponse] = Field(default_factory=list)
    experiences: list[ProfileExperienceResponse] = Field(default_factory=list)
    educations: list[ProfileEducationResponse] = Field(default_factory=list)
    projects: list[ProfileProjectResponse] = Field(default_factory=list)


# ============================================================================
# Root Profile Requests
# ============================================================================


class BaseProfileUpdateRequest(BaseModel):
    """Request payload for partially updating Base Profile root metadata."""

    name: str | None = Field(
        default=None,
        description="Updated candidate display name",
        min_length=1,
        max_length=255,
    )
    summary: str | None = Field(
        default=None,
        description="Candidate professional bio or summary",
    )


# ============================================================================
# Child Collection Requests (Create / Update)
# ============================================================================


class ProfileSkillCreateRequest(BaseModel):
    """Request payload to create a new profile skill."""

    name: str = Field(..., min_length=1, max_length=150, description="Skill name")
    category: str | None = Field(
        default=None, max_length=100, description="Domain category"
    )
    years_of_experience: Decimal | None = Field(
        default=None, ge=0, le=99.9, description="Years practiced"
    )
    level: str | None = Field(
        default=None, max_length=50, description="Proficiency level"
    )


class ProfileSkillUpdateRequest(BaseModel):
    """Request payload to partially update a profile skill."""

    name: str | None = Field(
        default=None, min_length=1, max_length=150, description="Updated name"
    )
    category: str | None = Field(
        default=None, max_length=100, description="Updated category"
    )
    years_of_experience: Decimal | None = Field(
        default=None, ge=0, le=99.9, description="Updated years"
    )
    level: str | None = Field(default=None, max_length=50, description="Updated level")


MAX_LIST_ITEMS = 50
MAX_ITEM_LENGTH = 150


def _validate_skills_used(skills: list[str] | None) -> None:
    """Ensure no individual skill item exceeds the maximum allowable length."""
    if skills is not None:
        for item in skills:
            if len(item) > MAX_ITEM_LENGTH:
                raise ValueError(
                    f"Item in 'skills_used' exceeds maximum length "
                    f"of {MAX_ITEM_LENGTH} characters"
                )


class ProfileExperienceCreateRequest(BaseModel):
    """Request payload to create a work experience entry."""

    company: str = Field(..., min_length=1, max_length=255, description="Employer name")
    title: str = Field(..., min_length=1, max_length=255, description="Job title")
    start_date: date = Field(..., description="Start date")
    end_date: date | None = Field(default=None, description="End date (if completed)")
    is_current: bool = Field(default=False, description="Whether currently employed")
    description: str | None = Field(
        default=None, description="Role summary/achievements"
    )
    skills_used: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Associated skills",
    )

    @model_validator(mode="after")
    def validate_experience_create(self) -> ProfileExperienceCreateRequest:
        _validate_skills_used(self.skills_used)
        return self


class ProfileExperienceUpdateRequest(BaseModel):
    """Request payload to partially update a work experience entry."""

    company: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated employer"
    )
    title: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated title"
    )
    start_date: date | None = Field(default=None, description="Updated start date")
    end_date: date | None = Field(default=None, description="Updated end date")
    is_current: bool | None = Field(default=None, description="Updated current status")
    description: str | None = Field(default=None, description="Updated description")
    skills_used: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated skills",
    )

    @model_validator(mode="after")
    def validate_experience_update(self) -> ProfileExperienceUpdateRequest:
        _validate_skills_used(self.skills_used)
        return self


class ProfileEducationCreateRequest(BaseModel):
    """Request payload to create an education record."""

    school: str = Field(
        ..., min_length=1, max_length=255, description="School / University"
    )
    degree: str = Field(
        ..., min_length=1, max_length=100, description="Degree obtained"
    )
    field_of_study: str = Field(
        ..., min_length=1, max_length=255, description="Major / Program"
    )
    start_year: int | None = Field(
        default=None, ge=1900, le=2100, description="Start year"
    )
    end_year: int | None = Field(default=None, ge=1900, le=2100, description="End year")


class ProfileEducationUpdateRequest(BaseModel):
    """Request payload to partially update an education record."""

    school: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated school"
    )
    degree: str | None = Field(
        default=None, min_length=1, max_length=100, description="Updated degree"
    )
    field_of_study: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated field"
    )
    start_year: int | None = Field(
        default=None, ge=1900, le=2100, description="Updated start year"
    )
    end_year: int | None = Field(
        default=None, ge=1900, le=2100, description="Updated end year"
    )


class ProfileProjectCreateRequest(BaseModel):
    """Request payload to create a project portfolio entry."""

    title: str = Field(..., min_length=1, max_length=255, description="Project title")
    description: str | None = Field(default=None, description="Project overview")
    skills_used: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Associated skills",
    )
    url: str | None = Field(default=None, max_length=2048, description="Project URL")

    @model_validator(mode="after")
    def validate_project_create(self) -> ProfileProjectCreateRequest:
        _validate_skills_used(self.skills_used)
        return self


class ProfileProjectUpdateRequest(BaseModel):
    """Request payload to partially update a project portfolio entry."""

    title: str | None = Field(
        default=None, min_length=1, max_length=255, description="Updated title"
    )
    description: str | None = Field(default=None, description="Updated description")
    skills_used: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated skills",
    )
    url: str | None = Field(default=None, max_length=2048, description="Updated URL")

    @model_validator(mode="after")
    def validate_project_update(self) -> ProfileProjectUpdateRequest:
        _validate_skills_used(self.skills_used)
        return self
