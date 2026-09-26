"""Unit tests for JobRepository query and detail operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)


def _make_dummy_orm_job(
    job_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    title: str = "Senior Python Engineer",
    company: str = "Acme Corp",
    location: str | None = "Remote",
    work_mode: str | None = "Remote",
    employment_type: str | None = "Full-time",
    status: JobStatus = JobStatus.ACTIVE,
    with_source: bool = True,
) -> JobModel:
    j_id = job_id or uuid.uuid4()
    s_id = source_id or uuid.uuid4()
    orm_job = JobModel(
        id=j_id,
        source_id=s_id,
        canonical_url=f"https://jobs.example.com/{j_id}",
        company=company,
        title=title,
        description="Build scalable services",
        responsibilities="Design APIs",
        location=location,
        work_mode=work_mode,
        employment_type=employment_type,
        salary="$150k-$180k",
        published_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        first_seen_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        closed_at=None,
        status=status,
        content_hash="hash_12345",
        created_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
    )
    if with_source:
        source_orm = SourceModel(
            id=s_id,
            name="Acme Lever Board",
            url="https://jobs.lever.co/acme",
            company="Acme Corp",
            ats_type="lever",
        )
        orm_job.source = source_orm
    return orm_job


@pytest.mark.asyncio
async def test_regression_get_by_id_remains_lightweight_session_get() -> None:
    """Regression test: get_by_id MUST call session.get and NOT a joined query."""
    mock_session = AsyncMock(spec=AsyncSession)
    job_id = uuid.uuid4()
    orm_job = _make_dummy_orm_job(job_id=job_id, with_source=False)
    mock_session.get.return_value = orm_job

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_by_id(job_id)

    assert result is not None
    assert result.id == job_id
    mock_session.get.assert_awaited_once_with(JobModel, job_id)
    # session.execute must NOT be called by get_by_id
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_job_detail_found_with_source_projection() -> None:
    """Verify get_job_detail executes joined query and projects source metadata."""
    mock_session = AsyncMock(spec=AsyncSession)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    orm_job = _make_dummy_orm_job(job_id=job_id, source_id=source_id, with_source=True)

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_job
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_job_detail(job_id)

    assert result is not None
    assert result.id == job_id
    assert result.source_id == source_id
    assert result.source_name == "Acme Lever Board"
    assert result.ats_type == "lever"
    assert result.source_url == "https://jobs.lever.co/acme"

    # Verify query had where clause for job_id
    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "WHERE jobs.id =" in compiled


@pytest.mark.asyncio
async def test_get_job_detail_not_found() -> None:
    """Verify get_job_detail returns None when job is nonexistent."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_job_detail(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_list_jobs_without_filters() -> None:
    """Verify list_jobs builds query without filters and applies deterministic order."""
    mock_session = AsyncMock(spec=AsyncSession)
    orm_job = _make_dummy_orm_job()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orm_job]
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    jobs = await repo.list_jobs(limit=25, offset=10)

    assert len(jobs) == 1
    assert jobs[0].id == orm_job.id

    mock_session.execute.assert_awaited_once()
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "ORDER BY jobs.first_seen_at DESC, jobs.id DESC" in compiled
    assert "LIMIT" in compiled
    assert "OFFSET" in compiled


@pytest.mark.asyncio
async def test_list_jobs_with_all_filters() -> None:
    """Verify list_jobs handles all filters and q substring search."""
    mock_session = AsyncMock(spec=AsyncSession)
    source_id = uuid.uuid4()
    orm_job = _make_dummy_orm_job(source_id=source_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orm_job]
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    jobs = await repo.list_jobs(
        status=JobStatus.ACTIVE,
        source_id=source_id,
        ats_type="lever",
        company="Acme",
        location="Remote",
        work_mode="Remote",
        employment_type="Full-time",
        search_query="Engineer",
        limit=50,
        offset=0,
    )

    assert len(jobs) == 1
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    # Verify join with sources on source_id
    assert "JOIN sources" in compiled
    assert "sources.ats_type =" in compiled
    assert "jobs.status =" in compiled
    assert "jobs.source_id =" in compiled
    assert "jobs.company =" in compiled
    assert "jobs.location =" in compiled
    assert "jobs.work_mode =" in compiled
    assert "jobs.employment_type =" in compiled
    # Verify q substring matching using ILIKE
    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.title) LIKE lower(", "jobs.title ILIKE")
    )
    assert any(
        pattern in compiled
        for pattern in ("lower(jobs.company) LIKE lower(", "jobs.company ILIKE")
    )


@pytest.mark.asyncio
async def test_count_jobs_with_identical_filters() -> None:
    """Verify count_jobs applies identical filter criteria as list_jobs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_session.execute.return_value = mock_result

    source_id = uuid.uuid4()
    repo = SQLAlchemyJobRepository(mock_session)
    count = await repo.count_jobs(
        status=JobStatus.ACTIVE,
        source_id=source_id,
        ats_type="lever",
        company="Acme",
        location="Remote",
        work_mode="Remote",
        employment_type="Full-time",
        search_query="Backend",
    )

    assert count == 42
    called_stmt = mock_session.execute.call_args[0][0]
    compiled = str(called_stmt.compile(compile_kwargs={"literal_binds": False}))

    assert "count(jobs.id)" in compiled
    assert "JOIN sources" in compiled
    assert "sources.ats_type =" in compiled
    assert "jobs.status =" in compiled
    assert "jobs.source_id =" in compiled
    assert "jobs.company =" in compiled
    assert "jobs.location =" in compiled
    assert "jobs.work_mode =" in compiled
    assert "jobs.employment_type =" in compiled
