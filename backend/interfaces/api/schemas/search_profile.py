"""Pydantic schemas for Search Profile API requests and responses."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SearchProfileResponse(BaseModel):
    """Schema representing a SearchProfile response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    base_profile_id: uuid.UUID
    name: str
    target_roles: list[str] = Field(default_factory=list)
    seniority: str | None = None
    target_skills: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    work_modes: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


SALARY_UPPER_BOUND = Decimal("9999999999.99")
MAX_LIST_ITEMS = 50
MAX_ITEM_LENGTH = 150


def _validate_string_list_elements(name: str, items: list[str] | None) -> None:
    """Ensure no string item in a list exceeds the maximum allowable length."""
    if items is not None:
        for item in items:
            if len(item) > MAX_ITEM_LENGTH:
                raise ValueError(
                    f"Item in '{name}' exceeds limit of {MAX_ITEM_LENGTH} characters"
                )


class SearchProfileCreateRequest(BaseModel):
    """Request payload to create a new search profile."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="Search profile name or label",
    )
    target_roles: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Target job titles or roles",
    )
    seniority: str | None = Field(
        default=None,
        max_length=50,
        description="Desired seniority level (e.g. junior, mid, senior, lead)",
    )
    target_skills: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Keywords or skills sought",
    )
    locations: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Target geographic locations",
    )
    work_modes: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Preferred work modes (e.g. remote, hybrid, on-site)",
    )
    industries: list[str] = Field(
        default_factory=list,
        max_length=MAX_LIST_ITEMS,
        description="Preferred industries",
    )
    salary_min: Decimal | None = Field(
        default=None,
        ge=0,
        le=SALARY_UPPER_BOUND,
        description="Minimum desired salary",
    )
    salary_max: Decimal | None = Field(
        default=None,
        ge=0,
        le=SALARY_UPPER_BOUND,
        description="Maximum desired salary",
    )

    @model_validator(mode="after")
    def validate_create_fields(self) -> SearchProfileCreateRequest:
        if not self.name.strip():
            raise ValueError("Search profile name cannot be empty or whitespace only")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Minimum salary cannot exceed maximum salary")
        _validate_string_list_elements("target_roles", self.target_roles)
        _validate_string_list_elements("target_skills", self.target_skills)
        _validate_string_list_elements("locations", self.locations)
        _validate_string_list_elements("work_modes", self.work_modes)
        _validate_string_list_elements("industries", self.industries)
        return self


class SearchProfileUpdateRequest(BaseModel):
    """Request payload to partially update a search profile."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
        description="Updated name",
    )
    target_roles: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated target roles",
    )
    seniority: str | None = Field(
        default=None,
        max_length=50,
        description="Updated seniority level",
    )
    target_skills: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated target skills",
    )
    locations: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated locations",
    )
    work_modes: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated work modes",
    )
    industries: list[str] | None = Field(
        default=None,
        max_length=MAX_LIST_ITEMS,
        description="Updated industries",
    )
    salary_min: Decimal | None = Field(
        default=None,
        ge=0,
        le=SALARY_UPPER_BOUND,
        description="Updated minimum salary",
    )
    salary_max: Decimal | None = Field(
        default=None,
        ge=0,
        le=SALARY_UPPER_BOUND,
        description="Updated maximum salary",
    )

    @model_validator(mode="after")
    def validate_update_fields(self) -> SearchProfileUpdateRequest:
        if self.name is not None and not self.name.strip():
            raise ValueError("Search profile name cannot be empty or whitespace only")
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Minimum salary cannot exceed maximum salary")
        _validate_string_list_elements("target_roles", self.target_roles)
        _validate_string_list_elements("target_skills", self.target_skills)
        _validate_string_list_elements("locations", self.locations)
        _validate_string_list_elements("work_modes", self.work_modes)
        _validate_string_list_elements("industries", self.industries)
        return self
