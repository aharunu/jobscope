"""Regression tests for normalized Work Mode filtering in JobRepository.

Verifies:
1. work_mode="On-site", "on-site", "ONSITE", " onsite " matches DB "onsite" records.
2. work_mode="Hybrid", "hybrid", "HYBRID" matches DB "HYBRID" records.
3. work_mode="Remote", "remote", "REMOTE" matches DB "remote"/"Remote" records.
4. work_mode=None records are never returned by any explicit work_mode filter.
5. list_jobs() and count_jobs() maintain identical filtering logic.
6. When work_mode filter is omitted, all records are returned.
7. Multi-filter combinations (work_mode + status, company, etc.) work correctly.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.job.entities import Job
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)

# ==============================================================================
# 1. SQL Query Compilation & Clean Mode Parameter Binding Tests (Unit)
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_mode", "expected_clean_mode"),
    [
        ("On-site", "onsite"),
        ("on-site", "onsite"),
        ("ONSITE", "onsite"),
        ("  onsite  ", "onsite"),
        ("  On-Site  ", "onsite"),
        ("Hybrid", "hybrid"),
        ("HYBRID", "hybrid"),
        ("hybrid", "hybrid"),
        ("Remote", "remote"),
        ("REMOTE", "remote"),
        ("remote", "remote"),
    ],
)
async def test_repository_list_jobs_clean_mode_parameter_binding(
    input_mode: str,
    expected_clean_mode: str,
) -> None:
    """Verify list_jobs normalizes input work_mode and generates SQL."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.list_jobs(work_mode=input_mode)

    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    # Verify SQL uses replace and lower
    assert "replace(lower(jobs.work_mode)" in compiled.lower()

    # Verify bound parameter value matches clean_mode
    params = called_stmt.compile().params
    assert expected_clean_mode in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_mode", "expected_clean_mode"),
    [
        ("On-site", "onsite"),
        ("on-site", "onsite"),
        ("ONSITE", "onsite"),
        ("Hybrid", "hybrid"),
        ("HYBRID", "hybrid"),
        ("Remote", "remote"),
        ("REMOTE", "remote"),
    ],
)
async def test_repository_count_jobs_clean_mode_parameter_binding(
    input_mode: str,
    expected_clean_mode: str,
) -> None:
    """Verify count_jobs normalizes input work_mode identically to list_jobs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.count_jobs(work_mode=input_mode)

    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert "count(jobs.id)" in compiled
    assert "replace(lower(jobs.work_mode)" in compiled.lower()

    params = called_stmt.compile().params
    assert expected_clean_mode in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize("blank_mode", [None, "", "   ", "\t"])
async def test_repository_omitted_work_mode_adds_no_filter(
    blank_mode: str | None,
) -> None:
    """Verify None or whitespace work_mode does NOT add a work_mode WHERE clause."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.list_jobs(work_mode=blank_mode)

    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "replace(lower(jobs.work_mode)" not in compiled.lower()


