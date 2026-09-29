"""API integration tests for candidate Base Profile child collections.

Validates full CRUD, strict User -> BaseProfile -> Child ownership enforcement,
non-destructive operations, partial updates, and validation error contracts.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.profile_management.child_services import (
    ProfileEducationService,
    ProfileExperienceService,
    ProfileProjectService,
    ProfileSkillService,
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
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.dependencies.profile import (
    get_base_profile_service,
    get_profile_education_service,
    get_profile_experience_service,
    get_profile_project_service,
    get_profile_skill_service,
)
from backend.interfaces.api.main import create_app

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
# Test Setup Fixture
# ============================================================================


@pytest.fixture
def child_api_setup():
    """Build isolated app, client, test doubles, and services for child API tests."""
    bp_repo = InMemoryBaseProfileRepository()
    skill_repo = InMemorySkillRepository()
    exp_repo = InMemoryExperienceRepository()
    edu_repo = InMemoryEducationRepository()
    proj_repo = InMemoryProjectRepository()

    bp_service = BaseProfileService(base_profile_repo=bp_repo)
    skill_service = ProfileSkillService(
        base_profile_repo=bp_repo, skill_repo=skill_repo
    )
    exp_service = ProfileExperienceService(
        base_profile_repo=bp_repo, experience_repo=exp_repo
    )
    edu_service = ProfileEducationService(
        base_profile_repo=bp_repo, education_repo=edu_repo
    )
    proj_service = ProfileProjectService(
        base_profile_repo=bp_repo, project_repo=proj_repo
    )

    test_settings = Settings(
        app_name="JobScope-Test",
        app_version="0.1.0-test",
        environment="test",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
        log_level="DEBUG",
    )

    users: dict[uuid.UUID, UserModel] = {}

    async def mock_get(model_cls, ident):
        if model_cls is UserModel:
            return users.get(ident)
        return None

    def mock_add(instance):
        if isinstance(instance, UserModel):
            users[instance.id] = instance

    session_inst = AsyncMock(spec=AsyncSession)
    session_inst.get.side_effect = mock_get
    session_inst.add.side_effect = mock_add
    session_inst.flush = AsyncMock()
    session_inst.commit = AsyncMock()
    session_inst.close = AsyncMock()

    app = create_app(settings=test_settings)

    async def mock_db_session_gen():
        yield session_inst

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = mock_db_session_gen
    app.dependency_overrides[get_base_profile_service] = lambda: bp_service
    app.dependency_overrides[get_profile_skill_service] = lambda: skill_service
    app.dependency_overrides[get_profile_experience_service] = lambda: exp_service
    app.dependency_overrides[get_profile_education_service] = lambda: edu_service
    app.dependency_overrides[get_profile_project_service] = lambda: proj_service

    client = TestClient(app)
    return {
        "client": client,
        "bp_repo": bp_repo,
        "skill_repo": skill_repo,
        "exp_repo": exp_repo,
        "edu_repo": edu_repo,
        "proj_repo": proj_repo,
    }


# ============================================================================
# 1. Skill API Tests
# ============================================================================


def test_skill_api_crud_lifecycle(child_api_setup) -> None:
    """Verify full CRUD operations on /api/profile/skills."""
    client: TestClient = child_api_setup["client"]
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # List initially empty
    resp = client.get("/api/profile/skills", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == []

    # Create skill
    payload = {
        "name": "FastAPI",
        "category": "Web Frameworks",
        "years_of_experience": 3.5,
        "level": "Expert",
    }
    create_resp = client.post("/api/profile/skills", json=payload, headers=headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    created_skill = create_resp.json()
    skill_id = created_skill["id"]
    assert created_skill["name"] == "FastAPI"
    assert created_skill["category"] == "Web Frameworks"
    assert Decimal(str(created_skill["years_of_experience"])) == Decimal("3.5")

    # List shows created skill
    list_resp = client.get("/api/profile/skills", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"] == skill_id

    # Partial update: PATCH only level
    patch_resp = client.patch(
        f"/api/profile/skills/{skill_id}",
        json={"level": "Staff"},
        headers=headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    updated_skill = patch_resp.json()
    assert updated_skill["level"] == "Staff"
    assert updated_skill["name"] == "FastAPI"
    assert updated_skill["category"] == "Web Frameworks"

    # Delete skill
    del_resp = client.delete(f"/api/profile/skills/{skill_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify deleted
    post_del_list = client.get("/api/profile/skills", headers=headers)
    assert len(post_del_list.json()) == 0


def test_skill_api_validation_errors(child_api_setup) -> None:
    """Verify API error contract for invalid skill requests."""
    client: TestClient = child_api_setup["client"]
    headers = {"X-User-Id": str(uuid.uuid4())}

    # Empty name
    resp = client.post("/api/profile/skills", json={"name": "   "}, headers=headers)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Negative years
    resp = client.post(
        "/api/profile/skills",
        json={"name": "Python", "years_of_experience": -2.0},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# 2. Experience API Tests
# ============================================================================


def test_experience_api_crud_lifecycle(child_api_setup) -> None:
    """Verify full CRUD operations on /api/profile/experiences."""
    client: TestClient = child_api_setup["client"]
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # Create experience
    payload = {
        "company": "Trendyol",
        "title": "Backend Engineer",
        "start_date": "2021-03-01",
        "end_date": "2023-08-31",
        "is_current": False,
        "description": "High scale commerce backend",
        "skills_used": ["Go", "Kafka", "Postgres"],
    }
    create_resp = client.post("/api/profile/experiences", json=payload, headers=headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    data = create_resp.json()
    exp_id = data["id"]
    assert data["company"] == "Trendyol"
    assert data["skills_used"] == ["Go", "Kafka", "Postgres"]

    # List experiences
    list_resp = client.get("/api/profile/experiences", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.json()) == 1

    # Partial update: PATCH title only
    patch_resp = client.patch(
        f"/api/profile/experiences/{exp_id}",
        json={"title": "Senior Backend Engineer"},
        headers=headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["title"] == "Senior Backend Engineer"
    assert patch_resp.json()["company"] == "Trendyol"
    assert patch_resp.json()["start_date"] == "2021-03-01"

    # Delete experience
    del_resp = client.delete(f"/api/profile/experiences/{exp_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    assert len(client.get("/api/profile/experiences", headers=headers).json()) == 0


def test_experience_api_validation_errors(child_api_setup) -> None:
    """Verify experience validation rejects invalid date logic and empty strings."""
    client: TestClient = child_api_setup["client"]
    headers = {"X-User-Id": str(uuid.uuid4())}

    # End date before start date
    resp = client.post(
        "/api/profile/experiences",
        json={
            "company": "Acme",
            "title": "Dev",
            "start_date": "2023-05-01",
            "end_date": "2022-05-01",
        },
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "precede" in resp.json()["detail"].lower()


# ============================================================================
# 3. Education API Tests
# ============================================================================


def test_education_api_crud_lifecycle(child_api_setup) -> None:
    """Verify full CRUD operations on /api/profile/educations."""
    client: TestClient = child_api_setup["client"]
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # Create education
    payload = {
        "school": "ITU",
        "degree": "Bachelor of Science",
        "field_of_study": "Computer Science",
        "start_year": 2016,
        "end_year": 2020,
    }
    create_resp = client.post("/api/profile/educations", json=payload, headers=headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    edu_id = create_resp.json()["id"]

    # List
    list_resp = client.get("/api/profile/educations", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.json()) == 1

    # Partial update: degree only
    patch_resp = client.patch(
        f"/api/profile/educations/{edu_id}",
        json={"degree": "B.Sc."},
        headers=headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["degree"] == "B.Sc."
    assert patch_resp.json()["school"] == "ITU"
    assert patch_resp.json()["start_year"] == 2016

    # Delete
    del_resp = client.delete(f"/api/profile/educations/{edu_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT


# ============================================================================
# 4. Project API Tests
# ============================================================================


def test_project_api_crud_lifecycle(child_api_setup) -> None:
    """Verify full CRUD operations on /api/profile/projects."""
    client: TestClient = child_api_setup["client"]
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # Create project
    payload = {
        "title": "JobScope Project",
        "description": "Deterministic job matching engine",
        "skills_used": ["Python", "FastAPI"],
        "url": "https://example.com/project",
    }
    create_resp = client.post("/api/profile/projects", json=payload, headers=headers)
    assert create_resp.status_code == status.HTTP_201_CREATED
    proj_id = create_resp.json()["id"]

    # List
    list_resp = client.get("/api/profile/projects", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    assert len(list_resp.json()) == 1

    # Partial update: URL only
    patch_resp = client.patch(
        f"/api/profile/projects/{proj_id}",
        json={"url": "https://example.com/updated"},
        headers=headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["url"] == "https://example.com/updated"
    assert patch_resp.json()["title"] == "JobScope Project"

    # Delete
    del_resp = client.delete(f"/api/profile/projects/{proj_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT


# ============================================================================
# 5. Strict Cross-User Ownership Enforcement Tests (Section 17)
# ============================================================================


def test_cross_user_ownership_enforcement(child_api_setup) -> None:
    """Verify User B cannot view, modify, or delete User A's child resources."""
    client: TestClient = child_api_setup["client"]

    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()
    headers_a = {"X-User-Id": str(user_a_id)}
    headers_b = {"X-User-Id": str(user_b_id)}

    # User A creates resources
    skill_a_id = client.post(
        "/api/profile/skills",
        json={"name": "Confidential Skill A"},
        headers=headers_a,
    ).json()["id"]

    exp_a_id = client.post(
        "/api/profile/experiences",
        json={
            "company": "Company A",
            "title": "Engineer A",
            "start_date": "2020-01-01",
        },
        headers=headers_a,
    ).json()["id"]

    edu_a_id = client.post(
        "/api/profile/educations",
        json={
            "school": "School A",
            "degree": "Degree A",
            "field_of_study": "Field A",
        },
        headers=headers_a,
    ).json()["id"]

    proj_a_id = client.post(
        "/api/profile/projects",
        json={"title": "Project A"},
        headers=headers_a,
    ).json()["id"]

    # 1. User B lists items: must NOT see User A's items
    assert client.get("/api/profile/skills", headers=headers_b).json() == []
    assert client.get("/api/profile/experiences", headers=headers_b).json() == []
    assert client.get("/api/profile/educations", headers=headers_b).json() == []
    assert client.get("/api/profile/projects", headers=headers_b).json() == []

    # 2. User B tries to PATCH User A's items: must return 404
    assert (
        client.patch(
            f"/api/profile/skills/{skill_a_id}",
            json={"name": "Hacked Skill"},
            headers=headers_b,
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    assert (
        client.patch(
            f"/api/profile/experiences/{exp_a_id}",
            json={"company": "Hacked Company"},
            headers=headers_b,
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    assert (
        client.patch(
            f"/api/profile/educations/{edu_a_id}",
            json={"school": "Hacked School"},
            headers=headers_b,
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    assert (
        client.patch(
            f"/api/profile/projects/{proj_a_id}",
            json={"title": "Hacked Project"},
            headers=headers_b,
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    # 3. User B tries to DELETE User A's items: must return 404
    assert (
        client.delete(
            f"/api/profile/skills/{skill_a_id}", headers=headers_b
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert (
        client.delete(
            f"/api/profile/experiences/{exp_a_id}", headers=headers_b
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert (
        client.delete(
            f"/api/profile/educations/{edu_a_id}", headers=headers_b
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert (
        client.delete(
            f"/api/profile/projects/{proj_a_id}", headers=headers_b
        ).status_code
        == status.HTTP_404_NOT_FOUND
    )

    # Verify User A's items are completely unchanged
    skills_a = client.get("/api/profile/skills", headers=headers_a).json()
    assert len(skills_a) == 1
    assert skills_a[0]["name"] == "Confidential Skill A"


# ============================================================================
# 6. Non-Destructive Update Across All Collections (Section 18)
# ============================================================================


def test_non_destructive_child_update(child_api_setup) -> None:
    """Verify modifying one child collection leaves all other children untouched."""
    client: TestClient = child_api_setup["client"]
    bp_repo: InMemoryBaseProfileRepository = child_api_setup["bp_repo"]
    skill_repo: InMemorySkillRepository = child_api_setup["skill_repo"]
    exp_repo: InMemoryExperienceRepository = child_api_setup["exp_repo"]
    edu_repo: InMemoryEducationRepository = child_api_setup["edu_repo"]
    proj_repo: InMemoryProjectRepository = child_api_setup["proj_repo"]

    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # Pre-populate base profile with multiple child items
    skill_1 = ProfileSkill(base_profile_id=profile_id, name="Python")
    skill_2 = ProfileSkill(base_profile_id=profile_id, name="Docker")
    exp_1 = ProfileExperience(
        base_profile_id=profile_id,
        company="Startup Co",
        title="Lead Dev",
        start_date=date(2020, 1, 1),
    )
    edu_1 = ProfileEducation(
        base_profile_id=profile_id,
        school="State University",
        degree="B.S.",
        field_of_study="Computer Science",
    )
    proj_1 = ProfileProject(
        base_profile_id=profile_id,
        title="Autonomous Agent",
    )

    # Store in repos
    skill_repo.items[skill_1.id] = skill_1
    skill_repo.items[skill_2.id] = skill_2
    exp_repo.items[exp_1.id] = exp_1
    edu_repo.items[edu_1.id] = edu_1
    proj_repo.items[proj_1.id] = proj_1

    base_profile = BaseProfile(
        id=profile_id,
        user_id=user_id,
        name="Original Candidate",
        summary="Experienced engineer",
        skills=[skill_1, skill_2],
        experiences=[exp_1],
        educations=[edu_1],
        projects=[proj_1],
    )
    bp_repo.profiles[profile_id] = base_profile

    # Update ONLY Skill 1
    patch_resp = client.patch(
        f"/api/profile/skills/{skill_1.id}",
        json={"name": "Python 3.12"},
        headers=headers,
    )
    assert patch_resp.status_code == status.HTTP_200_OK

    # Query skills: Skill 1 is updated, Skill 2 is untouched
    skills_after = client.get("/api/profile/skills", headers=headers).json()
    assert len(skills_after) == 2
    names = {s["name"] for s in skills_after}
    assert names == {"Python 3.12", "Docker"}

    # Query experiences: completely untouched
    exps_after = client.get("/api/profile/experiences", headers=headers).json()
    assert len(exps_after) == 1
    assert exps_after[0]["company"] == "Startup Co"

    # Query educations: completely untouched
    edus_after = client.get("/api/profile/educations", headers=headers).json()
    assert len(edus_after) == 1
    assert edus_after[0]["school"] == "State University"

    # Query projects: completely untouched
    projs_after = client.get("/api/profile/projects", headers=headers).json()
    assert len(projs_after) == 1
    assert projs_after[0]["title"] == "Autonomous Agent"

    # Query root profile: metadata remains intact
    root_profile = client.get("/api/profile", headers=headers).json()
    assert root_profile["name"] == "Original Candidate"
    assert root_profile["summary"] == "Experienced engineer"
