"""Application service for Search Profile management.

Enforces Candidate User -> BaseProfile -> SearchProfile ownership chain.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from backend.application.profile_management.exceptions import (
    ProfileValidationError,
    SearchProfileNotFoundError,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository

logger = logging.getLogger(__name__)


SALARY_MAX_LIMIT = Decimal("9999999999.99")
MAX_LIST_ITEMS = 50
MAX_ITEM_LENGTH = 150


def _clean_string_list(items: list[str] | None, field_name: str = "list") -> list[str]:
    """Strip whitespace and validate list length and item lengths.

    Raises ProfileValidationError if length constraints are violated,
    preventing silent data loss.
    """
    if not items:
        return []
    if len(items) > MAX_LIST_ITEMS:
        raise ProfileValidationError(
            f"'{field_name}' cannot contain more than {MAX_LIST_ITEMS} items"
        )
    cleaned = []
    for item in items:
        stripped = item.strip() if item else ""
        if len(stripped) > MAX_ITEM_LENGTH:
            raise ProfileValidationError(
                f"Item in '{field_name}' exceeds limit of {MAX_ITEM_LENGTH} characters"
            )
        if stripped:
            cleaned.append(stripped)
    return cleaned


@dataclass(slots=True)
class SearchProfileService:
    """Application orchestration service for candidate Search Profiles.

    Ensures strict scoped access: users can only view, create, update,
    or delete search profiles that belong to their own BaseProfile.
    """

    base_profile_repo: BaseProfileRepository
    search_profile_repo: SearchProfileRepository

    async def _resolve_base_profile(self, user_id: uuid.UUID) -> BaseProfile:
        """Fetch caller's base profile or auto-provision one if missing."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self.base_profile_repo.save(
                BaseProfile(user_id=user_id, name="Candidate Profile")
            )
        return profile

    async def list_search_profiles(self, user_id: uuid.UUID) -> list[SearchProfile]:
        """List all search profiles belonging to the current user's base profile."""
        profile = await self._resolve_base_profile(user_id)
        return await self.search_profile_repo.list_by_base_profile_id(profile.id)

    async def get_search_profile(
        self, user_id: uuid.UUID, search_profile_id: uuid.UUID
    ) -> SearchProfile:
        """Retrieve a search profile ensuring caller ownership."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )

        sp = await self.search_profile_repo.get_by_id_and_base_profile_id(
            search_profile_id=search_profile_id,
            base_profile_id=profile.id,
        )
        if sp is None:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )
        return sp

    async def create_search_profile(
        self,
        user_id: uuid.UUID,
        name: str,
        target_roles: list[str] | None = None,
        seniority: str | None = None,
        target_skills: list[str] | None = None,
        locations: list[str] | None = None,
        work_modes: list[str] | None = None,
        industries: list[str] | None = None,
        salary_min: Decimal | None = None,
        salary_max: Decimal | None = None,
    ) -> SearchProfile:
        """Create and attach a new search profile to caller's base profile."""
        profile = await self._resolve_base_profile(user_id)

        stripped_name = name.strip() if name else ""
        if not stripped_name:
            raise ProfileValidationError("Search profile name cannot be empty")
        if len(stripped_name) > 150:
            raise ProfileValidationError(
                "Search profile name cannot exceed 150 characters"
            )

        if salary_min is not None:
            if salary_min < Decimal("0"):
                raise ProfileValidationError("Minimum salary cannot be negative")
            if salary_min > SALARY_MAX_LIMIT:
                raise ProfileValidationError(
                    "Minimum salary cannot exceed maximum allowable limit "
                    f"({SALARY_MAX_LIMIT})"
                )

        if salary_max is not None:
            if salary_max < Decimal("0"):
                raise ProfileValidationError("Maximum salary cannot be negative")
            if salary_max > SALARY_MAX_LIMIT:
                raise ProfileValidationError(
                    "Maximum salary cannot exceed maximum allowable limit "
                    f"({SALARY_MAX_LIMIT})"
                )

        if (
            salary_min is not None
            and salary_max is not None
            and salary_min > salary_max
        ):
            raise ProfileValidationError("Minimum salary cannot exceed maximum salary")

        cleaned_roles = _clean_string_list(target_roles, "target_roles")
        cleaned_seniority = (
            seniority.strip() if seniority and seniority.strip() else None
        )
        cleaned_skills = _clean_string_list(target_skills, "target_skills")
        cleaned_locations = _clean_string_list(locations, "locations")
        cleaned_work_modes = _clean_string_list(work_modes, "work_modes")
        cleaned_industries = _clean_string_list(industries, "industries")

        entity = SearchProfile(
            base_profile_id=profile.id,
            name=stripped_name,
            target_roles=cleaned_roles,
            seniority=cleaned_seniority,
            target_skills=cleaned_skills,
            locations=cleaned_locations,
            work_modes=cleaned_work_modes,
            industries=cleaned_industries,
            salary_min=salary_min,
            salary_max=salary_max,
        )

        saved = await self.search_profile_repo.save(entity)
        logger.info(
            "Created search profile id=%s for user_id=%s (base_profile_id=%s)",
            saved.id,
            user_id,
            profile.id,
        )
        return saved

    async def update_search_profile(
        self,
        user_id: uuid.UUID,
        search_profile_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> SearchProfile:
        """Partially update an existing search profile belonging to caller."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )

        existing = await self.search_profile_repo.get_by_id_and_base_profile_id(
            search_profile_id=search_profile_id,
            base_profile_id=profile.id,
        )
        if existing is None:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )

        updated_name = existing.name
        if "name" in updates:
            raw_name = updates["name"]
            stripped = raw_name.strip() if raw_name else ""
            if not stripped:
                raise ProfileValidationError("Search profile name cannot be empty")
            if len(stripped) > 150:
                raise ProfileValidationError(
                    "Search profile name cannot exceed 150 characters"
                )
            updated_name = stripped

        updated_target_roles = (
            _clean_string_list(updates["target_roles"], "target_roles")
            if "target_roles" in updates
            else existing.target_roles
        )

        updated_seniority = existing.seniority
        if "seniority" in updates:
            raw_sen = updates["seniority"]
            updated_seniority = raw_sen.strip() if raw_sen and raw_sen.strip() else None

        updated_target_skills = (
            _clean_string_list(updates["target_skills"], "target_skills")
            if "target_skills" in updates
            else existing.target_skills
        )

        updated_locations = (
            _clean_string_list(updates["locations"], "locations")
            if "locations" in updates
            else existing.locations
        )

        updated_work_modes = (
            _clean_string_list(updates["work_modes"], "work_modes")
            if "work_modes" in updates
            else existing.work_modes
        )

        updated_industries = (
            _clean_string_list(updates["industries"], "industries")
            if "industries" in updates
            else existing.industries
        )

        updated_salary_min = existing.salary_min
        if "salary_min" in updates:
            raw_min = updates["salary_min"]
            if raw_min is not None:
                if raw_min < Decimal("0"):
                    raise ProfileValidationError("Minimum salary cannot be negative")
                if raw_min > SALARY_MAX_LIMIT:
                    raise ProfileValidationError(
                        "Minimum salary cannot exceed maximum allowable limit "
                        f"({SALARY_MAX_LIMIT})"
                    )
            updated_salary_min = raw_min

        updated_salary_max = existing.salary_max
        if "salary_max" in updates:
            raw_max = updates["salary_max"]
            if raw_max is not None:
                if raw_max < Decimal("0"):
                    raise ProfileValidationError("Maximum salary cannot be negative")
                if raw_max > SALARY_MAX_LIMIT:
                    raise ProfileValidationError(
                        "Maximum salary cannot exceed maximum allowable limit "
                        f"({SALARY_MAX_LIMIT})"
                    )
            updated_salary_max = raw_max

        if (
            updated_salary_min is not None
            and updated_salary_max is not None
            and updated_salary_min > updated_salary_max
        ):
            raise ProfileValidationError("Minimum salary cannot exceed maximum salary")

        updated_entity = SearchProfile(
            id=existing.id,
            base_profile_id=existing.base_profile_id,
            name=updated_name,
            target_roles=updated_target_roles,
            seniority=updated_seniority,
            target_skills=updated_target_skills,
            locations=updated_locations,
            work_modes=updated_work_modes,
            industries=updated_industries,
            salary_min=updated_salary_min,
            salary_max=updated_salary_max,
            created_at=existing.created_at,
        )

        saved = await self.search_profile_repo.save(updated_entity)
        logger.info(
            "Updated search profile id=%s for user_id=%s",
            saved.id,
            user_id,
        )
        return saved

    async def delete_search_profile(
        self, user_id: uuid.UUID, search_profile_id: uuid.UUID
    ) -> None:
        """Delete an existing search profile belonging to caller."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )

        deleted = await self.search_profile_repo.delete(
            search_profile_id=search_profile_id,
            base_profile_id=profile.id,
        )
        if not deleted:
            raise SearchProfileNotFoundError(
                f"Search profile '{search_profile_id}' not found"
            )
        logger.info(
            "Deleted search profile id=%s for user_id=%s",
            search_profile_id,
            user_id,
        )
