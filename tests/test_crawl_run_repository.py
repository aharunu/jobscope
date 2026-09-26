"""Unit tests for CrawlRunRepository and SQLAlchemyCrawlRunRepository."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.infrastructure.database.models.crawl_run import (
    CrawlRunModel,
)
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)


def test_domain_crawl_repository_independence() -> None:
    """Verify domain repository protocols have zero SQLAlchemy or Alembic imports."""
    mod = sys.modules.get("backend.domain.crawl.repositories")
    assert mod is not None, "backend.domain.crawl.repositories module not loaded"
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"Domain repository imports from SQLAlchemy: {attr_name}"
            )
            assert "alembic" not in attr_val.__module__.lower(), (
                f"Domain repository imports from Alembic: {attr_name}"
            )


def test_crawl_run_repository_protocol_conformance() -> None:
    """Verify SQLAlchemyCrawlRunRepository satisfies CrawlRunRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyCrawlRunRepository(mock_session)
    assert isinstance(repo, CrawlRunRepository)


@pytest.mark.asyncio
async def test_crawl_run_repository_create_run() -> None:
    """Verify create_run adds to session and flushes without committing."""
    mock_session = AsyncMock(spec=AsyncSession)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.RUNNING,
        started_at=datetime.now(UTC),
        jobs_found=10,
    )

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    created = await repo.create_run(run)

    assert created is not None
    assert created.id == run.id
    assert created.status == CrawlStatus.RUNNING
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_crawl_run_repository_update_run() -> None:
    """Verify update_run merges and flushes."""
    mock_session = AsyncMock(spec=AsyncSession)
    run = CrawlRun(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        jobs_found=10,
        jobs_created=8,
        jobs_updated=2,
        finished_at=datetime.now(UTC),
    )

    orm_run = CrawlRunModel.from_domain(run)
    mock_session.merge.return_value = orm_run

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    updated = await repo.update_run(run)

    assert updated is not None
    assert updated.status == CrawlStatus.COMPLETED
    assert updated.jobs_created == 8
    mock_session.merge.assert_awaited_once()
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_crawl_run_repository_get_by_id_found() -> None:
    """Verify get_by_id returns CrawlRun when found."""
    mock_session = AsyncMock(spec=AsyncSession)
    run_id = uuid.uuid4()
    orm_run = CrawlRunModel(
        id=run_id,
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        jobs_found=5,
    )
    mock_session.get.return_value = orm_run

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    result = await repo.get_by_id(run_id)

    assert result is not None
    assert result.id == run_id
    assert result.status == CrawlStatus.COMPLETED
    mock_session.get.assert_awaited_once_with(CrawlRunModel, run_id)


@pytest.mark.asyncio
async def test_crawl_run_repository_get_by_id_not_found() -> None:
    """Verify get_by_id returns None when not found."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_crawl_run_repository_get_latest_by_source() -> None:
    """Verify get_latest_by_source retrieves the latest run."""
    mock_session = AsyncMock(spec=AsyncSession)
    source_id = uuid.uuid4()
    orm_run = CrawlRunModel(
        id=uuid.uuid4(),
        source_id=source_id,
        status=CrawlStatus.COMPLETED,
        jobs_found=3,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_run
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    result = await repo.get_latest_by_source(source_id)

    assert result is not None
    assert result.source_id == source_id
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_crawl_run_repository_record_job_action() -> None:
    """Verify record_job_action merges CrawlRunJobModel and flushes."""
    mock_session = AsyncMock(spec=AsyncSession)
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    await repo.record_job_action(run_id, job_id, CrawlJobAction.CREATED)

    mock_session.merge.assert_awaited_once()
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_crawl_run_repository_record_job_actions_batch() -> None:
    """Verify record_job_actions persists multiple links."""
    mock_session = AsyncMock(spec=AsyncSession)
    run_id = uuid.uuid4()
    links = [
        CrawlRunJob(
            crawl_run_id=run_id, job_id=uuid.uuid4(), action=CrawlJobAction.CREATED
        ),
        CrawlRunJob(
            crawl_run_id=run_id, job_id=uuid.uuid4(), action=CrawlJobAction.UPDATED
        ),
    ]

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    await repo.record_job_actions(links)

    assert mock_session.merge.call_count == 2
    mock_session.flush.assert_awaited_once()
    assert mock_session.commit.call_count == 0
