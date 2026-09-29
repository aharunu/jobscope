"""Phase 6.5 - Profile & Matching Hardening Test Suite.

Validates the final security, validation, and resilience invariants for Phase 6:
1. Salary upper bound enforcement at both schema and service levels (HTTP 422).
2. Strict JSONB array count (>50) and element length (>150 chars) limits (HTTP 422).
3. Exact BaseProfile summary PATCH semantics (preserve, clear to None, trim).
4. Deterministic BaseProfile resolution order (created_at.asc).
5. Cascade deletion verification across SearchProfile and BaseProfile.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.profile_management.child_services import (
    ProfileExperienceService,
    ProfileProjectService,
)
from backend.application.profile_management.exceptions import (
    ProfileValidationError,
)
from backend.application.profile_management.search_profile_service import (
    SearchProfileService,
)
from backend.application.profile_management.services import BaseProfileService
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
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.base_profile import BaseProfileModel
from backend.infrastructure.database.models.matching import (
    MatchResultModel,
)
from backend.infrastructure.database.models.search_profile import SearchProfileModel
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.dependencies.profile import (
    get_base_profile_service,
    get_profile_experience_service,
    get_profile_project_service,
    get_search_profile_service,
)
from backend.interfaces.api.main import create_app

# ============================================================================
# In-Memory Test Repositories
# ============================================================================


class InMemoryBaseProfileRepo(BaseProfileRepository):
    def __init__(self, profiles: list[BaseProfile] | None = None) -> None:
        self.profiles: dict[uuid.UUID, BaseProfile] = {
            p.id: p for p in (profiles or [])
        }

    async def get_by_id(self, profile_id: uuid.UUID) -> BaseProfile | None:
        return self.profiles.get(profile_id)

    async def get_by_user_id(self, user_id: uuid.UUID) -> BaseProfile | None:
        matches = [p for p in self.profiles.values() if p.user_id == user_id]
        if not matches:
            return None
        matches.sort(
            key=lambda x: (x.created_at or datetime.min.replace(tzinfo=UTC), x.id)
        )
        return matches[0]

    async def save(self, profile: BaseProfile) -> BaseProfile:
        now = datetime.now(UTC)
        entity = BaseProfile(
            id=profile.id,
            user_id=profile.user_id,
            name=profile.name,
            summary=profile.summary,
            created_at=profile.created_at or now,
            updated_at=now,
            skills=profile.skills,
            experiences=profile.experiences,
            educations=profile.educations,
            projects=profile.projects,
        )
        self.profiles[entity.id] = entity
        return entity


class InMemorySearchProfileRepo(SearchProfileRepository):
    def __init__(self, items: list[SearchProfile] | None = None) -> None:
        self.items: dict[uuid.UUID, SearchProfile] = {sp.id: sp for sp in (items or [])}

    async def get_by_id(self, search_profile_id: uuid.UUID) -> SearchProfile | None:
        return self.items.get(search_profile_id)

    async def get_by_id_and_base_profile_id(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> SearchProfile | None:
        sp = self.items.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            return sp
        return None

    async def list_by_base_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[SearchProfile]:
        return [
            sp for sp in self.items.values() if sp.base_profile_id == base_profile_id
        ]

    async def save(self, search_profile: SearchProfile) -> SearchProfile:
        now = datetime.now(UTC)
        saved = SearchProfile(
            id=search_profile.id,
            base_profile_id=search_profile.base_profile_id,
            name=search_profile.name,
            target_roles=search_profile.target_roles,
            seniority=search_profile.seniority,
            target_skills=search_profile.target_skills,
            locations=search_profile.locations,
            work_modes=search_profile.work_modes,
            industries=search_profile.industries,
            salary_min=search_profile.salary_min,
            salary_max=search_profile.salary_max,
            created_at=search_profile.created_at or now,
            updated_at=now,
        )
        self.items[saved.id] = saved
        return saved

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        sp = await self.get_by_id_and_base_profile_id(
            search_profile_id, base_profile_id
        )
        if sp:
            del self.items[search_profile_id]
            return True
        return False


class InMemoryExperienceRepo(ProfileExperienceRepository):
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileExperience] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileExperience]:
        return [e for e in self.items.values() if e.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileExperience | None:
        e = self.items.get(experience_id)
        return e if e and e.base_profile_id == base_profile_id else None

    async def save(self, experience: ProfileExperience) -> ProfileExperience:
        self.items[experience.id] = experience
        return experience

    async def delete(
        self, experience_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        if experience_id in self.items:
            del self.items[experience_id]
            return True
        return False


class InMemoryProjectRepo(ProfileProjectRepository):
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileProject] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileProject]:
        return [p for p in self.items.values() if p.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, project_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileProject | None:
        p = self.items.get(project_id)
        return p if p and p.base_profile_id == base_profile_id else None

    async def save(self, project: ProfileProject) -> ProfileProject:
        self.items[project.id] = project
        return project

    async def delete(self, project_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        if project_id in self.items:
            del self.items[project_id]
            return True
        return False


class InMemorySkillRepo(ProfileSkillRepository):
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileSkill] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileSkill]:
        return [s for s in self.items.values() if s.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, skill_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileSkill | None:
        s = self.items.get(skill_id)
        return s if s and s.base_profile_id == base_profile_id else None

    async def save(self, skill: ProfileSkill) -> ProfileSkill:
        self.items[skill.id] = skill
        return skill

    async def delete(self, skill_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        if skill_id in self.items:
            del self.items[skill_id]
            return True
        return False


class InMemoryEducationRepo(ProfileEducationRepository):
    def __init__(self) -> None:
        self.items: dict[uuid.UUID, ProfileEducation] = {}

    async def list_by_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[ProfileEducation]:
        return [e for e in self.items.values() if e.base_profile_id == base_profile_id]

    async def get_by_id_and_profile_id(
        self, education_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> ProfileEducation | None:
        e = self.items.get(education_id)
        return e if e and e.base_profile_id == base_profile_id else None

    async def save(self, education: ProfileEducation) -> ProfileEducation:
        self.items[education.id] = education
        return education

    async def delete(self, education_id: uuid.UUID, base_profile_id: uuid.UUID) -> bool:
        if education_id in self.items:
            del self.items[education_id]
            return True
        return False


# ============================================================================
# Fixture
# ============================================================================


@pytest.fixture
def hardening_setup():
    user_id = uuid.uuid4()
    bp = BaseProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Candidate Hardening",
        summary="Initial Summary",
    )
    sp = SearchProfile(
        id=uuid.uuid4(),
        base_profile_id=bp.id,
        name="Initial Search Profile",
        target_roles=["Backend Engineer"],
    )

    bp_repo = InMemoryBaseProfileRepo([bp])
    sp_repo = InMemorySearchProfileRepo([sp])
    exp_repo = InMemoryExperienceRepo()
    proj_repo = InMemoryProjectRepo()

    bp_service = BaseProfileService(base_profile_repo=bp_repo)
    sp_service = SearchProfileService(
        base_profile_repo=bp_repo, search_profile_repo=sp_repo
    )
    exp_service = ProfileExperienceService(
        base_profile_repo=bp_repo, experience_repo=exp_repo
    )
    proj_service = ProfileProjectService(
        base_profile_repo=bp_repo, project_repo=proj_repo
    )

    settings = Settings(
        app_name="JobScope-Hardening",
        app_version="0.1.0",
        environment="development",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
        log_level="INFO",
    )
    app = create_app(settings=settings)

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = UserModel(id=user_id)

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = lambda: mock_session
    app.dependency_overrides[get_base_profile_service] = lambda: bp_service
    app.dependency_overrides[get_search_profile_service] = lambda: sp_service
    app.dependency_overrides[get_profile_experience_service] = lambda: exp_service
    app.dependency_overrides[get_profile_project_service] = lambda: proj_service

    client = TestClient(app)

    return {
        "client": client,
        "user_id": user_id,
        "bp": bp,
        "sp": sp,
        "bp_repo": bp_repo,
        "sp_repo": sp_repo,
        "bp_service": bp_service,
        "sp_service": sp_service,
        "exp_service": exp_service,
        "proj_service": proj_service,
    }


# ============================================================================
# 1. Salary Upper Bound Hardening Tests
# ============================================================================


def test_search_profile_salary_upper_bound_create_rejected(hardening_setup) -> None:
    """POST /api/search-profiles rejects salary > 9999999999.99 with 422."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    # salary_min exceeds limit
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "salary_min": 10_000_000_000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # salary_max exceeds limit
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "salary_max": 10_000_000_000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_search_profile_salary_upper_bound_update_rejected(hardening_setup) -> None:
    """PATCH /api/search-profiles/{id} rejects salary > 9999999999.99 with 422."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    sp: SearchProfile = hardening_setup["sp"]
    headers = {"X-User-Id": str(user_id)}

    resp = client.patch(
        f"/api/search-profiles/{sp.id}",
        json={"salary_min": 10_000_000_000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    resp = client.patch(
        f"/api/search-profiles/{sp.id}",
        json={"salary_max": 10_000_000_000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.asyncio
async def test_search_profile_service_salary_upper_bound(hardening_setup) -> None:
    """SearchProfileService raises ProfileValidationError if salary exceeds limit."""
    sp_service: SearchProfileService = hardening_setup["sp_service"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    sp: SearchProfile = hardening_setup["sp"]

    with pytest.raises(ProfileValidationError) as exc:
        await sp_service.create_search_profile(
            user_id=user_id,
            name="Test",
            salary_min=Decimal("10000000000.00"),
        )
    assert "maximum allowable limit" in str(exc.value).lower()

    with pytest.raises(ProfileValidationError) as exc:
        await sp_service.update_search_profile(
            user_id=user_id,
            search_profile_id=sp.id,
            updates={"salary_max": Decimal("10000000000.00")},
        )
    assert "maximum allowable limit" in str(exc.value).lower()


# ============================================================================
# 2. JSONB Array Count & Element Length Limits (Strict 422, No Silent Loss)
# ============================================================================


def test_search_profile_rejects_excessive_array_items(hardening_setup) -> None:
    """POST /api/search-profiles rejects >50 list items with 422."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    too_many_roles = [f"Role_{i}" for i in range(51)]
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "target_roles": too_many_roles},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_search_profile_rejects_excessive_item_string_length(hardening_setup) -> None:
    """POST /api/search-profiles rejects items >150 chars with 422."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    long_role = "A" * 151
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "target_roles": [long_role]},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert (
        "150 characters" in str(resp.json()["detail"]).lower()
        or "target_roles" in str(resp.json()["detail"]).lower()
    )


def test_experience_rejects_excessive_skills_used(hardening_setup) -> None:
    """POST /api/profile/experiences rejects >50 skills or strings >150 chars."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    # Item count limit (>50)
    resp = client.post(
        "/api/profile/experiences",
        json={
            "company": "Tech Corp",
            "title": "Developer",
            "start_date": "2022-01-01",
            "skills_used": [f"Skill_{i}" for i in range(51)],
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Item string length limit (>150 chars)
    resp = client.post(
        "/api/profile/experiences",
        json={
            "company": "Tech Corp",
            "title": "Developer",
            "start_date": "2022-01-01",
            "skills_used": ["Python", "X" * 151],
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_project_rejects_excessive_skills_used(hardening_setup) -> None:
    """POST /api/profile/projects rejects >50 skills or strings >150 chars."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    # Item count limit (>50)
    resp = client.post(
        "/api/profile/projects",
        json={
            "title": "Cool Project",
            "skills_used": [f"Skill_{i}" for i in range(51)],
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Item string length limit (>150 chars)
    resp = client.post(
        "/api/profile/projects",
        json={
            "title": "Cool Project",
            "skills_used": ["Postgres", "Z" * 151],
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# 3. BaseProfile Summary PATCH Semantics (All 5 Contract Rules)
# ============================================================================


def test_base_profile_summary_patch_contract(hardening_setup) -> None:
    """Verify all 5 exact contract cases for BaseProfile summary PATCH semantics."""
    client: TestClient = hardening_setup["client"]
    user_id: uuid.UUID = hardening_setup["user_id"]
    headers = {"X-User-Id": str(user_id)}

    # Rule 1: Field omitted -> existing value preserved
    resp = client.patch(
        "/api/profile",
        json={"name": "Alice Renamed"},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["name"] == "Alice Renamed"
    assert resp.json()["summary"] == "Initial Summary"

    # Rule 2: summary=null -> None
    resp = client.patch(
        "/api/profile",
        json={"summary": None},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["summary"] is None

    # Reset summary
    client.patch("/api/profile", json={"summary": "Active Summary"}, headers=headers)

    # Rule 3: summary="" -> None
    resp = client.patch(
        "/api/profile",
        json={"summary": ""},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["summary"] is None

    # Reset summary
    client.patch("/api/profile", json={"summary": "Active Summary"}, headers=headers)

    # Rule 4: summary="   " -> None
    resp = client.patch(
        "/api/profile",
        json={"summary": "     "},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["summary"] is None

    # Rule 5: summary=" text " -> "text"
    resp = client.patch(
        "/api/profile",
        json={"summary": "  Senior Python Architect  "},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["summary"] == "Senior Python Architect"


# ============================================================================
# 4. Deterministic BaseProfile Resolution Order
# ============================================================================


@pytest.mark.asyncio
async def test_base_profile_resolution_order_deterministic() -> None:
    """BaseProfile repo deterministically resolves earliest profile."""
    user_id = uuid.uuid4()
    time_early = datetime(2026, 1, 1, tzinfo=UTC)
    time_late = datetime(2026, 1, 2, tzinfo=UTC)

    bp_early = BaseProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Early Profile",
        created_at=time_early,
    )
    bp_late = BaseProfile(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Late Profile",
        created_at=time_late,
    )

    repo = InMemoryBaseProfileRepo([bp_late, bp_early])
    resolved = await repo.get_by_user_id(user_id)
    assert resolved is not None
    assert resolved.id == bp_early.id
    assert resolved.name == "Early Profile"


# ============================================================================
# 5. Database Cascade Invariants Verification (Zero Migrations)
# ============================================================================


def test_orm_models_cascade_configurations_verified() -> None:
    """Verify ORM relationship cascade rules without schema migrations."""
    # BaseProfile cascades
    assert "delete-orphan" in BaseProfileModel.search_profiles.property.cascade
    assert "delete-orphan" in BaseProfileModel.skills.property.cascade
    assert "delete-orphan" in BaseProfileModel.experiences.property.cascade
    assert "delete-orphan" in BaseProfileModel.educations.property.cascade
    assert "delete-orphan" in BaseProfileModel.projects.property.cascade
    assert "delete-orphan" in BaseProfileModel.match_results.property.cascade

    # SearchProfile cascades to match_results
    assert "delete-orphan" in SearchProfileModel.match_results.property.cascade

    # MatchResult cascades to requirement_matches
    assert "delete-orphan" in MatchResultModel.requirement_matches.property.cascade
