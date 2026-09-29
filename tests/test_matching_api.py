"""API endpoint tests for deterministic job matching (POST /api/matches)."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.matching.services import MatchingService
from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.enums import RequirementType
from backend.domain.job.repositories import JobRepository
from backend.domain.matching.entities import MatchResult
from backend.domain.matching.repositories import MatchResultRepository
from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileSkill,
)
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
from backend.interfaces.api.dependencies.auth import DEV_FALLBACK_USER_ID
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.dependencies.matching import get_matching_service
from backend.interfaces.api.main import create_app

# ============================================================================
# In-Memory Test Doubles
# ============================================================================


class InMemoryJobRepository(JobRepository):
    """In-memory test double for JobRepository."""

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self.jobs: dict[uuid.UUID, Job] = {j.id: j for j in (jobs or [])}

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    async def get_by_source_and_external_id(
        self, source_id: uuid.UUID, external_job_id: str
    ) -> Job | None:
        return None

    async def get_by_canonical_url(self, canonical_url: str) -> Job | None:
        return None

    async def save(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    async def save_bulk(self, jobs: list[Job]) -> list[Job]:
        for j in jobs:
            self.jobs[j.id] = j
        return jobs

    async def count(self, source_id=None, status=None) -> int:
        return len(self.jobs)

    async def get_job_detail(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)

    async def list_jobs(self, **kwargs) -> list[Job]:
        return list(self.jobs.values())


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

    def __init__(self, profiles: list[SearchProfile] | None = None) -> None:
        self.profiles: dict[uuid.UUID, SearchProfile] = {
            p.id: p for p in (profiles or [])
        }

    async def get_by_id(self, search_profile_id: uuid.UUID) -> SearchProfile | None:
        return self.profiles.get(search_profile_id)

    async def get_by_id_and_base_profile_id(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> SearchProfile | None:
        sp = self.profiles.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            return sp
        return None

    async def list_by_base_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[SearchProfile]:
        return [
            sp for sp in self.profiles.values() if sp.base_profile_id == base_profile_id
        ]

    async def save(self, search_profile: SearchProfile) -> SearchProfile:
        self.profiles[search_profile.id] = search_profile
        return search_profile

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        sp = self.profiles.get(search_profile_id)
        if sp and sp.base_profile_id == base_profile_id:
            del self.profiles[search_profile_id]
            return True
        return False


class InMemoryMatchResultRepository(MatchResultRepository):
    """In-memory test double for MatchResultRepository."""

    def __init__(self) -> None:
        self.records: dict[tuple[uuid.UUID, uuid.UUID], MatchResult] = {}

    async def get_by_id(self, match_result_id: uuid.UUID) -> MatchResult | None:
        for r in self.records.values():
            if r.id == match_result_id:
                return r
        return None

    async def get_by_job_and_search_profile(
        self, job_id: uuid.UUID, search_profile_id: uuid.UUID
    ) -> MatchResult | None:
        return self.records.get((job_id, search_profile_id))

    async def save(self, match_result: MatchResult) -> MatchResult:
        key = (match_result.job_id, match_result.search_profile_id)
        self.records[key] = match_result
        return match_result


# ============================================================================
# API Test Fixtures
# ============================================================================


@pytest.fixture
def test_setup():
    """Build test double repositories, entities, service, and FastAPI client."""
    job_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    sp_id = uuid.uuid4()

    req_py = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="Python programming",
        normalized_skill="Python",
    )
    req_exp = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EXPERIENCE,
        description="2+ years experience",
    )

    job = Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/job/1",
        company="Tech Istanbul",
        title="AI Engineer",
        description="We need an AI Engineer proficient in Python.",
        content_hash="hash1",
        location="Istanbul",
        work_mode="Hybrid",
        requirements=[req_py, req_exp],
    )

    user_id = DEV_FALLBACK_USER_ID

    base_profile = BaseProfile(
        id=bp_id,
        user_id=user_id,
        name="Candidate One",
        skills=[
            ProfileSkill(base_profile_id=bp_id, name="Python"),
            ProfileSkill(base_profile_id=bp_id, name="FastAPI"),
        ],
        experiences=[
            ProfileExperience(
                base_profile_id=bp_id,
                company="Startup",
                title="AI Engineer",
                start_date=date(2022, 1, 1),
                is_current=True,
            )
        ],
        educations=[
            ProfileEducation(
                base_profile_id=bp_id,
                school="Bosphorus Univ",
                degree="Bachelor's Degree",
                field_of_study="Computer Science",
            )
        ],
    )

    search_profile = SearchProfile(
        id=sp_id,
        base_profile_id=bp_id,
        name="Target AI",
        target_roles=["AI Engineer", "Machine Learning Engineer"],
        target_skills=["Python", "FastAPI"],
        locations=["Istanbul"],
        work_modes=["Hybrid", "Remote"],
    )

    job_repo = InMemoryJobRepository([job])
    bp_repo = InMemoryBaseProfileRepository([base_profile])
    sp_repo = InMemorySearchProfileRepository([search_profile])
    match_repo = InMemoryMatchResultRepository()

    service = MatchingService(
        job_repo=job_repo,
        base_profile_repo=bp_repo,
        search_profile_repo=sp_repo,
        match_result_repo=match_repo,
    )

    test_settings = Settings(
        app_name="JobScope-Test",
        app_version="0.1.0-test",
        environment="test",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
        log_level="DEBUG",
    )

    users: dict[uuid.UUID, UserModel] = {
        user_id: UserModel(id=user_id),
    }

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
    app.dependency_overrides[get_matching_service] = lambda: service
    client = TestClient(app)

    return {
        "client": client,
        "job_id": job_id,
        "bp_id": bp_id,
        "sp_id": sp_id,
        "match_repo": match_repo,
        "service": service,
    }


# ============================================================================
# API Tests
# ============================================================================


def test_post_matches_success(test_setup) -> None:
    """POST /api/matches succeeds and returns full deterministic MatchResultResponse."""
    client: TestClient = test_setup["client"]
    job_id: uuid.UUID = test_setup["job_id"]
    sp_id: uuid.UUID = test_setup["sp_id"]

    response = client.post(
        "/api/matches",
        json={"job_id": str(job_id), "search_profile_id": str(sp_id)},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["job_id"] == str(job_id)
    assert data["search_profile_id"] == str(sp_id)
    assert "overall_score" in data
    assert "deterministic_score" in data
    assert "final_score" in data
    assert "confidence" in data
    assert float(data["overall_score"]) > 0.0

    # Category scores
    cat_scores = data["category_scores"]
    assert "ROLE" in cat_scores
    assert "SKILLS" in cat_scores
    assert "EXPERIENCE" in cat_scores
    assert "LOCATION_WORK_MODE" in cat_scores
    assert "EDUCATION" in cat_scores
    assert "OTHER" in cat_scores

    # Requirement matches
    req_matches = data["requirement_matches"]
    assert len(req_matches) >= 2
    for rm in req_matches:
        assert "requirement_id" in rm
        assert rm["match_status"] in ("MATCHED", "PARTIAL", "NOT_MATCHED", "UNKNOWN")
        assert "reason" in rm

    # Explanation
    explanation = data["explanation"]
    assert explanation is not None
    assert "summary" in explanation
    assert "category_explanations" in explanation
    assert "ROLE" in explanation["category_explanations"]


def test_post_matches_idempotent(test_setup) -> None:
    """Repeated calls to POST /api/matches return identical output."""
    client: TestClient = test_setup["client"]
    job_id: uuid.UUID = test_setup["job_id"]
    sp_id: uuid.UUID = test_setup["sp_id"]
    match_repo = test_setup["match_repo"]

    payload = {"job_id": str(job_id), "search_profile_id": str(sp_id)}

    res1 = client.post("/api/matches", json=payload)
    res2 = client.post("/api/matches", json=payload)

    assert res1.status_code == status.HTTP_200_OK
    assert res2.status_code == status.HTTP_200_OK

    d1 = res1.json()
    d2 = res2.json()

    assert d1["overall_score"] == d2["overall_score"]
    assert d1["confidence"] == d2["confidence"]
    assert d1["category_scores"] == d2["category_scores"]
    assert len(match_repo.records) == 1


def test_post_matches_job_not_found(test_setup) -> None:
    """POST /api/matches returns 404 when Job does not exist."""
    client: TestClient = test_setup["client"]
    sp_id: uuid.UUID = test_setup["sp_id"]
    missing_job_id = uuid.uuid4()

    response = client.post(
        "/api/matches",
        json={"job_id": str(missing_job_id), "search_profile_id": str(sp_id)},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Job with ID '{missing_job_id}' not found" in response.json()["detail"]


def test_post_matches_search_profile_not_found(test_setup) -> None:
    """POST /api/matches returns 404 when SearchProfile does not exist."""
    client: TestClient = test_setup["client"]
    job_id: uuid.UUID = test_setup["job_id"]
    missing_sp_id = uuid.uuid4()

    response = client.post(
        "/api/matches",
        json={"job_id": str(job_id), "search_profile_id": str(missing_sp_id)},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert (
        f"Search profile with ID '{missing_sp_id}' not found"
        in response.json()["detail"]
    )


def test_post_matches_invalid_payload(test_setup) -> None:
    """POST /api/matches returns 422 for malformed requests."""
    client: TestClient = test_setup["client"]

    # Missing fields
    res1 = client.post("/api/matches", json={})
    assert res1.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Invalid UUID
    res2 = client.post(
        "/api/matches",
        json={"job_id": "not-a-uuid", "search_profile_id": "also-not-a-uuid"},
    )
    assert res2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
