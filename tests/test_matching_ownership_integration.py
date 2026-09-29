"""API and service integration tests for matching ownership enforcement.

Validates the security invariant:
    current_user_id -> owned BaseProfile -> owned SearchProfile -> Job -> MatchResult
Ensures real profile data (skills, experiences, educations, projects) is bound to
the deterministic match engine, cross-user requests return 404, and production
unauthenticated requests are blocked with 401.
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

from backend.application.matching.exceptions import (
    JobNotFoundError,
    SearchProfileNotFoundError,
)
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
    ProfileProject,
    ProfileSkill,
)
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.models.user import UserModel
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
# Fixture
# ============================================================================


@pytest.fixture
def matching_ownership_setup():
    """Build multi-user isolated environment for matching ownership tests."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    bp_a_id = uuid.uuid4()

    bp_a = BaseProfile(
        id=bp_a_id,
        user_id=user_a,
        name="Alice Candidate",
        skills=[
            ProfileSkill(
                base_profile_id=bp_a_id,
                name="Python",
                category="Backend",
                years_of_experience=Decimal("5.0"),
                level="Senior",
            ),
        ],
        experiences=[
            ProfileExperience(
                base_profile_id=bp_a_id,
                company="Fintech Corp",
                title="Senior Python Developer",
                start_date=date(2020, 1, 1),
                is_current=True,
                skills_used=["Python", "FastAPI"],
            ),
        ],
        educations=[
            ProfileEducation(
                base_profile_id=bp_a_id,
                school="Technical University",
                degree="Bachelor's Degree",
                field_of_study="Computer Science",
            ),
        ],
        projects=[
            ProfileProject(
                base_profile_id=bp_a_id,
                title="Job Scope",
                skills_used=["Python", "PostgreSQL"],
            ),
        ],
    )

    sp_a = SearchProfile(
        id=uuid.uuid4(),
        base_profile_id=bp_a.id,
        name="Alice Search Profile",
        target_roles=["Senior Python Developer", "Backend Engineer"],
        seniority="senior",
        target_skills=["AWS"],
        locations=["Berlin", "Remote"],
        work_modes=["remote", "hybrid"],
    )

    bp_b = BaseProfile(
        id=uuid.uuid4(),
        user_id=user_b,
        name="Bob Candidate",
    )

    sp_b = SearchProfile(
        id=uuid.uuid4(),
        base_profile_id=bp_b.id,
        name="Bob Search Profile",
        target_roles=["DevOps Engineer"],
    )

    job_id = uuid.uuid4()
    req_py = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="Python programming",
        normalized_skill="Python",
    )
    req_fastapi = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="FastAPI framework",
        normalized_skill="FastAPI",
    )
    req_postgres = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="PostgreSQL database",
        normalized_skill="PostgreSQL",
    )
    req_aws = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="AWS cloud",
        normalized_skill="AWS",
    )
    req_exp = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EXPERIENCE,
        description="3+ years of experience",
    )
    req_edu = JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EDUCATION,
        description="Bachelor's Degree in Computer Science",
    )

    job = Job(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url=f"https://example.com/jobs/{job_id}",
        company="Berlin Tech",
        title="Senior Python Developer",
        description="Seeking a Senior Python Developer with FastAPI.",
        content_hash="hash_123",
        location="Berlin",
        work_mode="remote",
        requirements=[
            req_py,
            req_fastapi,
            req_postgres,
            req_aws,
            req_exp,
            req_edu,
        ],
    )

    job_repo = InMemoryJobRepository([job])
    bp_repo = InMemoryBaseProfileRepository([bp_a, bp_b])
    sp_repo = InMemorySearchProfileRepository([sp_a, sp_b])
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
        user_a: UserModel(id=user_a),
        user_b: UserModel(id=user_b),
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
        "app": app,
        "user_a": user_a,
        "user_b": user_b,
        "bp_a": bp_a,
        "bp_b": bp_b,
        "sp_a": sp_a,
        "sp_b": sp_b,
        "job": job,
        "service": service,
        "match_repo": match_repo,
    }


# ============================================================================
# 1. Cross-User Matching Isolation Tests
# ============================================================================


def test_cross_user_matching_returns_404(matching_ownership_setup) -> None:
    """User B cannot trigger matching on User A's search profile."""
    client: TestClient = matching_ownership_setup["client"]
    user_b: uuid.UUID = matching_ownership_setup["user_b"]
    sp_a: SearchProfile = matching_ownership_setup["sp_a"]
    job: Job = matching_ownership_setup["job"]
    match_repo: InMemoryMatchResultRepository = matching_ownership_setup["match_repo"]

    # User B attempts to evaluate match with User A's SearchProfile
    resp = client.post(
        "/api/matches",
        json={"job_id": str(job.id), "search_profile_id": str(sp_a.id)},
        headers={"X-User-Id": str(user_b)},
    )

    # Must return 404 Not Found to prevent information disclosure
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in resp.json()["detail"].lower()

    # Verify no MatchResult was created or stored in repository
    assert len(match_repo.records) == 0


# ============================================================================
# 2. Authorized Matching with Real Profile Evidence
# ============================================================================


