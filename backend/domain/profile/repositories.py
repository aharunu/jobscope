"""Base profile domain repository protocols."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)


@runtime_checkable
class BaseProfileRepository(Protocol):
    """Protocol defining persistence operations for BaseProfile domain entities."""

    async def get_by_id(self, profile_id: uuid.UUID) -> BaseProfile | None:
        """Retrieve a base profile by ID with child collections eagerly loaded."""
        ...

    async def get_by_user_id(self, user_id: uuid.UUID) -> BaseProfile | None:
        """Retrieve a base profile by owning user ID with child collections loaded."""
        ...

    async def save(self, profile: BaseProfile) -> BaseProfile:
        """Persist or update a base profile entity."""
        ...


@runtime_checkable
class ProfileSkillRepository(Protocol):
    """Protocol defining persistence operations for candidate ProfileSkill entities."""

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileSkill]:
        """List all skills belonging to a given base profile."""
        ...

    async def get_by_id_and_profile_id(
        self, skill_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileSkill | None:
        """Retrieve a skill scoped to a specific base profile."""
        ...

    async def save(self, skill: ProfileSkill) -> ProfileSkill:
        """Persist or update a skill entity."""
        ...

    async def delete(self, skill_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete a skill scoped to a specific base profile. Returns True if deleted."""
        ...


@runtime_checkable
class ProfileExperienceRepository(Protocol):
    """Protocol for candidate ProfileExperience entity persistence."""

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileExperience]:
        """List all experiences belonging to a given base profile."""
        ...

    async def get_by_id_and_profile_id(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileExperience | None:
        """Retrieve an experience scoped to a specific base profile."""
        ...

    async def save(self, experience: ProfileExperience) -> ProfileExperience:
        """Persist or update an experience entity."""
        ...

    async def delete(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        """Delete an experience scoped to a base profile. Returns True if deleted."""
        ...


@runtime_checkable
class ProfileEducationRepository(Protocol):
    """Protocol for candidate ProfileEducation entity persistence."""

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileEducation]:
        """List all education records belonging to a given base profile."""
        ...

    async def get_by_id_and_profile_id(
        self, education_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileEducation | None:
        """Retrieve an education record scoped to a specific base profile."""
        ...

    async def save(self, education: ProfileEducation) -> ProfileEducation:
        """Persist or update an education entity."""
        ...

    async def delete(self, education_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete an education record. Returns True if deleted."""
        ...


@runtime_checkable
class ProfileProjectRepository(Protocol):
    """Protocol for candidate ProfileProject entity persistence."""

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileProject]:
        """List all project portfolio items belonging to a given base profile."""
        ...

    async def get_by_id_and_profile_id(
        self, project_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileProject | None:
        """Retrieve a project scoped to a specific base profile."""
        ...

    async def save(self, project: ProfileProject) -> ProfileProject:
        """Persist or update a project entity."""
        ...

    async def delete(self, project_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        """Delete a project scoped to a base profile. Returns True if deleted."""
        ...
