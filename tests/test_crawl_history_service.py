"""Unit tests for CrawlHistoryService and Clean Architecture boundaries."""

from __future__ import annotations

import ast
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from backend.application.job_discovery.dtos import (
    CrawlRunFilterDTO,
)
from backend.application.job_discovery.history_service import CrawlHistoryService
from backend.domain.crawl.entities import CrawlRun, CrawlRunJob
from backend.domain.crawl.enums import CrawlJobAction, CrawlStatus
from backend.domain.crawl.repositories import CrawlRunRepository


class MockCrawlRunRepository(CrawlRunRepository):
    """In-memory mock repository implementing CrawlRunRepository protocol."""

    def __init__(self, runs: list[CrawlRun] | None = None) -> None:
        self.runs: list[CrawlRun] = runs or []
        self.jobs: list[CrawlRunJob] = []

    async def create_run(self, run: CrawlRun) -> CrawlRun:
        self.runs.append(run)
        return run

    async def update_run(self, run: CrawlRun) -> CrawlRun:
        for i, r in enumerate(self.runs):
            if r.id == run.id:
                self.runs[i] = run
                return run
        self.runs.append(run)
        return run

    async def get_by_id(self, run_id: uuid.UUID) -> CrawlRun | None:
        for r in self.runs:
            if r.id == run_id:
                return r
        return None

    async def get_run_detail(self, run_id: uuid.UUID) -> CrawlRun | None:
        return await self.get_by_id(run_id)

    async def get_latest_by_source(self, source_id: uuid.UUID) -> CrawlRun | None:
        matching = [r for r in self.runs if r.source_id == source_id]
        if not matching:
            return None
        matching.sort(key=lambda x: x.started_at or datetime.min, reverse=True)
        return matching[0]

    async def list_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRun]:
        res = self.runs
        if source_id is not None:
            res = [r for r in res if r.source_id == source_id]
        if status is not None:
            res = [r for r in res if r.status == status]
        if ats_type is not None:
            res = [r for r in res if r.ats_type == ats_type]
        if date_from is not None:
            res = [r for r in res if (r.created_at or datetime.min) >= date_from]
        if date_to is not None:
            res = [r for r in res if (r.created_at or datetime.min) < date_to]
        return res[offset : offset + limit]

    async def count_runs(
        self,
        source_id: uuid.UUID | None = None,
        status: CrawlStatus | None = None,
        ats_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        runs = await self.list_runs(
            source_id=source_id,
            status=status,
            ats_type=ats_type,
            date_from=date_from,
            date_to=date_to,
            limit=10000,
            offset=0,
        )
        return len(runs)

    async def record_job_action(
        self,
        run_id: uuid.UUID,
        job_id: uuid.UUID,
        action: CrawlJobAction,
    ) -> None:
        self.jobs.append(CrawlRunJob(crawl_run_id=run_id, job_id=job_id, action=action))

    async def record_job_actions(self, links: list[CrawlRunJob]) -> None:
        self.jobs.extend(links)

    async def list_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CrawlRunJob]:
        res = [j for j in self.jobs if j.crawl_run_id == run_id]
        if action is not None:
            res = [j for j in res if j.action == action]
        return res[offset : offset + limit]

    async def count_run_jobs(
        self,
        run_id: uuid.UUID,
        action: CrawlJobAction | None = None,
    ) -> int:
        jobs = await self.list_run_jobs(
            run_id=run_id, action=action, limit=10000, offset=0
        )
        return len(jobs)


# ============================================================================
# 1. Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_list_runs_rejects_limit_over_100() -> None:
    """Verify limit > 100 raises ValueError."""
    service = CrawlHistoryService(MockCrawlRunRepository())
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        await service.list_runs(CrawlRunFilterDTO(limit=101))


@pytest.mark.asyncio
async def test_list_runs_rejects_limit_under_1() -> None:
    """Verify limit < 1 raises ValueError."""
    service = CrawlHistoryService(MockCrawlRunRepository())
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        await service.list_runs(CrawlRunFilterDTO(limit=0))


@pytest.mark.asyncio
async def test_list_runs_rejects_negative_offset() -> None:
    """Verify negative offset raises ValueError."""
    service = CrawlHistoryService(MockCrawlRunRepository())
    with pytest.raises(ValueError, match="Offset must be non-negative"):
        await service.list_runs(CrawlRunFilterDTO(offset=-1))


@pytest.mark.asyncio
async def test_list_runs_rejects_invalid_date_range() -> None:
    """Verify date_from > date_to raises ValueError."""
    service = CrawlHistoryService(MockCrawlRunRepository())
    now = datetime.now(UTC)
    with pytest.raises(ValueError, match="date_from must not be later than date_to"):
        await service.list_runs(
            CrawlRunFilterDTO(date_from=now, date_to=now - timedelta(hours=1))
        )


@pytest.mark.asyncio
async def test_list_run_jobs_rejects_invalid_pagination() -> None:
    """Verify list_run_jobs validates limit and offset boundaries."""
    service = CrawlHistoryService(MockCrawlRunRepository())
    run_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Limit must be between 1 and 100"):
        await service.list_run_jobs(run_id=run_id, limit=150)

    with pytest.raises(ValueError, match="Offset must be non-negative"):
        await service.list_run_jobs(run_id=run_id, offset=-5)


