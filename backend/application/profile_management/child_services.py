"""Application services for BaseProfile child collections.
Covers Skills, Experiences, Educations, and Projects.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from backend.application.profile_management.exceptions import (
    ProfileEducationNotFoundError,
    ProfileExperienceNotFoundError,
    ProfileProjectNotFoundError,
    ProfileSkillNotFoundError,
    ProfileValidationError,
)
from backend.application.profile_management.validation import (
    validate_experience_dates,
    validate_skill_years,
)
from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.domain.profile.repositories import (
    BaseProfileRepository,
    ProfileEducationRepository,
    ProfileExperienceRepository,
    ProfileProjectRepository,
    ProfileSkillRepository,
)

logger = logging.getLogger(__name__)

MAX_SKILLS_USED = 50
MAX_SKILL_LENGTH = 150


def _clean_and_validate_skills_used(skills_used: list[str] | None) -> list[str]:
    """Strip whitespace and enforce length limits on associated skills."""
    if not skills_used:
        return []
    if len(skills_used) > MAX_SKILLS_USED:
        raise ProfileValidationError(
            f"Cannot associate more than {MAX_SKILLS_USED} skills"
        )
    cleaned = []
    for s in skills_used:
        stripped = s.strip() if s else ""
        if len(stripped) > MAX_SKILL_LENGTH:
            raise ProfileValidationError(
                f"Skill name exceeds maximum length of {MAX_SKILL_LENGTH} characters"
            )
        if stripped:
            cleaned.append(stripped)
    return cleaned


@dataclass(slots=True)
class ProfileSkillService:
    """Application orchestration service for candidate skills."""

    base_profile_repo: BaseProfileRepository
    skill_repo: ProfileSkillRepository

    async def _resolve_base_profile(self, user_id: uuid.UUID) -> BaseProfile:
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self.base_profile_repo.save(
                BaseProfile(user_id=user_id, name="Candidate Profile")
            )
        return profile

    async def list_skills(self, user_id: uuid.UUID) -> list[ProfileSkill]:
        """List all skills belonging to the current user's profile."""
        profile = await self._resolve_base_profile(user_id)
        return await self.skill_repo.list_by_profile_id(profile.id)

    async def create_skill(
        self,
        user_id: uuid.UUID,
        name: str,
        category: str | None = None,
        years_of_experience: Decimal | None = None,
        level: str | None = None,
    ) -> ProfileSkill:
        """Create and attach a new skill to caller's base profile."""
        profile = await self._resolve_base_profile(user_id)

        stripped_name = name.strip() if name else ""
        if not stripped_name:
            raise ProfileValidationError("Skill name cannot be empty")

        validate_skill_years(years_of_experience)

        skill = ProfileSkill(
            base_profile_id=profile.id,
            name=stripped_name,
            category=category.strip() if category and category.strip() else None,
            years_of_experience=years_of_experience,
            level=level.strip() if level and level.strip() else None,
        )
        saved = await self.skill_repo.save(skill)
        logger.info("Created skill id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def update_skill(
        self,
        user_id: uuid.UUID,
        skill_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> ProfileSkill:
        """Partially update an existing skill belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileSkillNotFoundError(f"Skill '{skill_id}' not found")

        existing = await self.skill_repo.get_by_id_and_profile_id(skill_id, profile.id)
        if existing is None:
            raise ProfileSkillNotFoundError(f"Skill '{skill_id}' not found")

        updated_name = existing.name
        if "name" in updates:
            raw_name = updates["name"]
            stripped = raw_name.strip() if raw_name else ""
            if not stripped:
                raise ProfileValidationError("Skill name cannot be empty")
            updated_name = stripped

        updated_category = existing.category
        if "category" in updates:
            raw_cat = updates["category"]
            updated_category = raw_cat.strip() if raw_cat and raw_cat.strip() else None

        updated_years = existing.years_of_experience
        if "years_of_experience" in updates:
            raw_years = updates["years_of_experience"]
            validate_skill_years(raw_years)
            updated_years = raw_years

        updated_level = existing.level
        if "level" in updates:
            raw_lvl = updates["level"]
            updated_level = raw_lvl.strip() if raw_lvl and raw_lvl.strip() else None

        updated_entity = ProfileSkill(
            id=existing.id,
            base_profile_id=existing.base_profile_id,
            name=updated_name,
            category=updated_category,
            years_of_experience=updated_years,
            level=updated_level,
            created_at=existing.created_at,
        )
        saved = await self.skill_repo.save(updated_entity)
        logger.info("Updated skill id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def delete_skill(self, user_id: uuid.UUID, skill_id: uuid.UUID) -> None:
        """Delete an existing skill belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileSkillNotFoundError(f"Skill '{skill_id}' not found")

        deleted = await self.skill_repo.delete(skill_id, profile.id)
        if not deleted:
            raise ProfileSkillNotFoundError(f"Skill '{skill_id}' not found")
        logger.info("Deleted skill id=%s for user_id=%s", skill_id, user_id)


@dataclass(slots=True)
class ProfileExperienceService:
    """Application orchestration service for candidate work experience."""

    base_profile_repo: BaseProfileRepository
    experience_repo: ProfileExperienceRepository

    async def _resolve_base_profile(self, user_id: uuid.UUID) -> BaseProfile:
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self.base_profile_repo.save(
                BaseProfile(user_id=user_id, name="Candidate Profile")
            )
        return profile

    async def list_experiences(self, user_id: uuid.UUID) -> list[ProfileExperience]:
        """List all work experiences belonging to the current user's profile."""
        profile = await self._resolve_base_profile(user_id)
        return await self.experience_repo.list_by_profile_id(profile.id)

    async def create_experience(
        self,
        user_id: uuid.UUID,
        company: str,
        title: str,
        start_date: date,
        end_date: date | None = None,
        is_current: bool = False,
        description: str | None = None,
        skills_used: list[str] | None = None,
    ) -> ProfileExperience:
        """Create and attach a new work experience entry."""
        profile = await self._resolve_base_profile(user_id)

        company_clean = company.strip() if company else ""
        if not company_clean:
            raise ProfileValidationError("Company name cannot be empty")

        title_clean = title.strip() if title else ""
        if not title_clean:
            raise ProfileValidationError("Job title cannot be empty")

        end_date = None if is_current else end_date
        validate_experience_dates(start_date, end_date)

        cleaned_skills = _clean_and_validate_skills_used(skills_used)

        experience = ProfileExperience(
            base_profile_id=profile.id,
            company=company_clean,
            title=title_clean,
            start_date=start_date,
            end_date=end_date if not is_current else None,
            is_current=is_current,
            description=description.strip()
            if description and description.strip()
            else None,
            skills_used=cleaned_skills,
        )
        saved = await self.experience_repo.save(experience)
        logger.info("Created experience id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def update_experience(
        self,
        user_id: uuid.UUID,
        experience_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> ProfileExperience:
        """Partially update an existing experience belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileExperienceNotFoundError(
                f"Experience '{experience_id}' not found"
            )

        existing = await self.experience_repo.get_by_id_and_profile_id(
            experience_id, profile.id
        )
        if existing is None:
            raise ProfileExperienceNotFoundError(
                f"Experience '{experience_id}' not found"
            )

        updated_company = existing.company
        if "company" in updates:
            raw = updates["company"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("Company name cannot be empty")
            updated_company = cleaned

        updated_title = existing.title
        if "title" in updates:
            raw = updates["title"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("Job title cannot be empty")
            updated_title = cleaned

        updated_start = updates.get("start_date", existing.start_date)
        updated_is_current = updates.get("is_current", existing.is_current)
        updated_end = updates.get("end_date", existing.end_date)

        if updated_is_current:
            updated_end = None

        validate_experience_dates(updated_start, updated_end)

        updated_desc = existing.description
        if "description" in updates:
            raw = updates["description"]
            updated_desc = raw.strip() if raw and raw.strip() else None

        updated_skills = existing.skills_used
        if "skills_used" in updates:
            raw_skills = updates["skills_used"]
            updated_skills = _clean_and_validate_skills_used(raw_skills)

        updated_entity = ProfileExperience(
            id=existing.id,
            base_profile_id=existing.base_profile_id,
            company=updated_company,
            title=updated_title,
            start_date=updated_start,
            end_date=updated_end,
            is_current=updated_is_current,
            description=updated_desc,
            skills_used=updated_skills,
            created_at=existing.created_at,
        )
        saved = await self.experience_repo.save(updated_entity)
        logger.info("Updated experience id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def delete_experience(
        self, user_id: uuid.UUID, experience_id: uuid.UUID
    ) -> None:
        """Delete an existing experience belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileExperienceNotFoundError(
                f"Experience '{experience_id}' not found"
            )

        deleted = await self.experience_repo.delete(experience_id, profile.id)
        if not deleted:
            raise ProfileExperienceNotFoundError(
                f"Experience '{experience_id}' not found"
            )
        logger.info("Deleted experience id=%s for user_id=%s", experience_id, user_id)


@dataclass(slots=True)
class ProfileEducationService:
    """Application orchestration service for candidate education history."""

    base_profile_repo: BaseProfileRepository
    education_repo: ProfileEducationRepository

    async def _resolve_base_profile(self, user_id: uuid.UUID) -> BaseProfile:
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self.base_profile_repo.save(
                BaseProfile(user_id=user_id, name="Candidate Profile")
            )
        return profile

    async def list_educations(self, user_id: uuid.UUID) -> list[ProfileEducation]:
        """List all education records belonging to caller's base profile."""
        profile = await self._resolve_base_profile(user_id)
        return await self.education_repo.list_by_profile_id(profile.id)

    async def create_education(
        self,
        user_id: uuid.UUID,
        school: str,
        degree: str,
        field_of_study: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> ProfileEducation:
        """Create and attach a new education record."""
        profile = await self._resolve_base_profile(user_id)

        school_clean = school.strip() if school else ""
        if not school_clean:
            raise ProfileValidationError("School name cannot be empty")

        degree_clean = degree.strip() if degree else ""
        if not degree_clean:
            raise ProfileValidationError("Degree cannot be empty")

        field_clean = field_of_study.strip() if field_of_study else ""
        if not field_clean:
            raise ProfileValidationError("Field of study cannot be empty")

        if start_year is not None and (start_year < 1900 or start_year > 2100):
            raise ProfileValidationError("Start year must be between 1900 and 2100")
        if end_year is not None and (end_year < 1900 or end_year > 2100):
            raise ProfileValidationError("End year must be between 1900 and 2100")
        if start_year is not None and end_year is not None and end_year < start_year:
            raise ProfileValidationError("End year cannot precede start year")

        education = ProfileEducation(
            base_profile_id=profile.id,
            school=school_clean,
            degree=degree_clean,
            field_of_study=field_clean,
            start_year=start_year,
            end_year=end_year,
        )
        saved = await self.education_repo.save(education)
        logger.info("Created education id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def update_education(
        self,
        user_id: uuid.UUID,
        education_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> ProfileEducation:
        """Partially update an existing education record."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileEducationNotFoundError(f"Education '{education_id}' not found")

        existing = await self.education_repo.get_by_id_and_profile_id(
            education_id, profile.id
        )
        if existing is None:
            raise ProfileEducationNotFoundError(f"Education '{education_id}' not found")

        updated_school = existing.school
        if "school" in updates:
            raw = updates["school"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("School name cannot be empty")
            updated_school = cleaned

        updated_degree = existing.degree
        if "degree" in updates:
            raw = updates["degree"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("Degree cannot be empty")
            updated_degree = cleaned

        updated_field = existing.field_of_study
        if "field_of_study" in updates:
            raw = updates["field_of_study"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("Field of study cannot be empty")
            updated_field = cleaned

        updated_start = updates.get("start_year", existing.start_year)
        updated_end = updates.get("end_year", existing.end_year)

        if updated_start is not None and (updated_start < 1900 or updated_start > 2100):
            raise ProfileValidationError("Start year must be between 1900 and 2100")
        if updated_end is not None and (updated_end < 1900 or updated_end > 2100):
            raise ProfileValidationError("End year must be between 1900 and 2100")
        if (
            updated_start is not None
            and updated_end is not None
            and updated_end < updated_start
        ):
            raise ProfileValidationError("End year cannot precede start year")

        updated_entity = ProfileEducation(
            id=existing.id,
            base_profile_id=existing.base_profile_id,
            school=updated_school,
            degree=updated_degree,
            field_of_study=updated_field,
            start_year=updated_start,
            end_year=updated_end,
            created_at=existing.created_at,
        )
        saved = await self.education_repo.save(updated_entity)
        logger.info("Updated education id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def delete_education(
        self, user_id: uuid.UUID, education_id: uuid.UUID
    ) -> None:
        """Delete an existing education record belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileEducationNotFoundError(f"Education '{education_id}' not found")

        deleted = await self.education_repo.delete(education_id, profile.id)
        if not deleted:
            raise ProfileEducationNotFoundError(f"Education '{education_id}' not found")
        logger.info("Deleted education id=%s for user_id=%s", education_id, user_id)


@dataclass(slots=True)
class ProfileProjectService:
    """Application orchestration service for candidate projects."""

    base_profile_repo: BaseProfileRepository
    project_repo: ProfileProjectRepository

    async def _resolve_base_profile(self, user_id: uuid.UUID) -> BaseProfile:
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            profile = await self.base_profile_repo.save(
                BaseProfile(user_id=user_id, name="Candidate Profile")
            )
        return profile

    async def list_projects(self, user_id: uuid.UUID) -> list[ProfileProject]:
        """List all project portfolio items for caller's base profile."""
        profile = await self._resolve_base_profile(user_id)
        return await self.project_repo.list_by_profile_id(profile.id)

    async def create_project(
        self,
        user_id: uuid.UUID,
        title: str,
        description: str | None = None,
        skills_used: list[str] | None = None,
        url: str | None = None,
    ) -> ProfileProject:
        """Create and attach a new project item."""
        profile = await self._resolve_base_profile(user_id)

        title_clean = title.strip() if title else ""
        if not title_clean:
            raise ProfileValidationError("Project title cannot be empty")

        url_clean = url.strip() if url and url.strip() else None
        if url_clean and len(url_clean) > 2048:
            raise ProfileValidationError(
                "Project URL is too long (maximum 2048 characters)"
            )

        cleaned_skills = _clean_and_validate_skills_used(skills_used)

        project = ProfileProject(
            base_profile_id=profile.id,
            title=title_clean,
            description=description.strip()
            if description and description.strip()
            else None,
            skills_used=cleaned_skills,
            url=url_clean,
        )
        saved = await self.project_repo.save(project)
        logger.info("Created project id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def update_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> ProfileProject:
        """Partially update an existing project belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileProjectNotFoundError(f"Project '{project_id}' not found")

        existing = await self.project_repo.get_by_id_and_profile_id(
            project_id, profile.id
        )
        if existing is None:
            raise ProfileProjectNotFoundError(f"Project '{project_id}' not found")

        updated_title = existing.title
        if "title" in updates:
            raw = updates["title"]
            cleaned = raw.strip() if raw else ""
            if not cleaned:
                raise ProfileValidationError("Project title cannot be empty")
            updated_title = cleaned

        updated_desc = existing.description
        if "description" in updates:
            raw = updates["description"]
            updated_desc = raw.strip() if raw and raw.strip() else None

        updated_url = existing.url
        if "url" in updates:
            raw = updates["url"]
            cleaned = raw.strip() if raw and raw.strip() else None
            if cleaned and len(cleaned) > 2048:
                raise ProfileValidationError(
                    "Project URL is too long (maximum 2048 characters)"
                )
            updated_url = cleaned

        updated_skills = existing.skills_used
        if "skills_used" in updates:
            raw_skills = updates["skills_used"]
            updated_skills = _clean_and_validate_skills_used(raw_skills)

        updated_entity = ProfileProject(
            id=existing.id,
            base_profile_id=existing.base_profile_id,
            title=updated_title,
            description=updated_desc,
            skills_used=updated_skills,
            url=updated_url,
            created_at=existing.created_at,
        )
        saved = await self.project_repo.save(updated_entity)
        logger.info("Updated project id=%s for user_id=%s", saved.id, user_id)
        return saved

    async def delete_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Delete an existing project belonging to caller's profile."""
        profile = await self.base_profile_repo.get_by_user_id(user_id)
        if profile is None:
            raise ProfileProjectNotFoundError(f"Project '{project_id}' not found")

        deleted = await self.project_repo.delete(project_id, profile.id)
        if not deleted:
            raise ProfileProjectNotFoundError(f"Project '{project_id}' not found")
        logger.info("Deleted project id=%s for user_id=%s", project_id, user_id)
