"""Unit tests for JobRepository and RawJobRepository implementations."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.infrastructure.database.models.job import JobModel, RawJobModel
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)


def test_domain_job_repository_independence() -> None:
    """Verify domain repository protocols have zero SQLAlchemy or Alembic imports."""
    mod = sys.modules.get("backend.domain.job.repositories")
    assert mod is not None, "backend.domain.job.repositories module not loaded"
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"Domain repository imports from SQLAlchemy: {attr_name}"
            )
            assert "alembic" not in attr_val.__module__.lower(), (
                f"Domain repository imports from Alembic: {attr_name}"
            )


def test_job_repository_protocol_conformance() -> None:
    """Verify SQLAlchemyJobRepository satisfies JobRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRepository(mock_session)
    assert isinstance(repo, JobRepository)


def test_raw_job_repository_protocol_conformance() -> None:
    """Verify SQLAlchemyRawJobRepository satisfies RawJobRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyRawJobRepository(mock_session)
    assert isinstance(repo, RawJobRepository)


@pytest.mark.asyncio
async def test_job_repository_get_by_id_found() -> None:
    """Verify get_by_id returns domain Job when found."""
    mock_session = AsyncMock(spec=AsyncSession)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    orm_job = JobModel(
        id=job_id,
        source_id=source_id,
        canonical_url="https://example.com/job/1",
        company="Acme Corp",
        title="Software Engineer",
        description="Write code",
        content_hash="abc123hash",
        status=JobStatus.ACTIVE,
    )
    mock_session.get.return_value = orm_job

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_by_id(job_id)

    assert result is not None
    assert isinstance(result, Job)
    assert result.id == job_id
    assert result.title == "Software Engineer"
    mock_session.get.assert_awaited_once_with(JobModel, job_id)


@pytest.mark.asyncio
async def test_job_repository_get_by_id_not_found() -> None:
    """Verify get_by_id returns None when not found."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_job_repository_get_by_source_and_external_id() -> None:
    """Verify get_by_source_and_external_id filters correctly."""
    mock_session = AsyncMock(spec=AsyncSession)
    source_id = uuid.uuid4()
    ext_id = "ext-456"
    orm_job = JobModel(
        id=uuid.uuid4(),
        source_id=source_id,
        external_job_id=ext_id,
        canonical_url="https://example.com/job/456",
        company="Acme Corp",
        title="Backend Engineer",
        description="Write async python",
        content_hash="hash456",
        status=JobStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_job
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_by_source_and_external_id(source_id, ext_id)

    assert result is not None
    assert result.external_job_id == ext_id
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_job_repository_get_by_canonical_url() -> None:
    """Verify get_by_canonical_url queries by URL."""
    mock_session = AsyncMock(spec=AsyncSession)
    test_url = "https://example.com/jobs/dev-1"
    orm_job = JobModel(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        canonical_url=test_url,
        company="Acme Corp",
        title="Developer",
        description="Development work",
        content_hash="hashdev1",
        status=JobStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_job
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_by_canonical_url(test_url)

    assert result is not None
    assert result.canonical_url == test_url


@pytest.mark.asyncio
async def test_job_repository_save() -> None:
    """Verify save merges model and flushes without committing."""
    mock_session = AsyncMock(spec=AsyncSession)
    job = Job(
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/job/save",
        company="Acme",
        title="QA Engineer",
        description="Test software",
        content_hash="qahash",
    )

    orm_saved = JobModel.from_domain(job)
    mock_session.merge.return_value = orm_saved

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.save(job)

    assert result is not None
    assert result.title == "QA Engineer"
    mock_session.merge.assert_awaited_once()
    mock_session.flush.assert_awaited_once()
    # Transaction boundary invariant: repo never commits
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_job_repository_save_bulk() -> None:
    """Verify save_bulk persists multiple entities and flushes."""
    mock_session = AsyncMock(spec=AsyncSession)
    jobs = [
        Job(
            source_id=uuid.uuid4(),
            canonical_url=f"https://example.com/job/{i}",
            company="Acme",
            title=f"Engineer {i}",
            description="Code",
            content_hash=f"hash{i}",
        )
        for i in range(3)
    ]

    mock_session.merge.side_effect = lambda orm: orm

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.save_bulk(jobs)

    assert len(result) == 3
    assert mock_session.merge.call_count == 3
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_job_repository_count() -> None:
    """Verify count query returns integer."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    count = await repo.count(status=JobStatus.ACTIVE)

    assert count == 42
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_raw_job_repository_save_and_get() -> None:
    """Verify RawJobRepository saves via merge and retrieves by job_id."""
    mock_session = AsyncMock(spec=AsyncSession)
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()

    raw_job = RawJob(
        job_id=job_id,
        source_id=source_id,
        raw_content='{"id": 1}',
        content_type="application/json",
        fetched_at=datetime.now(UTC),
    )

    orm_raw = RawJobModel.from_domain(raw_job)
    mock_session.merge.return_value = orm_raw

    raw_repo = SQLAlchemyRawJobRepository(mock_session)
    saved = await raw_repo.save(raw_job)

    assert saved is not None
    assert saved.job_id == job_id
    mock_session.merge.assert_awaited_once()
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0

    # Test get_by_job_id
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orm_raw]
    mock_session.execute.return_value = mock_result

    history = await raw_repo.get_by_job_id(job_id)
    assert len(history) == 1
    assert history[0].job_id == job_id


@pytest.mark.asyncio
async def test_job_repository_get_active_jobs_by_source() -> None:
    """Verify get_active_jobs_by_source filters by source_id and ACTIVE status."""
    mock_session = AsyncMock(spec=AsyncSession)
    source_id = uuid.uuid4()
    orm_jobs = [
        JobModel(
            id=uuid.uuid4(),
            source_id=source_id,
            canonical_url=f"https://example.com/job/{i}",
            company="Acme Corp",
            title=f"Engineer {i}",
            description="Code",
            content_hash=f"hash{i}",
            status=JobStatus.ACTIVE,
        )
        for i in range(2)
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = orm_jobs
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRepository(mock_session)
    result = await repo.get_active_jobs_by_source(source_id)

    assert len(result) == 2
    assert all(isinstance(j, Job) for j in result)
    assert all(j.status == JobStatus.ACTIVE for j in result)
    assert all(j.source_id == source_id for j in result)
    mock_session.execute.assert_awaited_once()
