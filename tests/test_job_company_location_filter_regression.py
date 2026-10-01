"""Regression tests for case-insensitive substring Company and Location filtering.

Covers:
1. company substring: company="Dream" -> Dream Games records
2. company case-insensitive: "dream", "DREAM", "Dream" return identical results
3. company full name: "Dream Games" returns correct records
4. location substring: location="istanbul" -> all matching records
5. location partial: location="Sarıyer" -> "Sarıyer, Istanbul"
6. location case-insensitive: "istanbul" and "Istanbul" return identical results
7. location embedded value: location="Singapore" finds combined locations
8. unknown company/location: 0 results returned
9. empty/whitespace: None, "", "   ", "\\t" add no filter
10. list_jobs() and count_jobs() consistency
11. combined filters: company + location + work_mode (AND logic)
12. combined filters: company + location + status
13. NULL company/location records do not match explicit filters
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)

# ==============================================================================
# 1. SQL Query Compilation & Substring Pattern Binding Unit Tests
# ==============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_company", "expected_pattern"),
    [
        ("Dream", "%Dream%"),
        ("dream", "%dream%"),
        ("Dream Games", "%Dream Games%"),
        ("  OKX  ", "%OKX%"),
    ],
)
async def test_repository_list_jobs_company_pattern_binding(
    input_company: str,
    expected_pattern: str,
) -> None:
    """Verify list_jobs builds ILIKE expression with trimmed substring wildcard."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.list_jobs(company=input_company)

    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.company) LIKE lower(", "jobs.company ILIKE")
    )
    params = called_stmt.compile().params
    assert expected_pattern in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_location", "expected_pattern"),
    [
        ("istanbul", "%istanbul%"),
        ("Sarıyer", "%Sarıyer%"),
        ("Germany", "%Germany%"),
        ("  Singapore  ", "%Singapore%"),
    ],
)
async def test_repository_list_jobs_location_pattern_binding(
    input_location: str,
    expected_pattern: str,
) -> None:
    """Verify list_jobs builds location ILIKE expression with trimmed wildcard."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.list_jobs(location=input_location)

    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.location) LIKE lower(", "jobs.location ILIKE")
    )
    params = called_stmt.compile().params
    assert expected_pattern in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_company", "expected_pattern"),
    [
        ("Dream", "%Dream%"),
        ("dream", "%dream%"),
        ("Dream Games", "%Dream Games%"),
    ],
)
async def test_repository_count_jobs_company_pattern_binding(
    input_company: str,
    expected_pattern: str,
) -> None:
    """Verify count_jobs applies identical ILIKE pattern for company."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.count_jobs(company=input_company)

    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert "count(jobs.id)" in compiled
    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.company) LIKE lower(", "jobs.company ILIKE")
    )
    params = called_stmt.compile().params
    assert expected_pattern in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("input_location", "expected_pattern"),
    [
        ("istanbul", "%istanbul%"),
        ("Singapore", "%Singapore%"),
    ],
)
async def test_repository_count_jobs_location_pattern_binding(
    input_location: str,
    expected_pattern: str,
) -> None:
    """Verify count_jobs applies identical ILIKE pattern for location."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.count_jobs(location=input_location)

    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert "count(jobs.id)" in compiled
    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.location) LIKE lower(", "jobs.location ILIKE")
    )
    params = called_stmt.compile().params
    assert expected_pattern in params.values()


@pytest.mark.asyncio
@pytest.mark.parametrize("blank_val", [None, "", "   ", "\t"])
async def test_repository_omitted_company_and_location_adds_no_filter(
    blank_val: str | None,
) -> None:
    """Verify None or whitespace company/location values do NOT add WHERE clauses."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    await repo.list_jobs(company=blank_val, location=blank_val)

    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert "WHERE" not in compiled
    assert "LIKE" not in compiled
    assert "ILIKE" not in compiled


