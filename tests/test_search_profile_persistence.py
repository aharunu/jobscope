"""Persistence tests for SearchProfile repository and protocol conformance."""

from __future__ import annotations

import sys
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.base_profile import (
    BaseProfileModel,
)
from backend.infrastructure.database.models.search_profile import (
    SearchProfileModel,
)
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.repositories.base_profile_repository import (
    SQLAlchemyBaseProfileRepository,
)
from backend.infrastructure.database.repositories.search_profile_repository import (
    SQLAlchemySearchProfileRepository,
)

# ============================================================================
# 1. Protocol Conformance & Clean Architecture Independence
# ============================================================================


def test_search_profile_repository_protocol_independence() -> None:
    """Verify domain repository protocol has zero SQLAlchemy dependencies."""
    mod = sys.modules.get("backend.domain.search_profile.repositories")
    assert mod is not None
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"{attr_name} imports from SQLAlchemy"
            )


def test_search_profile_repository_satisfies_protocol() -> None:
    """Verify concrete SQLAlchemy repository satisfies domain protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemySearchProfileRepository(mock_session)
    assert isinstance(repo, SearchProfileRepository)


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
async def test_search_profile_repository_crud_flow(pg_session: AsyncSession) -> None:
    """Verify full CRUD lifecycle via SQLAlchemySearchProfileRepository."""
    # 1. Setup User and Base Profile
    user_id = uuid.uuid4()
    user = UserModel(id=user_id)
    pg_session.add(user)
    await pg_session.flush()

    bp_repo = SQLAlchemyBaseProfileRepository(pg_session)
    bp = await bp_repo.save(BaseProfile(user_id=user.id, name="Test Candidate"))

    sp_repo = SQLAlchemySearchProfileRepository(pg_session)

    # 2. Create Search Profile
    sp = SearchProfile(
        base_profile_id=bp.id,
        name="Backend Lead",
        target_roles=["Backend Lead", "Staff Engineer"],
        seniority="lead",
        target_skills=["Python", "PostgreSQL", "Kafka"],
        locations=["London", "Remote"],
        work_modes=["remote", "hybrid"],
        industries=["Fintech"],
        salary_min=Decimal("90000.00"),
        salary_max=Decimal("130000.00"),
    )
    saved = await sp_repo.save(sp)
    assert saved.id == sp.id
    assert saved.name == "Backend Lead"
    assert saved.target_roles == ["Backend Lead", "Staff Engineer"]
    assert saved.salary_min == Decimal("90000.00")

    # 3. Retrieve by ID
    by_id = await sp_repo.get_by_id(saved.id)
    assert by_id is not None
    assert by_id.name == "Backend Lead"

    # 4. Scoped get: matches right base_profile_id
    scoped = await sp_repo.get_by_id_and_base_profile_id(saved.id, bp.id)
    assert scoped is not None
    assert scoped.id == saved.id

    # Scoped get: returns None if wrong base_profile_id
    wrong_scoped = await sp_repo.get_by_id_and_base_profile_id(saved.id, uuid.uuid4())
    assert wrong_scoped is None

    # 5. List by base_profile_id
    sp2 = SearchProfile(
        base_profile_id=bp.id,
        name="Platform Engineer",
        target_roles=["Platform Engineer"],
    )
    await sp_repo.save(sp2)

    all_for_bp = await sp_repo.list_by_base_profile_id(bp.id)
    assert len(all_for_bp) == 2
    assert {p.name for p in all_for_bp} == {"Backend Lead", "Platform Engineer"}

    # Other base profile gets empty list
    other_list = await sp_repo.list_by_base_profile_id(uuid.uuid4())
    assert other_list == []

    # 6. Scoped Delete: returns False on wrong base_profile_id
    del_wrong = await sp_repo.delete(saved.id, uuid.uuid4())
    assert del_wrong is False

    # Scoped Delete: returns True on correct base_profile_id
    del_correct = await sp_repo.delete(saved.id, bp.id)
    assert del_correct is True

    # Confirm deletion
    deleted_check = await sp_repo.get_by_id(saved.id)
    assert deleted_check is None


@pytest.mark.asyncio
async def test_search_profile_cascade_delete(pg_session: AsyncSession) -> None:
    """Verify that deleting a BaseProfile cascades to its SearchProfiles."""
    user_id = uuid.uuid4()
    user = UserModel(id=user_id)
    pg_session.add(user)
    await pg_session.flush()

    bp_repo = SQLAlchemyBaseProfileRepository(pg_session)
    bp = await bp_repo.save(BaseProfile(user_id=user.id, name="Cascade Target"))

    sp_repo = SQLAlchemySearchProfileRepository(pg_session)
    sp = await sp_repo.save(
        SearchProfile(base_profile_id=bp.id, name="Cascade Search Profile")
    )
    assert await sp_repo.get_by_id(sp.id) is not None

    # Delete BaseProfile
    await pg_session.execute(
        delete(BaseProfileModel).where(BaseProfileModel.id == bp.id)
    )
    await pg_session.flush()

    # SearchProfile should be gone via cascade

    stmt = select(SearchProfileModel).where(SearchProfileModel.id == sp.id)
    res = await pg_session.execute(stmt)
    assert res.scalar_one_or_none() is None