# ============================================================================
# 2. Duration and Metrics Calculations
# ============================================================================


@pytest.mark.asyncio
async def test_duration_calculated_for_completed_run() -> None:
    """Verify duration_ms is derived from finished_at - started_at."""
    start = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)
    finish = datetime(2026, 9, 26, 12, 0, 3, 500000, tzinfo=UTC)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        started_at=start,
        finished_at=finish,
        created_at=start,
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=0,
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))
    items, total = await service.list_runs(CrawlRunFilterDTO())

    assert total == 1
    assert len(items) == 1
    summary = items[0]
    assert summary.duration_ms == 3500.0
    assert summary.jobs_unchanged == 2  # 10 - 6 - 2 - 0 - 0 = 2


@pytest.mark.asyncio
async def test_jobs_unchanged_derivation_with_errors() -> None:
    """Verify jobs_unchanged derivation accounts for error_count."""
    start = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)
    finish = datetime(2026, 9, 26, 12, 0, 5, tzinfo=UTC)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.PARTIAL,
        started_at=start,
        finished_at=finish,
        created_at=start,
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=0,
        error_count=1,
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))
    items, total = await service.list_runs(CrawlRunFilterDTO())

    assert total == 1
    assert len(items) == 1
    summary = items[0]
    # 10 - 6 - 2 - 0 - 1 = 1
    assert summary.jobs_unchanged == 1


@pytest.mark.asyncio
async def test_jobs_unchanged_derivation_zero_errors() -> None:
    """Verify jobs_unchanged derivation when error_count is zero."""
    start = datetime(2026, 9, 26, 12, 0, 0, tzinfo=UTC)
    finish = datetime(2026, 9, 26, 12, 0, 5, tzinfo=UTC)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        started_at=start,
        finished_at=finish,
        created_at=start,
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=0,
        error_count=0,
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))
    items, total = await service.list_runs(CrawlRunFilterDTO())

    assert total == 1
    assert len(items) == 1
    summary = items[0]
    # 10 - 6 - 2 - 0 - 0 = 2
    assert summary.jobs_unchanged == 2


@pytest.mark.asyncio
async def test_jobs_unchanged_derivation_ignores_jobs_closed() -> None:
    """Verify jobs_closed does not reduce jobs_unchanged."""
    start = datetime.now(UTC)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        started_at=start,
        finished_at=start + timedelta(seconds=1),
        created_at=start,
        jobs_found=10,
        jobs_created=6,
        jobs_updated=2,
        jobs_closed=5,  # 5 absent jobs were closed
        error_count=1,
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))
    items, total = await service.list_runs(CrawlRunFilterDTO())

    assert total == 1
    # 10 (discovered) - 6 (created) - 2 (updated) - 1 (error) = 1 unchanged.
    # jobs_closed (5) must NOT reduce jobs_unchanged.
    assert items[0].jobs_unchanged == 1
    assert items[0].jobs_closed == 5
    assert items[0].jobs_found == 10


@pytest.mark.asyncio
async def test_duration_is_none_for_running_run() -> None:
    """Verify duration_ms is None for RUNNING status runs."""
    start = datetime.now(UTC)
    run = CrawlRun(
        source_id=uuid.uuid4(),
        status=CrawlStatus.RUNNING,
        started_at=start,
        finished_at=None,
        created_at=start,
        jobs_found=0,
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))
    items, _ = await service.list_runs(CrawlRunFilterDTO())

    assert len(items) == 1
    assert items[0].duration_ms is None


@pytest.mark.asyncio
async def test_get_run_found_and_not_found() -> None:
    """Verify get_run returns summary DTO when found and None when absent."""
    run_id = uuid.uuid4()
    run = CrawlRun(
        id=run_id,
        source_id=uuid.uuid4(),
        status=CrawlStatus.COMPLETED,
        source_name="Trendyol",
        ats_type="lever",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    service = CrawlHistoryService(MockCrawlRunRepository([run]))

    found = await service.get_run(run_id)
    assert found is not None
    assert found.id == run_id
    assert found.source_name == "Trendyol"
    assert found.ats_type == "lever"

    missing = await service.get_run(uuid.uuid4())
    assert missing is None


# ============================================================================
# 3. Clean Architecture AST Boundary Check
# ============================================================================


def test_clean_architecture_history_service_no_infra_imports() -> None:
    """Verify history_service.py has zero infrastructure, ORM, or web imports."""
    forbidden = ["backend.infrastructure", "sqlalchemy", "fastapi", "httpx"]
    service_file = Path("backend/application/job_discovery/history_service.py")
    tree = ast.parse(service_file.read_text(encoding="utf-8"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert not alias.name.startswith(f), (
                        f"Forbidden import: {alias.name}"
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            for f in forbidden:
                assert not node.module.startswith(f), (
                    f"Forbidden import from: {node.module}"
                )