# ==============================================================================
# 2. Database Integration Tests with PostgreSQL
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
async def test_live_company_location_filter_integration(
    pg_session: AsyncSession,
) -> None:
    """Verify company and location filtering end-to-end against database records."""
    repo = SQLAlchemyJobRepository(pg_session)
    source_id = uuid.uuid4()
    now = datetime(2026, 9, 29, 20, 0, 0, tzinfo=UTC)

    source = SourceModel(
        id=source_id,
        name="Company Location Regression Source",
        url="https://jobs.example.com/co-loc-board",
        ats_type="lever",
        company="Dream Games",
    )
    pg_session.add(source)
    await pg_session.flush()

    # 1. Dream Games in Sarıyer, Istanbul (onsite, ACTIVE)
    job1 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Dream Games",
        title="Senior Game Developer",
        description="Core puzzle mechanics",
        location="Sarıyer, Istanbul",
        work_mode="onsite",
        status=JobStatus.ACTIVE,
        content_hash="co_loc_hash_1",
        first_seen_at=now,
    )
    # 2. Dream Games in Istanbul, Türkiye (HYBRID, ACTIVE)
    job2 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Dream Games",
        title="3D Animator",
        description="Character animations",
        location="Istanbul, Türkiye",
        work_mode="HYBRID",
        status=JobStatus.ACTIVE,
        content_hash="co_loc_hash_2",
        first_seen_at=now,
    )
    # 3. OKX in Hong Kong, Hong Kong SAR; Singapore, Singapore (onsite, ACTIVE)
    job3 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="OKX",
        title="Operations Analyst",
        description="Trading operations",
        location="Hong Kong, Hong Kong SAR; Singapore, Singapore",
        work_mode="onsite",
        status=JobStatus.ACTIVE,
        content_hash="co_loc_hash_3",
        first_seen_at=now,
    )
    # 4. Globex Corporation in Berlin, Germany (Remote, ACTIVE)
    job4 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Globex Corporation",
        title="Backend Engineer",
        description="Data pipelines",
        location="Berlin, Germany",
        work_mode="remote",
        status=JobStatus.ACTIVE,
        content_hash="co_loc_hash_4",
        first_seen_at=now,
    )
    # 5. Dream Games in London, UK (onsite, CLOSED)
    job5 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Dream Games",
        title="Product Lead",
        description="Growth strategy",
        location="London, UK",
        work_mode="onsite",
        status=JobStatus.CLOSED,
        content_hash="co_loc_hash_5",
        first_seen_at=now,
    )
    # 6. Null Location record (onsite, ACTIVE)
    job6 = Job(
        id=uuid.uuid4(),
        source_id=source_id,
        canonical_url=f"https://example.com/jobs/{uuid.uuid4()}",
        company="Mystery Inc",
        title="Stealth Engineer",
        description="Classified",
        location=None,
        work_mode="onsite",
        status=JobStatus.ACTIVE,
        content_hash="co_loc_hash_6",
        first_seen_at=now,
    )

    for j in [job1, job2, job3, job4, job5, job6]:
        await repo.save(j)
    await pg_session.flush()

    # 1. Company substring: "Dream" -> matches job1, job2, job5
    res_company_sub = await repo.list_jobs(company="Dream", source_id=source_id)
    ids_company_sub = {j.id for j in res_company_sub}
    assert ids_company_sub == {job1.id, job2.id, job5.id}

    # 2. Company case-insensitive: "dream", "DREAM", "Dream", "  dReAm  "
    for variant in ["dream", "DREAM", "Dream", "  dReAm  "]:
        res_var = await repo.list_jobs(company=variant, source_id=source_id)
        assert {j.id for j in res_var} == {job1.id, job2.id, job5.id}

    # 3. Company full name: "Dream Games"
    res_company_full = await repo.list_jobs(company="Dream Games", source_id=source_id)
    assert {j.id for j in res_company_full} == {job1.id, job2.id, job5.id}

    # 4. Location substring: "istanbul" -> matches job1 and job2
    res_loc_sub = await repo.list_jobs(location="istanbul", source_id=source_id)
    assert {j.id for j in res_loc_sub} == {job1.id, job2.id}

    # 5. Location partial: "Sarıyer" -> matches job1
    res_loc_part = await repo.list_jobs(location="Sarıyer", source_id=source_id)
    assert {j.id for j in res_loc_part} == {job1.id}

    # 6. Location case-insensitive: "istanbul", "Istanbul", "ISTANBUL", "  iSTanbUl  "
    for loc_var in ["istanbul", "Istanbul", "ISTANBUL", "  iSTanbUl  "]:
        res_loc = await repo.list_jobs(location=loc_var, source_id=source_id)
        assert {j.id for j in res_loc} == {job1.id, job2.id}

    # 7. Location embedded value: "Singapore" in multi-region location string
    res_singapore = await repo.list_jobs(location="Singapore", source_id=source_id)
    assert {j.id for j in res_singapore} == {job3.id}

    # 8. Unknown company / location -> 0 results
    assert await repo.list_jobs(company="NonexistentCorp", source_id=source_id) == []
    assert await repo.count_jobs(company="NonexistentCorp", source_id=source_id) == 0
    assert await repo.list_jobs(location="Atlantis", source_id=source_id) == []
    assert await repo.count_jobs(location="Atlantis", source_id=source_id) == 0

    # 9. Empty/whitespace company and location adds no filter (returns all 6 jobs)
    for blank in [None, "", "   ", "\t"]:
        res_blank = await repo.list_jobs(
            company=blank, location=blank, source_id=source_id
        )
        assert len(res_blank) == 6

    # 10. list_jobs() and count_jobs() consistency across filters
    test_filter_scenarios = [
        {"company": "Dream"},
        {"company": "OKX"},
        {"location": "Istanbul"},
        {"location": "Germany"},
        {"location": "Singapore"},
        {"company": "UnknownCo"},
    ]
    for sc in test_filter_scenarios:
        lst = await repo.list_jobs(source_id=source_id, **sc)
        cnt = await repo.count_jobs(source_id=source_id, **sc)
        assert len(lst) == cnt

    # 11. Combined filters: company="Dream" + location="Istanbul" + work_mode="On-site"
    # Intersects with AND logic:
    # - job1: Dream Games, Sarıyer, Istanbul, onsite -> MATCH
    # - job2: Dream Games, Istanbul, Türkiye, HYBRID -> excluded by work_mode
    # - job5: Dream Games, London, UK, onsite -> excluded by location
    res_combined = await repo.list_jobs(
        company="Dream",
        location="Istanbul",
        work_mode="On-site",
        source_id=source_id,
    )
    assert {j.id for j in res_combined} == {job1.id}
    assert (
        await repo.count_jobs(
            company="Dream",
            location="Istanbul",
            work_mode="On-site",
            source_id=source_id,
        )
        == 1
    )

    # 12. Combined filters: company + location + status
    # company="Dream" + status=ACTIVE -> job1, job2 (job5 is CLOSED)
    res_active_dream = await repo.list_jobs(
        company="Dream", status=JobStatus.ACTIVE, source_id=source_id
    )
    assert {j.id for j in res_active_dream} == {job1.id, job2.id}

    # company="Dream" + status=CLOSED -> job5
    res_closed_dream = await repo.list_jobs(
        company="Dream", status=JobStatus.CLOSED, source_id=source_id
    )
    assert {j.id for j in res_closed_dream} == {job5.id}

    # 13. NULL location record (job6) is never matched by an explicit location filter
    res_null_test = await repo.list_jobs(location="Mystery", source_id=source_id)
    assert {j.id for j in res_null_test} == set()
