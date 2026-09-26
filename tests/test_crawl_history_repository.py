"""Unit tests for CrawlRunRepository observability and history queries."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.models.crawl_run import (
    CrawlRunJobModel,
    CrawlRunModel,
)
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)


@pytest.mark.asyncio
async def test_list_runs_with_all_filters_and_ordering() -> None:
    """Verify list_runs builds SQL with filters, joins, and deterministic ordering."""
    mock_session = AsyncMock(spec=AsyncSession)
    source_id = uuid.uuid4()
    run_id = uuid.uuid4()
    d_from = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    d_to = datetime(2026, 9, 30, 23, 59, tzinfo=UTC)

    source_orm = SourceModel(
        id=source_id,
        name="Acme Lever",
        url="https://jobs.lever.co/acme",
        ats_type="lever",
        company="Acme Corp",
    )
    orm_run = CrawlRunModel(
        id=run_id,
        source_id=source_id,
        status=CrawlStatus.COMPLETED,
        jobs_found=10,
        jobs_created=5,
        jobs_updated=2,
        jobs_closed=1,
        started_at=d_from,
        finished_at=d_to,
        created_at=d_from,
    )
    orm_run.source = source_orm

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orm_run]
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    runs = await repo.list_runs(
        source_id=source_id,
        status=CrawlStatus.COMPLETED,
        ats_type="lever",
        date_from=d_from,
        date_to=d_to,
        limit=20,
        offset=5,
    )

    assert len(runs) == 1
    assert runs[0].id == run_id
    assert runs[0].source_name == "Acme Lever"
    assert runs[0].ats_type == "lever"

    # Verify query compilation and ordering
    stmt = mock_session.execute.call_args[0][0]
    sql_str = str(stmt).lower()
    assert "order by crawl_runs.created_at desc, crawl_runs.id desc" in sql_str
    assert "limit :param_" in sql_str or "limit" in sql_str
    assert "offset :param_" in sql_str or "offset" in sql_str
    assert "crawl_runs.source_id =" in sql_str
    assert "crawl_runs.status =" in sql_str
    assert "sources.ats_type =" in sql_str
    assert "crawl_runs.created_at >=" in sql_str
    assert "crawl_runs.created_at <" in sql_str


@pytest.mark.asyncio
async def test_count_runs_filters() -> None:
    """Verify count_runs builds aggregation query with filters and joins."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 14
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    count = await repo.count_runs(
        status=CrawlStatus.FAILED,
        ats_type="greenhouse",
    )

    assert count == 14
    mock_session.execute.assert_awaited_once()
    stmt = mock_session.execute.call_args[0][0]
    sql_str = str(stmt).lower()
    assert "count(crawl_runs.id)" in sql_str
    assert "crawl_runs.status =" in sql_str
    assert "sources.ats_type =" in sql_str


@pytest.mark.asyncio
async def test_get_run_detail_found_and_not_found() -> None:
    """Verify get_run_detail eager-loads source relation and maps projections."""
    mock_session = AsyncMock(spec=AsyncSession)
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()

    source_orm = SourceModel(
        id=source_id,
        name="Trendyol Lever",
        url="https://jobs.lever.co/trendyol",
        ats_type="lever",
        company="Trendyol",
    )
    orm_run = CrawlRunModel(
        id=run_id,
        source_id=source_id,
        status=CrawlStatus.COMPLETED,
        jobs_found=3,
    )
    orm_run.source = source_orm

    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_run
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    detail = await repo.get_run_detail(run_id)

    assert detail is not None
    assert detail.id == run_id
    assert detail.source_name == "Trendyol Lever"
    assert detail.ats_type == "lever"

    # Test not found
    mock_result.scalars.return_value.first.return_value = None
    not_found = await repo.get_run_detail(uuid.uuid4())
    assert not_found is None


@pytest.mark.asyncio
async def test_list_run_jobs_with_action_filter_and_ordering() -> None:
    """Verify list_run_jobs builds deterministic ordering and maps job details."""
    mock_session = AsyncMock(spec=AsyncSession)
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()

    job_orm = JobModel(
        id=job_id,
        source_id=uuid.uuid4(),
        canonical_url="https://example.com/job/101",
        title="Backend Engineer",
        company="Tech Corp",
        location="Remote",
        status=JobStatus.ACTIVE,
        first_seen_at=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 9, 25, 10, 0, tzinfo=UTC),
    )
    link_orm = CrawlRunJobModel(
        crawl_run_id=run_id,
        job_id=job_id,
        action=CrawlJobAction.CREATED,
    )
    link_orm.job = job_orm

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [link_orm]
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    items = await repo.list_run_jobs(
        run_id=run_id,
        action=CrawlJobAction.CREATED,
        limit=10,
        offset=0,
    )

    assert len(items) == 1
    assert items[0].crawl_run_id == run_id
    assert items[0].job_id == job_id
    assert items[0].action == CrawlJobAction.CREATED
    assert items[0].title == "Backend Engineer"
    assert items[0].canonical_url == "https://example.com/job/101"
    assert items[0].company == "Tech Corp"
    assert items[0].location == "Remote"
    assert items[0].job_status == "ACTIVE"

    stmt = mock_session.execute.call_args[0][0]
    sql_str = str(stmt).lower()
    assert "order by crawl_run_jobs.action asc, jobs.title asc, jobs.id asc" in sql_str
    assert "crawl_run_jobs.action =" in sql_str


@pytest.mark.asyncio
async def test_count_run_jobs() -> None:
    """Verify count_run_jobs counts job links with action filter."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 8
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyCrawlRunRepository(mock_session)
    count = await repo.count_run_jobs(
        run_id=uuid.uuid4(),
        action=CrawlJobAction.UPDATED,
    )

    assert count == 8
    mock_session.execute.assert_awaited_once()
    stmt = mock_session.execute.call_args[0][0]
    sql_str = str(stmt).lower()
    assert "count(*)" in sql_str or "count" in sql_str
    assert "crawl_run_jobs.action =" in sql_str
