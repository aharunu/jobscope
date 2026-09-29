"""API tests for candidate Base Profile management (/api/profile)."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.profile_management.services import BaseProfileService
from backend.domain.profile.entities import (
    BaseProfile,
    ProfileExperience,
    ProfileSkill,
)
from backend.domain.profile.repositories import BaseProfileRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.auth import DEV_FALLBACK_USER_ID
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.dependencies.profile import get_base_profile_service
from backend.interfaces.api.main import create_app

# ============================================================================
# In-Memory Test Double
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


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_session():
    """Mock async session supporting UserModel queries and transaction methods."""
    session = AsyncMock(spec=AsyncSession)
    users: dict[uuid.UUID, UserModel] = {}

    async def mock_get(model_cls, ident):
        if model_cls is UserModel:
            return users.get(ident)
        return None

    def mock_add(instance):
        if isinstance(instance, UserModel):
            users[instance.id] = instance

    session.get.side_effect = mock_get
    session.add.side_effect = mock_add
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def profile_test_setup(mock_session):
    """Set up test app with in-memory repo, service, and mock session."""
    repo = InMemoryBaseProfileRepository()
    service = BaseProfileService(base_profile_repo=repo)

    test_settings = Settings(
        app_name="JobScope-Test",
        app_version="0.1.0-test",
        environment="test",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
        log_level="DEBUG",
    )

    app = create_app(settings=test_settings)

    async def mock_db_session_gen():
        yield mock_session

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = mock_db_session_gen
    app.dependency_overrides[get_base_profile_service] = lambda: service

    client = TestClient(app)
    return {
        "app": app,
        "client": client,
        "repo": repo,
        "service": service,
        "mock_session": mock_session,
        "settings": test_settings,
    }


# ============================================================================
# API Tests
# ============================================================================


def test_get_current_profile_auto_provisions_default_dev_user(
    profile_test_setup,
) -> None:
    """GET /api/profile auto-creates and returns a blank profile in dev/test."""
    client: TestClient = profile_test_setup["client"]

    # Request without X-User-Id header
    response = client.get("/api/profile")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user_id"] == str(DEV_FALLBACK_USER_ID)
    assert data["name"] == "Candidate Profile"
    assert data["summary"] is None
    assert data["skills"] == []
    assert data["experiences"] == []
    assert data["educations"] == []
    assert data["projects"] == []


def test_get_current_profile_with_explicit_user_id(profile_test_setup) -> None:
    """GET /api/profile with explicit X-User-Id returns profile for that user."""
    client: TestClient = profile_test_setup["client"]
    user_id = uuid.uuid4()

    response = client.get("/api/profile", headers={"X-User-Id": str(user_id)})
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["name"] == "Candidate Profile"


def test_get_current_profile_invalid_user_id_format(profile_test_setup) -> None:
    """GET /api/profile rejects invalid UUID format with 400 Bad Request."""
    client: TestClient = profile_test_setup["client"]

    response = client.get("/api/profile", headers={"X-User-Id": "invalid-uuid-string"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid X-User-Id header format" in response.json()["detail"]


def test_get_current_profile_production_missing_header_rejected(
    profile_test_setup,
) -> None:
    """In production mode, missing X-User-Id returns 401 Unauthorized."""
    app: FastAPI = profile_test_setup["app"]
    client: TestClient = profile_test_setup["client"]

    # Configure production settings (non-dev, debug=False)
    prod_settings = Settings(
        app_name="JobScope-Prod",
        app_version="0.1.0",
        environment="production",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_prod",
        log_level="INFO",
    )
    app.dependency_overrides[get_settings] = lambda: prod_settings

    response = client.get("/api/profile")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication required" in response.json()["detail"]


def test_get_current_profile_production_with_valid_user(profile_test_setup) -> None:
    """In production mode, a valid authenticated user returns their profile."""
    app: FastAPI = profile_test_setup["app"]
    client: TestClient = profile_test_setup["client"]
    mock_session = profile_test_setup["mock_session"]
    user_id = uuid.uuid4()

    prod_settings = Settings(
        app_name="JobScope-Prod",
        app_version="0.1.0",
        environment="production",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_prod",
        log_level="INFO",
    )
    app.dependency_overrides[get_settings] = lambda: prod_settings

    # Pre-populate user record in mock session
    mock_session.add(UserModel(id=user_id))

    response = client.get("/api/profile", headers={"X-User-Id": str(user_id)})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["user_id"] == str(user_id)


def test_patch_current_profile_not_found_when_missing(profile_test_setup) -> None:
    """PATCH /api/profile returns 404 when profile does not exist for the user."""
    client: TestClient = profile_test_setup["client"]
    user_id = uuid.uuid4()

    response = client.patch(
        "/api/profile",
        json={"name": "Alice Developer"},
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


def test_patch_current_profile_metadata_success(profile_test_setup) -> None:
    """PATCH /api/profile updates root name and summary non-destructively."""
    client: TestClient = profile_test_setup["client"]
    repo: InMemoryBaseProfileRepository = profile_test_setup["repo"]
    user_id = uuid.uuid4()

    # Pre-seed existing profile with a skill and experience
    profile_id = uuid.uuid4()
    profile = BaseProfile(
        id=profile_id,
        user_id=user_id,
        name="Old Name",
        summary="Old summary",
        skills=[
            ProfileSkill(base_profile_id=profile_id, name="Python", level="Senior")
        ],
        experiences=[
            ProfileExperience(
                base_profile_id=profile_id,
                company="Old Corp",
                title="Engineer",
                start_date=date(2021, 1, 1),
            )
        ],
    )
    repo.profiles[profile_id] = profile

    patch_payload = {
        "name": "Jane Developer",
        "summary": "Experienced Full Stack Engineer with cloud expertise",
    }
    response = client.patch(
        "/api/profile",
        json=patch_payload,
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["name"] == "Jane Developer"
    assert data["summary"] == "Experienced Full Stack Engineer with cloud expertise"
    # Verify child collections remain intact
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "Python"
    assert len(data["experiences"]) == 1
    assert data["experiences"][0]["company"] == "Old Corp"


def test_patch_current_profile_partial_field_preservation(profile_test_setup) -> None:
    """PATCH /api/profile updating only name leaves existing summary untouched."""
    client: TestClient = profile_test_setup["client"]
    user_id = uuid.uuid4()

    # Auto-provision profile via GET
    client.get("/api/profile", headers={"X-User-Id": str(user_id)})

    # Set initial summary
    client.patch(
        "/api/profile",
        json={"name": "Alice Initial", "summary": "Keep this summary"},
        headers={"X-User-Id": str(user_id)},
    )

    # Partial update: name only
    response = client.patch(
        "/api/profile",
        json={"name": "Alice Updated"},
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["name"] == "Alice Updated"
    assert response.json()["summary"] == "Keep this summary"


def test_patch_current_profile_validation_rejects_empty_name(
    profile_test_setup,
) -> None:
    """PATCH /api/profile with blank whitespace name returns 422."""
    client: TestClient = profile_test_setup["client"]
    user_id = uuid.uuid4()

    # Auto-provision profile via GET
    client.get("/api/profile", headers={"X-User-Id": str(user_id)})

    response = client.patch(
        "/api/profile",
        json={"name": "   "},
        headers={"X-User-Id": str(user_id)},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "cannot be empty" in response.json()["detail"].lower()