# ==============================================================================
# 2. Database Integration Tests with Varied Work Mode Values
# ==============================================================================


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
async def test_live_work_mode_filter_integration(pg_session: AsyncSession) -> None:
    """Verify end-to-end work_mode filtering against actual database records.

    Tests that raw ATS casing ("onsite", "HYBRID", "Remote", NULL) correctly
    interacts with user input ("On-site", "Hybrid", "Remote").
    """
    repo = SQLAlchemyJobRepository(pg_session)
    source_id = uuid.uuid4()
    now = datetime(2026, 9, 29, 20, 0, 0, tzinfo=UTC)

    # Insert a dummy source to satisfy FK constraint
    source = SourceModel(
        id=source_id,
        name="Test Regression Board",
        url="https://jobs.example.com/board",
        ats_type="lever",
        company="Test Company",
    )
    pg_session.add(source)
    await pg_session.flush()

    # Seed 4 jobs with distinct work_mode variants:
    # 1. "onsite" (lowercase, no hyphen - typical Lever)
    job_onsite = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Dream Studios",
        title="Game Developer",
        description="Onsite role",
        location="Istanbul",
        work_mode="onsite",
        content_hash="h1",
        first_seen_at=now,
    )
    # 2. "HYBRID" (all uppercase)
    job_hybrid = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Nexus AI",
        title="ML Engineer",
        description="Hybrid role",
        location="Ankara",
        work_mode="HYBRID",
        content_hash="h2",
        first_seen_at=now,
    )
    # 3. "Remote" (Title-Case)
    job_remote = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Cloud Global",
        title="DevOps Lead",
        description="Remote role",
        location="Worldwide",
        work_mode="Remote",
        content_hash="h3",
        first_seen_at=now,
    )
    # 4. None (NULL - typical Greenhouse without workplaceType)
    job_null = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Good Games",
        title="2D Artist",
        description="No work_mode metadata",
        location="Istanbul (Remote)",
        work_mode=None,
        content_hash="h4",
        first_seen_at=now,
    )

    await repo.save_bulk([job_onsite, job_hybrid, job_remote, job_null])

    # 1. Test On-site variations against DB "onsite"
    for input_val in ["On-site", "on-site", "ONSITE", "onsite", " On-site "]:
        results = await repo.list_jobs(source_id=source_id, work_mode=input_val)
        count = await repo.count_jobs(source_id=source_id, work_mode=input_val)
        assert len(results) == 1, f"Failed for input_val={input_val}"
        assert count == 1
        assert results[0].id == job_onsite.id
        assert results[0].work_mode == "onsite"

    # 2. Test Hybrid variations against DB "HYBRID"
    for input_val in ["Hybrid", "hybrid", "HYBRID", " Hybrid "]:
        results = await repo.list_jobs(source_id=source_id, work_mode=input_val)
        count = await repo.count_jobs(source_id=source_id, work_mode=input_val)
        assert len(results) == 1, f"Failed for input_val={input_val}"
        assert count == 1
        assert results[0].id == job_hybrid.id
        assert results[0].work_mode == "HYBRID"

    # 3. Test Remote variations against DB "Remote"
    for input_val in ["Remote", "remote", "REMOTE", " Remote "]:
        results = await repo.list_jobs(source_id=source_id, work_mode=input_val)
        count = await repo.count_jobs(source_id=source_id, work_mode=input_val)
        assert len(results) == 1, f"Failed for input_val={input_val}"
        assert count == 1
        assert results[0].id == job_remote.id
        assert results[0].work_mode == "Remote"

    # 4. Verify NULL work_mode is NEVER returned when any work_mode filter is set
    for mode in ["On-site", "Hybrid", "Remote", "onsite", "HYBRID"]:
        results = await repo.list_jobs(source_id=source_id, work_mode=mode)
        returned_ids = [j.id for j in results]
        assert job_null.id not in returned_ids

    # 5. Verify all 4 jobs returned when work_mode is None
    all_jobs = await repo.list_jobs(source_id=source_id, work_mode=None)
    all_count = await repo.count_jobs(source_id=source_id, work_mode=None)
    assert len(all_jobs) == 4
    assert all_count == 4
    assert {j.id for j in all_jobs} == {
        job_onsite.id,
        job_hybrid.id,
        job_remote.id,
        job_null.id,
    }

    # 6. Verify multi-filter: work_mode="On-site" AND company="Dream Studios"
    filtered = await repo.list_jobs(
        source_id=source_id, work_mode="On-site", company="Dream Studios"
    )
    assert len(filtered) == 1
    assert filtered[0].id == job_onsite.id

    # Non-matching multi-filter: work_mode="On-site" AND company="Nexus AI" -> 0
    non_matching = await repo.list_jobs(
        source_id=source_id, work_mode="On-site", company="Nexus AI"
    )
    assert len(non_matching) == 0
