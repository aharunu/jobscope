"""Persistence tests for child profile repositories and protocol conformance."""

from __future__ import annotations

import sys
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.profile.entities import (
    BaseProfile,
    ProfileEducation,
    ProfileExperience,
    ProfileProject,
    ProfileSkill,
)
from backend.domain.profile.repositories import (
    ProfileEducationRepository,
    ProfileExperienceRepository,
    ProfileProjectRepository,
    ProfileSkillRepository,
)
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.repositories.base_profile_repository import (
    SQLAlchemyBaseProfileRepository,
)
from backend.infrastructure.database.repositories.profile_child_repositories import (
    SQLAlchemyProfileEducationRepository,
    SQLAlchemyProfileExperienceRepository,
    SQLAlchemyProfileProjectRepository,
    SQLAlchemyProfileSkillRepository,
)

# ============================================================================
# 1. Protocol Conformance & Clean Architecture Independence
# ============================================================================


def test_child_repository_protocol_independence() -> None:
    """Verify domain repository protocols have zero SQLAlchemy dependencies."""
    mod = sys.modules.get("backend.domain.profile.repositories")
    assert mod is not None
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"{attr_name} imports from SQLAlchemy"
            )


def test_child_repositories_satisfy_protocols() -> None:
    """Verify concrete SQLAlchemy repositories satisfy domain repository protocols."""
    mock_session = AsyncMock(spec=AsyncSession)

    skill_repo = SQLAlchemyProfileSkillRepository(mock_session)
    assert isinstance(skill_repo, ProfileSkillRepository)

    exp_repo = SQLAlchemyProfileExperienceRepository(mock_session)
    assert isinstance(exp_repo, ProfileExperienceRepository)

    edu_repo = SQLAlchemyProfileEducationRepository(mock_session)
    assert isinstance(edu_repo, ProfileEducationRepository)

    proj_repo = SQLAlchemyProfileProjectRepository(mock_session)
    assert isinstance(proj_repo, ProfileProjectRepository)


# ============================================================================
# 2. Database Integration Tests (Transactional Session with Rollback)
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
async def test_child_repositories_persistence_crud_and_scoping(
    pg_session: AsyncSession,
) -> None:
    """Verify child repositories execute CRUD with strict base_profile_id scoping."""
    # 1. Provision user and base profile
    user_id = uuid.uuid4()
    pg_session.add(UserModel(id=user_id))
    await pg_session.flush()

    bp_repo = SQLAlchemyBaseProfileRepository(pg_session)
    profile = await bp_repo.save(
        BaseProfile(user_id=user_id, name="Test Integration Candidate")
    )
    profile_id = profile.id
    other_profile_id = uuid.uuid4()

    # 2. Skill Repository CRUD & Scoping
    skill_repo = SQLAlchemyProfileSkillRepository(pg_session)
    skill = ProfileSkill(
        base_profile_id=profile_id,
        name="PostgreSQL",
        category="Databases",
        years_of_experience=Decimal("4.0"),
        level="Senior",
    )
    saved_skill = await skill_repo.save(skill)
    assert saved_skill.id == skill.id

    # Retrieve with correct profile
    fetched_skill = await skill_repo.get_by_id_and_profile_id(skill.id, profile_id)
    assert fetched_skill is not None
    assert fetched_skill.name == "PostgreSQL"

    # Query with cross-profile id must return None
    cross_skill = await skill_repo.get_by_id_and_profile_id(skill.id, other_profile_id)
    assert cross_skill is None

    # Delete with wrong profile must fail
    wrong_del = await skill_repo.delete(skill.id, other_profile_id)
    assert wrong_del is False
    assert await skill_repo.get_by_id_and_profile_id(skill.id, profile_id) is not None

    # Delete with correct profile
    right_del = await skill_repo.delete(skill.id, profile_id)
    assert right_del is True
    assert await skill_repo.get_by_id_and_profile_id(skill.id, profile_id) is None

    # 3. Experience Repository CRUD
    exp_repo = SQLAlchemyProfileExperienceRepository(pg_session)
    exp = ProfileExperience(
        base_profile_id=profile_id,
        company="TechCorp",
        title="DevOps Engineer",
        start_date=date(2021, 1, 1),
        is_current=True,
        skills_used=["Docker", "Kubernetes"],
    )
    saved_exp = await exp_repo.save(exp)
    assert saved_exp.company == "TechCorp"
    assert await exp_repo.get_by_id_and_profile_id(exp.id, profile_id) is not None
    assert await exp_repo.get_by_id_and_profile_id(exp.id, other_profile_id) is None

    # 4. Education Repository CRUD
    edu_repo = SQLAlchemyProfileEducationRepository(pg_session)
    edu = ProfileEducation(
        base_profile_id=profile_id,
        school="METU",
        degree="B.S.",
        field_of_study="Electrical Engineering",
        start_year=2015,
        end_year=2019,
    )
    saved_edu = await edu_repo.save(edu)
    assert saved_edu.school == "METU"
    assert await edu_repo.get_by_id_and_profile_id(edu.id, profile_id) is not None

    # 5. Project Repository CRUD
    proj_repo = SQLAlchemyProfileProjectRepository(pg_session)
    proj = ProfileProject(
        base_profile_id=profile_id,
        title="Distributed Queue",
        skills_used=["Go", "Redis"],
    )
    saved_proj = await proj_repo.save(proj)
    assert saved_proj.title == "Distributed Queue"
    assert await proj_repo.get_by_id_and_profile_id(proj.id, profile_id) is not None
