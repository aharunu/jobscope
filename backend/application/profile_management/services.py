"""Application services for Base Profile management."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from backend.application.profile_management.exceptions import (
    ProfileNotFoundError,
    ProfileValidationError,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.profile.repositories import BaseProfileRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BaseProfileService:
    """Application orchestration service for candidate base profiles."""

    base_profile_repo: BaseProfileRepository

    async def get_or_create_profile(
        self,
        user_id: uuid.UUID,
        default_name: str = "Candidate Profile",
    ) -> BaseProfile:
        """Retrieve the base profile for a user, or auto-provision one if missing."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is not None:
            return profile

        logger.info("Auto-provisioning BaseProfile for user_id=%s", user_id)
        new_profile = BaseProfile(
            user_id=user_id,
            name=default_name,
        )
        return await self.base_profile_repo.save(new_profile)

    async def get_profile(self, user_id: uuid.UUID) -> BaseProfile:
        """Retrieve the base profile for a user, raising if not found."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError(f"Base profile for user '{user_id}' not found")
        return profile

    async def update_profile(
        self,
        user_id: uuid.UUID,
        updates: dict[str, Any] | None = None,
        name: str | None = None,
        summary: str | None = None,
    ) -> BaseProfile:
        """Partially update root metadata for a user's base profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileNotFoundError(f"Base profile for user '{user_id}' not found")

        updated_name = profile.name
        updated_summary = profile.summary

        if updates is not None:
            if "name" in updates:
                raw_name = updates["name"]
                stripped = raw_name.strip() if raw_name else ""
                if not stripped:
                    raise ProfileValidationError("Profile name cannot be empty")
                updated_name = stripped

            if "summary" in updates:
                raw_summary = updates["summary"]
                if raw_summary is None:
                    updated_summary = None
                else:
                    stripped_summary = raw_summary.strip()
                    updated_summary = stripped_summary if stripped_summary else None
        else:
            if name is not None:
                stripped = name.strip()
                if not stripped:
                    raise ProfileValidationError("Profile name cannot be empty")
                updated_name = stripped

            if summary is not None:
                stripped_summary = summary.strip()
                updated_summary = stripped_summary if stripped_summary else None

        # Construct updated domain entity preserving child collections
        updated_profile = BaseProfile(
            id=profile.id,
            user_id=profile.user_id,
            name=updated_name,
            summary=updated_summary,
            created_at=profile.created_at,
            skills=profile.skills,
            experiences=profile.experiences,
            educations=profile.educations,
            projects=profile.projects,
        )
        persisted = await self.base_profile_repo.save(updated_profile)
        logger.info("Updated BaseProfile metadata for user_id=%s", user_id)
        return persisted
