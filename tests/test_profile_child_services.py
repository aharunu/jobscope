"""Unit tests for BaseProfile child application services.
Covers Skills, Experiences, Educations, and Projects CRUD.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from backend.application.profile_management.child_services import (
    ProfileEducationService,
    ProfileExperienceService,
    ProfileProjectService,
    ProfileSkillService,
)
from backend.application.profile_management.exceptions import (
    ProfileSkillNotFoundError,
    ProfileValidationError,
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

# ============================================================================
# In-Memory Test Doubles
# ============================================================================


class InMemoryBaseProfileRepository(BaseProfileRepository):
    """In-memory test double for BaseProfileRepository."""

    def __init__(self, profiles: list[BaseProfile] | None = None) -> None:
        self.profiles: dict[uuid.UUID, BaseProfile] = {
            p.id: p for p in (profiles or [])
        }

    async def get_by_id(self, profile_id: uuid.UUID) -> BaseProfile | None:
        return self.profiles.get(profile_id)

    async def get_by_user_id(self, user_id: uuid.UUID) -> BaseProfile | None:
        for p in self.profiles.values():
            if p.user_id == user_id:
                return p
        return None

    async def save(self, profile: BaseProfile) -> BaseProfile:
        self.profiles[profile.id] = profile
        return profile


class InMemorySkillRepository(ProfileSkillRepository):
    """In-memory test double for ProfileSkillRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileSkill] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileSkill]:
        return [s for s in self.items.values() if s.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, skill_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileSkill | None:
        item = self.items.get(skill_id)
        if item and item.base_profile_id == base_profile_id:
            return item
        return None

    async def save(self, skill: ProfileSkill) -> ProfileSkill:
        self.items[skill.id] = skill
        return skill

    async def delete(self, skill_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        item = self.items.get(skill_id)
        if item and item.base_profile_id == base_profile_id:
            del self.items[skill_id]
            return True
        return False


class InMemoryExperienceRepository(ProfileExperienceRepository):
    """In-memory test double for ProfileExperienceRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileExperience] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileExperience]:
        return [e for e in self.items.values() if e.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileExperience | None:
        item = self.items.get(experience_id)
        if item and item.base_profile_id == base_profile_id:
            return item
        return None

    async def save(self, experience: ProfileExperience) -> ProfileExperience:
        self.items[experience.id] = experience
        return experience

    async def delete(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        item = self.items.get(experience_id)
        if item and item.base_profile_id == base_profile_id:
            del self.items[experience_id]
            return True
        return False


class InMemoryEducationRepository(ProfileEducationRepository):
    """In-memory test double for ProfileEducationRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileEducation] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileEducation]:
        return [e for e in self.items.values() if e.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, education_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileEducation | None:
        item = self.items.get(education_id)
        if item and item.base_profile_id == base_profile_id:
            return item
        return None

    async def save(self, education: ProfileEducation) -> ProfileEducation:
        self.items[education.id] = education
        return education

    async def delete(self, education_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        item = self.items.get(education_id)
        if item and item.base_profile_id == base_profile_id:
            del self.items[education_id]
            return True
        return False


class InMemoryProjectRepository(ProfileProjectRepository):
    """In-memory test double for ProfileProjectRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileProject] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileProject]:
        return [p for p in self.items.values() if p.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, project_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileProject | None:
        item = self.items.get(project_id)
        if item and item.base_profile_id == base_profile_id:
            return item
        return None

    async def save(self, project: ProfileProject) -> ProfileProject:
        self.items[project.id] = project
        return project

    async def delete(self, project_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        item = self.items.get(project_id)
        if item and item.base_profile_id == base_profile_id:
            del self.items[project_id]
            return True
        return False


# ============================================================================
# Skill Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_skill_service_crud_lifecycle() -> None:
    """Verify full CRUD lifecycle and auto-provisioning for ProfileSkillService."""
    bp_repo = InMemoryBaseProfileRepository()
    skill_repo = InMemorySkillRepository()
    service = ProfileSkillService(base_profile_repo=bp_repo, skill_repo=skill_repo)
    user_id = uuid.uuid4()

    # 1. List initially empty (implicitly provisions base profile)
    skills = await service.list_skills(user_id)
    assert skills == []

    # 2. Create skill
    created = await service.create_skill(
        user_id=user_id,
        name="Python",
        category="Languages",
        years_of_experience=Decimal("5.5"),
        level="Senior",
    )
    assert created.name == "Python"
    assert created.category == "Languages"
    assert created.years_of_experience == Decimal("5.5")
    assert created.level == "Senior"

    # 3. List contains created skill
    skills = await service.list_skills(user_id)
    assert len(skills) == 1
    assert skills[0].id == created.id

    # 4. Partial update (name only, category & years preserved)
    updated = await service.update_skill(
        user_id=user_id,
        skill_id=created.id,
        updates={"name": "Python 3"},
    )
    assert updated.name == "Python 3"
    assert updated.category == "Languages"
    assert updated.years_of_experience == Decimal("5.5")

    # 5. Delete skill
    await service.delete_skill(user_id, created.id)
    remaining = await service.list_skills(user_id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_skill_service_validations() -> None:
    """Verify validation rules in ProfileSkillService."""
    bp_repo = InMemoryBaseProfileRepository()
    skill_repo = InMemorySkillRepository()
    service = ProfileSkillService(base_profile_repo=bp_repo, skill_repo=skill_repo)
    user_id = uuid.uuid4()

    # Reject empty name
    with pytest.raises(ProfileValidationError, match="cannot be empty"):
        await service.create_skill(user_id=user_id, name="   ")

    # Reject negative years
    with pytest.raises(ProfileValidationError, match="cannot be negative"):
        await service.create_skill(
            user_id=user_id, name="Python", years_of_experience=Decimal("-1.0")
        )

    # Not found update
    with pytest.raises(ProfileSkillNotFoundError):
        await service.update_skill(
            user_id=user_id, skill_id=uuid.uuid4(), updates={"name": "Rust"}
        )

    # Not found delete
    with pytest.raises(ProfileSkillNotFoundError):
        await service.delete_skill(user_id=user_id, skill_id=uuid.uuid4())


# ============================================================================
# Experience Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_experience_service_crud_lifecycle() -> None:
    """Verify full CRUD lifecycle for ProfileExperienceService."""
    bp_repo = InMemoryBaseProfileRepository()
    exp_repo = InMemoryExperienceRepository()
    service = ProfileExperienceService(
        base_profile_repo=bp_repo, experience_repo=exp_repo
    )
    user_id = uuid.uuid4()

    # 1. Create experience
    created = await service.create_experience(
        user_id=user_id,
        company="Acme Corp",
        title="Software Engineer",
        start_date=date(2022, 1, 1),
        end_date=date(2023, 6, 1),
        is_current=False,
        description="Developed backend microservices",
        skills_used=["Python", "FastAPI", "Docker"],
    )
    assert created.company == "Acme Corp"
    assert created.title == "Software Engineer"
    assert created.skills_used == ["Python", "FastAPI", "Docker"]

    # 2. List experiences
    items = await service.list_experiences(user_id)
    assert len(items) == 1
    assert items[0].id == created.id

    # 3. Partial update: change title only
    updated = await service.update_experience(
        user_id=user_id,
        experience_id=created.id,
        updates={"title": "Senior Software Engineer"},
    )
    assert updated.title == "Senior Software Engineer"
    assert updated.company == "Acme Corp"
    assert updated.start_date == date(2022, 1, 1)

    # 4. Delete experience
    await service.delete_experience(user_id, created.id)
    remaining = await service.list_experiences(user_id)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_experience_service_validations() -> None:
    """Verify validation rules for dates and required fields in Experience service."""
    bp_repo = InMemoryBaseProfileRepository()
    exp_repo = InMemoryExperienceRepository()
    service = ProfileExperienceService(
        base_profile_repo=bp_repo, experience_repo=exp_repo
    )
    user_id = uuid.uuid4()

    # Reject empty company
    with pytest.raises(ProfileValidationError, match="Company name cannot be empty"):
        await service.create_experience(
            user_id=user_id,
            company="",
            title="Engineer",
            start_date=date(2022, 1, 1),
        )

    # Reject empty title
    with pytest.raises(ProfileValidationError, match="Job title cannot be empty"):
        await service.create_experience(
            user_id=user_id,
            company="Acme",
            title="  ",
            start_date=date(2022, 1, 1),
        )

    # Reject end_date before start_date
    with pytest.raises(ProfileValidationError, match="End date cannot precede"):
        await service.create_experience(
            user_id=user_id,
            company="Acme",
            title="Dev",
            start_date=date(2023, 1, 1),
            end_date=date(2022, 1, 1),
        )


# ============================================================================
# Education Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_education_service_crud_lifecycle() -> None:
    """Verify full CRUD lifecycle for ProfileEducationService."""
    bp_repo = InMemoryBaseProfileRepository()
    edu_repo = InMemoryEducationRepository()
    service = ProfileEducationService(
        base_profile_repo=bp_repo, education_repo=edu_repo
    )
    user_id = uuid.uuid4()

    # 1. Create education
    created = await service.create_education(
        user_id=user_id,
        school="Technical University",
        degree="B.S.",
        field_of_study="Computer Engineering",
        start_year=2018,
        end_year=2022,
    )
    assert created.school == "Technical University"
    assert created.degree == "B.S."
    assert created.start_year == 2018

    # 2. List
    items = await service.list_educations(user_id)
    assert len(items) == 1

    # 3. Partial update: degree only
    updated = await service.update_education(
        user_id=user_id,
        education_id=created.id,
        updates={"degree": "M.S."},
    )
    assert updated.degree == "M.S."
    assert updated.school == "Technical University"
    assert updated.start_year == 2018

    # 4. Delete
    await service.delete_education(user_id, created.id)
    assert len(await service.list_educations(user_id)) == 0


@pytest.mark.asyncio
async def test_education_service_validations() -> None:
    """Verify year range and field validations in Education service."""
    bp_repo = InMemoryBaseProfileRepository()
    edu_repo = InMemoryEducationRepository()
    service = ProfileEducationService(
        base_profile_repo=bp_repo, education_repo=edu_repo
    )
    user_id = uuid.uuid4()

    # End year before start year
    with pytest.raises(ProfileValidationError, match="End year cannot precede"):
        await service.create_education(
            user_id=user_id,
            school="School",
            degree="B.S.",
            field_of_study="CS",
            start_year=2022,
            end_year=2020,
        )

    # Invalid year bounds
    with pytest.raises(ProfileValidationError, match="between 1900 and 2100"):
        await service.create_education(
            user_id=user_id,
            school="School",
            degree="B.S.",
            field_of_study="CS",
            start_year=1800,
        )


# ============================================================================
# Project Service Tests
# ============================================================================


@pytest.mark.asyncio
async def test_project_service_crud_lifecycle() -> None:
    """Verify full CRUD lifecycle for ProfileProjectService."""
    bp_repo = InMemoryBaseProfileRepository()
    proj_repo = InMemoryProjectRepository()
    service = ProfileProjectService(base_profile_repo=bp_repo, project_repo=proj_repo)
    user_id = uuid.uuid4()

    # 1. Create project
    created = await service.create_project(
        user_id=user_id,
        title="JobScope",
        description="Autonomous matching engine",
        skills_used=["Python", "FastAPI", "PostgreSQL"],
        url="https://github.com/example/jobscope",
    )
    assert created.title == "JobScope"
    assert created.url == "https://github.com/example/jobscope"

    # 2. List
    items = await service.list_projects(user_id)
    assert len(items) == 1

    # 3. Partial update: description only
    updated = await service.update_project(
        user_id=user_id,
        project_id=created.id,
        updates={"description": "High performance autonomous matching platform"},
    )
    assert updated.description == "High performance autonomous matching platform"
    assert updated.title == "JobScope"
    assert updated.url == "https://github.com/example/jobscope"

    # 4. Delete
    await service.delete_project(user_id, created.id)
    assert len(await service.list_projects(user_id)) == 0


@pytest.mark.asyncio
async def test_project_service_validations() -> None:
    """Verify validation rules in Project service."""
    bp_repo = InMemoryBaseProfileRepository()
    proj_repo = InMemoryProjectRepository()
    service = ProfileProjectService(base_profile_repo=bp_repo, project_repo=proj_repo)
    user_id = uuid.uuid4()

    # Reject empty title
    with pytest.raises(ProfileValidationError, match="Project title cannot be empty"):
        await service.create_project(user_id=user_id, title="   ")

    # Reject excessive URL length (>2048 chars)
    with pytest.raises(ProfileValidationError, match="too long"):
        await service.create_project(
            user_id=user_id, title="Test", url="https://example.com/" + "a" * 2050
        )