def test_authorized_match_connects_real_profile_data(
    matching_ownership_setup,
) -> None:
    """Authorized User A evaluates match and receives evidence from real BaseProfile."""
    client: TestClient = matching_ownership_setup["client"]
    user_a: uuid.UUID = matching_ownership_setup["user_a"]
    bp_a: BaseProfile = matching_ownership_setup["bp_a"]
    sp_a: SearchProfile = matching_ownership_setup["sp_a"]
    job: Job = matching_ownership_setup["job"]
    match_repo: InMemoryMatchResultRepository = matching_ownership_setup["match_repo"]

    resp = client.post(
        "/api/matches",
        json={"job_id": str(job.id), "search_profile_id": str(sp_a.id)},
        headers={"X-User-Id": str(user_a)},
    )

    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    # Core attributes
    assert data["job_id"] == str(job.id)
    assert data["base_profile_id"] == str(bp_a.id)
    assert data["search_profile_id"] == str(sp_a.id)
    assert float(data["overall_score"]) > 0.0
    assert float(data["confidence"]) > 0.0

    # Verify categories evaluated
    cat_scores = data["category_scores"]
    assert "SKILLS" in cat_scores
    assert "EXPERIENCE" in cat_scores
    assert "ROLE" in cat_scores
    assert "LOCATION_WORK_MODE" in cat_scores
    assert "EDUCATION" in cat_scores

    # Verify skill requirements cite real profile evidence
    req_matches = data["requirement_matches"]

    # "Python" evidence comes from BaseProfile.skills
    py_matches = [
        rm
        for rm in req_matches
        if rm.get("evidence") and "BaseProfile.skills" in rm["evidence"]
    ]
    assert len(py_matches) >= 1
    assert py_matches[0]["match_status"] == "MATCHED"

    # "FastAPI" evidence comes from ProfileExperience
    fastapi_matches = [
        rm
        for rm in req_matches
        if rm.get("evidence") and "ProfileExperience (Fintech Corp)" in rm["evidence"]
    ]
    assert len(fastapi_matches) >= 1
    assert fastapi_matches[0]["match_status"] == "MATCHED"

    # "PostgreSQL" evidence comes from ProfileProject
    postgres_matches = [
        rm
        for rm in req_matches
        if rm.get("evidence") and "ProfileProject (Job Scope)" in rm["evidence"]
    ]
    assert len(postgres_matches) >= 1
    assert postgres_matches[0]["match_status"] == "MATCHED"

    # "AWS" evidence comes from SearchProfile.target_skills
    aws_matches = [
        rm
        for rm in req_matches
        if rm.get("evidence") and "SearchProfile.target_skills" in rm["evidence"]
    ]
    assert len(aws_matches) >= 1
    assert aws_matches[0]["match_status"] == "MATCHED"

    # Verify explanation contains real skills matched
    explanation = data["explanation"]
    assert explanation is not None
    assert "Python" in explanation["matched_skills"]
    assert "FastAPI" in explanation["matched_skills"]
    assert "PostgreSQL" in explanation["matched_skills"]
    assert "AWS" in explanation["matched_skills"]

    # Verify persisted in repository
    persisted = match_repo.records.get((job.id, sp_a.id))
    assert persisted is not None
    assert persisted.base_profile_id == bp_a.id


# ============================================================================
# 3. Production Authentication Protection (401)
# ============================================================================


def test_production_unauthenticated_match_blocked(
    matching_ownership_setup,
) -> None:
    """In production environment, unauthenticated POST /api/matches returns 401."""
    app = matching_ownership_setup["app"]
    job: Job = matching_ownership_setup["job"]
    sp_a: SearchProfile = matching_ownership_setup["sp_a"]

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
    resp = prod_client.post(
        "/api/matches",
        json={"job_id": str(job.id), "search_profile_id": str(sp_a.id)},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# 4. Service-Level Direct Ownership Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_service_level_ownership_enforcement(
    matching_ownership_setup,
) -> None:
    """MatchingService directly rejects cross-user or missing profile requests."""
    service: MatchingService = matching_ownership_setup["service"]
    user_a: uuid.UUID = matching_ownership_setup["user_a"]
    user_b: uuid.UUID = matching_ownership_setup["user_b"]
    sp_a: SearchProfile = matching_ownership_setup["sp_a"]
    job: Job = matching_ownership_setup["job"]

    # User B attempting to match with User A's SearchProfile
    # must raise SearchProfileNotFoundError
    with pytest.raises(SearchProfileNotFoundError):
        await service.match_job(
            job_id=job.id,
            search_profile_id=sp_a.id,
            user_id=user_b,
        )

    # Non-existent user
    with pytest.raises(SearchProfileNotFoundError):
        await service.match_job(
            job_id=job.id,
            search_profile_id=sp_a.id,
            user_id=uuid.uuid4(),
        )

    # Non-existent job
    with pytest.raises(JobNotFoundError):
        await service.match_job(
            job_id=uuid.uuid4(),
            search_profile_id=sp_a.id,
            user_id=user_a,
        )

    # Authorized user succeeds
    res = await service.match_job(
        job_id=job.id,
        search_profile_id=sp_a.id,
        user_id=user_a,
    )
    assert res is not None
    assert res.deterministic_score > Decimal("0.00")
