"""Tests for matching repositories and persistence idempotency."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.matching.services import MatchingService
from backend.domain.job.enums import JobStatus, RequirementType
from backend.domain.matching.repositories import MatchResultRepository
from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileSkill,
)
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.base_profile import BaseProfileModel
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
)
from backend.infrastructure.database.models.matching import (
    MatchResultModel,
)
from backend.infrastructure.database.models.search_profile import (
    SearchProfileModel,
)
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.repositories.base_profile_repository import (
    SQLAlchemyBaseProfileRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)
from backend.infrastructure.database.repositories.matching_repository import (
    SQLAlchemyMatchResultRepository,
)
from backend.infrastructure.database.repositories.search_profile_repository import (
    SQLAlchemySearchProfileRepository,
)

# ============================================================================
# 1. Domain Independence & Protocol Conformance Tests
# ============================================================================


def test_domain_matching_repository_independence() -> None:
    """Verify repository protocols have zero ORM imports."""
    for mod_name in [
        "backend.domain.matching.repositories",
        "backend.domain.profile.repositories",
        "backend.domain.search_profile.repositories",
    ]:
        mod = sys.modules.get(mod_name)
        assert mod is not None, f"Module {mod_name} not found"
        for attr_name, attr_val in mod.__dict__.items():
            if hasattr(attr_val, "__module__") and attr_val.__module__:
                assert "sqlalchemy" not in attr_val.__module__.lower(), (
                    f"{mod_name}.{attr_name} imports from SQLAlchemy"
                )
                assert "alembic" not in attr_val.__module__.lower(), (
                    f"{mod_name}.{attr_name} imports from Alembic"
                )


def test_repository_protocol_conformance() -> None:
    """Verify concrete SQLAlchemy repositories satisfy their domain Protocols."""
    mock_session = AsyncMock(spec=AsyncSession)

    match_repo = SQLAlchemyMatchResultRepository(mock_session)
    assert isinstance(match_repo, MatchResultRepository)

    bp_repo = SQLAlchemyBaseProfileRepository(mock_session)
    assert isinstance(bp_repo, BaseProfileRepository)

    sp_repo = SQLAlchemySearchProfileRepository(mock_session)
    assert isinstance(sp_repo, SearchProfileRepository)


# ============================================================================
# 2. Database Integration & Idempotency Tests (Real PostgreSQL)
# ============================================================================


@pytest.fixture
async def pg_session():
    """Yield an isolated transactional PostgreSQL session that is always rolled back."""
    engine = create_database_engine()
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    try:
        async with factory() as session:
            await session.execute(select(1))
            yield session
            await session.rollback()
    except Exception as exc:
        pytest.skip(f"PostgreSQL integration database unavailable: {exc}")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_matching_persistence_and_idempotency(pg_session: AsyncSession) -> None:
    """Verify MatchResult persistence, relationship mapping, and idempotent overwrite.

    1. Seeds a full User, BaseProfile, SearchProfile, Source, Job, and JobRequirements.
    2. Runs MatchingService.match_job.
    3. Verifies MatchResultModel and RequirementMatchModel records are persisted.
    4. Runs MatchingService.match_job a second time.
    5. Confirms NO duplicate rows exist in match_results.
    6. Verifies deterministic results are identical.
    """
    now = datetime.now(UTC)

    # 1. Seed User
    user = UserModel(id=uuid.uuid4())
    pg_session.add(user)
    await pg_session.flush()

    # 2. Seed BaseProfile with Skills, Experience, Education
    bp_id = uuid.uuid4()
    bp = BaseProfileModel(
        id=bp_id,
        user_id=user.id,
        name="Jane's Profile",
        summary="Senior Backend Software Engineer with Python expertise.",
    )
    pg_session.add(bp)
    await pg_session.flush()

    # Add profile children
    bp_repo = SQLAlchemyBaseProfileRepository(pg_session)
    base_profile_domain = BaseProfile(
        id=bp_id,
        user_id=user.id,
        name="Jane's Profile",
        skills=[
            ProfileSkill(base_profile_id=bp_id, name="Python"),
            ProfileSkill(base_profile_id=bp_id, name="FastAPI"),
            ProfileSkill(base_profile_id=bp_id, name="PostgreSQL"),
        ],
        experiences=[
            ProfileExperience(
                base_profile_id=bp_id,
                company="Tech Corp",
                title="Backend Engineer",
                start_date=date(2021, 1, 1),
                is_current=True,
            )
        ],
        educations=[
            ProfileEducation(
                base_profile_id=bp_id,
                school="Istanbul Tech",
                degree="Bachelor's Degree",
                field_of_study="Computer Engineering",
            )
        ],
    )
    await bp_repo.save(base_profile_domain)

    # 3. Seed SearchProfile
    sp_id = uuid.uuid4()
    sp = SearchProfileModel(
        id=sp_id,
        base_profile_id=bp_id,
        name="Backend Roles Istanbul",
        target_roles=["Backend Engineer", "Software Engineer"],
        target_skills=["Python", "FastAPI", "PostgreSQL"],
        locations=["Istanbul"],
        work_modes=["Hybrid", "Remote"],
    )
    pg_session.add(sp)
    await pg_session.flush()

    # 4. Seed Source & Job
    source = SourceModel(
        id=uuid.uuid4(),
        name=f"test_src_{uuid.uuid4().hex[:6]}",
        ats_type="lever",
        url="https://jobs.lever.co/example",
        active=True,
    )
    pg_session.add(source)
    await pg_session.flush()

    job_id = uuid.uuid4()
    job = JobModel(
        id=job_id,
        source_id=source.id,
        canonical_url=f"https://jobs.lever.co/example/{job_id}",
        company="Acme Istanbul",
        title="Backend Engineer",
        description="Looking for Python and FastAPI developer.",
        content_hash="test_content_hash_123",
        location="Istanbul",
        work_mode="Hybrid",
        status=JobStatus.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
    )
    pg_session.add(job)
    await pg_session.flush()

    # Seed Job Requirements
    req1 = JobRequirementModel(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="Python programming",
        normalized_skill="Python",
    )
    req2 = JobRequirementModel(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.EXPERIENCE,
        description="2+ years of experience",
    )
    pg_session.add_all([req1, req2])
    await pg_session.flush()

    # 5. Initialize Repositories and MatchingService
    job_repo = SQLAlchemyJobRepository(pg_session)
    sp_repo = SQLAlchemySearchProfileRepository(pg_session)
    match_repo = SQLAlchemyMatchResultRepository(pg_session)

    service = MatchingService(
        job_repo=job_repo,
        base_profile_repo=bp_repo,
        search_profile_repo=sp_repo,
        match_result_repo=match_repo,
    )

    # 6. Execute match evaluation - First Run
    result1 = await service.match_job(
        job_id=job_id, search_profile_id=sp_id, user_id=user.id
    )

    assert result1 is not None
    assert result1.deterministic_score > Decimal("0.00")
    assert result1.confidence > Decimal("0.00")
    assert len(result1.requirement_matches) >= 2

    # Verify directly from database table
    count_stmt = (
        select(func.count())
        .select_from(MatchResultModel)
        .where(
            MatchResultModel.job_id == job_id,
            MatchResultModel.search_profile_id == sp_id,
        )
    )
    count1 = (await pg_session.execute(count_stmt)).scalar_one()
    assert count1 == 1

    # 7. Execute match evaluation - Second Run (Idempotency test)
    result2 = await service.match_job(
        job_id=job_id, search_profile_id=sp_id, user_id=user.id
    )

    # Verify no duplicate row was created
    count2 = (await pg_session.execute(count_stmt)).scalar_one()
    assert count2 == 1, "Duplicate MatchResultModel record created on re-matching!"

    # Verify results are identical
    assert result2.id == result1.id
    assert result2.deterministic_score == result1.deterministic_score
    assert result2.final_score == result1.final_score
    assert result2.confidence == result1.confidence
    assert len(result2.requirement_matches) == len(result1.requirement_matches)
