"""API integration tests for candidate Search Profile management.

Validates full CRUD on /api/search-profiles, strict User -> BaseProfile ->
SearchProfile ownership enforcement, partial PATCH updates, validation errors,
and production auth contracts.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.profile_management.search_profile_service import (
    SearchProfileService,
)
from backend.domain.profile.entities import BaseProfile
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.dependencies.profile import (
    get_search_profile_service,
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


class InMemorySearchProfileRepository(SearchProfileRepository):
    """In-memory test double for SearchProfileRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, SearchProfile] = {}

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
        self.items[search_profile.id] = search_profile
        return search_profile

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        sp = self.items.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            del self.items[search_profile_id]
            return True
        return False


# ============================================================================
# Fixture
# ============================================================================


@pytest.fixture
def sp_api_setup():
    """Build isolated client and services for search profile API tests."""

    bp_repo = InMemoryBaseProfileRepository()
    sp_repo = InMemorySearchProfileRepository()
    sp_service = SearchProfileService(
        base_profile_repo=bp_repo,
        search_profile_repo=sp_repo,
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
    app.dependency_overrides[get_search_profile_service] = lambda: sp_service

    client = TestClient(app)
    return {
        "client": client,
        "bp_repo": bp_repo,
        "sp_repo": sp_repo,
        "sp_service": sp_service,
        "settings": test_settings,
        "app": app,
    }


# ============================================================================
# 1. Basic CRUD Lifecycle
# ============================================================================


def test_search_profile_crud_lifecycle(sp_api_setup) -> None:
    """Verify full CRUD lifecycle on /api/search-profiles."""
    client: TestClient = sp_api_setup["client"]
    user_id = uuid.uuid4()
    headers = {"X-User-Id": str(user_id)}

    # 1. Initially empty
    list_resp = client.get("/api/search-profiles", headers=headers)
    assert list_resp.status_code == status.HTTP_200_OK
    assert list_resp.json() == []

    # 2. Create search profile
    create_payload = {
        "name": "Senior Backend Engineer",
        "target_roles": ["Senior Backend Engineer", "Lead Developer"],
        "seniority": "senior",
        "target_skills": ["Python", "FastAPI", "PostgreSQL"],
        "locations": ["London", "Remote"],
        "work_modes": ["remote", "hybrid"],
        "industries": ["Fintech", "Healthtech"],
        "salary_min": 85000.00,
        "salary_max": 125000.00,
    }
    create_resp = client.post(
        "/api/search-profiles", json=create_payload, headers=headers
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    data = create_resp.json()
    sp_id = data["id"]
    assert data["name"] == "Senior Backend Engineer"
    assert data["seniority"] == "senior"
    assert data["target_roles"] == ["Senior Backend Engineer", "Lead Developer"]
    assert float(data["salary_min"]) == 85000.00
    assert float(data["salary_max"]) == 125000.00

    # 3. Retrieve by ID
    get_resp = client.get(f"/api/search-profiles/{sp_id}", headers=headers)
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == sp_id

    # 4. Partial PATCH: update name and seniority only
    patch_payload = {"name": "Staff Backend Engineer", "seniority": "staff"}
    patch_resp = client.patch(
        f"/api/search-profiles/{sp_id}", json=patch_payload, headers=headers
    )
    assert patch_resp.status_code == status.HTTP_200_OK
    patched = patch_resp.json()
    assert patched["name"] == "Staff Backend Engineer"
    assert patched["seniority"] == "staff"
    # Unchanged fields remain preserved
    assert patched["target_roles"] == ["Senior Backend Engineer", "Lead Developer"]
    assert float(patched["salary_min"]) == 85000.00

    # 5. List now has 1 profile
    list_after = client.get("/api/search-profiles", headers=headers)
    assert list_after.status_code == status.HTTP_200_OK
    assert len(list_after.json()) == 1

    # 6. Delete
    del_resp = client.delete(f"/api/search-profiles/{sp_id}", headers=headers)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # 7. Verify 404 after deletion
    get_after_del = client.get(f"/api/search-profiles/{sp_id}", headers=headers)
    assert get_after_del.status_code == status.HTTP_404_NOT_FOUND

    # 8. List is empty again
    list_empty = client.get("/api/search-profiles", headers=headers)
    assert list_empty.json() == []


# ============================================================================
# 2. Validation Errors
# ============================================================================


def test_search_profile_validation_errors(sp_api_setup) -> None:
    """Verify 422 Unprocessable Entity responses for malformed inputs."""
    client: TestClient = sp_api_setup["client"]
    headers = {"X-User-Id": str(uuid.uuid4())}

    # Empty name
    resp = client.post("/api/search-profiles", json={"name": "   "}, headers=headers)
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Negative salary
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "salary_min": -1000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Salary min > salary max
    resp = client.post(
        "/api/search-profiles",
        json={"name": "Dev", "salary_min": 100000, "salary_max": 50000},
        headers=headers,
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# 3. Cross-User Ownership Isolation
# ============================================================================


def test_cross_user_ownership_isolation(sp_api_setup) -> None:
    """Verify User B cannot view, modify, or delete User A's SearchProfile."""
    client: TestClient = sp_api_setup["client"]
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    headers_a = {"X-User-Id": str(user_a)}
    headers_b = {"X-User-Id": str(user_b)}

    # User A creates a SearchProfile
    resp_a = client.post(
        "/api/search-profiles",
        json={"name": "User A Private Target", "target_roles": ["Lead"]},
        headers=headers_a,
    )
    assert resp_a.status_code == status.HTTP_201_CREATED
    sp_a_id = resp_a.json()["id"]

    # 1. User B lists profiles: User A's profile must NOT appear
    list_b = client.get("/api/search-profiles", headers=headers_b)
    assert list_b.status_code == status.HTTP_200_OK
    assert list_b.json() == []

    # 2. User B tries to GET User A's profile by ID -> 404
    get_b = client.get(f"/api/search-profiles/{sp_a_id}", headers=headers_b)
    assert get_b.status_code == status.HTTP_404_NOT_FOUND

    # 3. User B tries to PATCH User A's profile -> 404
    patch_b = client.patch(
        f"/api/search-profiles/{sp_a_id}",
        json={"name": "Hacked Title"},
        headers=headers_b,
    )
    assert patch_b.status_code == status.HTTP_404_NOT_FOUND

    # 4. User B tries to DELETE User A's profile -> 404
    del_b = client.delete(f"/api/search-profiles/{sp_a_id}", headers=headers_b)
    assert del_b.status_code == status.HTTP_404_NOT_FOUND

    # 5. User A verifies profile is untouched
    get_a = client.get(f"/api/search-profiles/{sp_a_id}", headers=headers_a)
    assert get_a.status_code == status.HTTP_200_OK
    assert get_a.json()["name"] == "User A Private Target"


# ============================================================================
# 4. Production Authentication Protection
# ============================================================================


def test_production_unauthenticated_request_blocked(sp_api_setup) -> None:
    """Verify that in production environment, unauthenticated requests return 401."""
    app = sp_api_setup["app"]
    prod_settings = Settings(
        app_name="JobScope-Prod",
        app_version="0.1.0-prod",
        environment="production",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_prod",
        log_level="INFO",
    )
    app.dependency_overrides[get_settings] = lambda: prod_settings

    prod_client = TestClient(app)
    # Request without auth in production must fail with 401
    resp = prod_client.get("/api/search-profiles")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
