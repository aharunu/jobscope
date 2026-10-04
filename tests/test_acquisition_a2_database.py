"""Real PostgreSQL admission, connection lifetime, collision and rollback proof."""

import asyncio
import uuid
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.budget import AcquisitionBudget
from backend.application.job_discovery.crawler_service import CrawlerOrchestrator
from backend.application.job_discovery.dtos import CrawlResultDTO, DiscoveredJobDTO
from backend.application.job_discovery.exceptions import SourceBusyError
from backend.domain.crawl.enums import CrawlStatus
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.ats.factory import create_adapter_registry
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.crawl_persistence import (
    SQLAlchemyCrawlPersistenceManager,
)
from backend.infrastructure.database.crawl_runtime import (
    PostgreSQLCrawlAdmissionGuard,
    SQLAlchemyRuntimeSourceProvider,
)
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.crawl_run import CrawlRunModel
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.http.safe_client import HttpSafeClient


@pytest.fixture
async def db():
    settings = get_settings().model_copy(update={"debug": False})
    engine = create_database_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    sources = [
        Source(
            name="A2 test",
            url=f"https://jobs.lever.co/a2-{uuid.uuid4().hex}",
            ats_type="lever",
            active=True,
        )
        for _ in range(2)
    ]
    try:
        async with factory() as session:
            session.add_all([SourceModel.from_domain(s) for s in sources])
            await session.commit()
        yield engine, factory, sources
    finally:
        async with factory() as session:
            ids = [s.id for s in sources]
            await session.execute(
                delete(CrawlRunModel).where(CrawlRunModel.source_id.in_(ids))
            )
            await session.execute(delete(JobModel).where(JobModel.source_id.in_(ids)))
            await session.execute(delete(SourceModel).where(SourceModel.id.in_(ids)))
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_worker_admission_independent_sources_and_idle_connection(db):
    engine, _, sources = db
    guard1, guard2 = (
        PostgreSQLCrawlAdmissionGuard(engine),
        PostgreSQLCrawlAdmissionGuard(engine),
    )
    a, b = [s.id for s in sources]
    async with guard1.hold(a):
        with pytest.raises(SourceBusyError):
            async with guard2.hold(a):
                pytest.fail("Second worker admitted")
        async with guard2.hold(b):
            pass
        async with engine.connect() as observer:
            # The actual lock-holder session must be idle, not idle-in-transaction.
            rows = (
                await observer.execute(
                    text(
                        "SELECT a.state, a.xact_start FROM pg_locks l "
                        "JOIN pg_stat_activity a ON a.pid=l.pid "
                        "WHERE l.locktype='advisory' AND l.granted "
                        "AND a.datname=current_database()"
                    )
                )
            ).all()
            assert rows and all(
                state == "idle" and start is None for state, start in rows
            )
    async with guard2.hold(a):
        pass
    with pytest.raises(RuntimeError, match="acquisition failed"):
        async with guard1.hold(a):
            raise RuntimeError("acquisition failed")
    async with guard2.hold(a):
        pass


@pytest.mark.asyncio
async def test_lock_released_after_cancellation(db):
    engine, _, sources = db
    started, finish = asyncio.Event(), asyncio.Event()

    async def run():
        async with PostgreSQLCrawlAdmissionGuard(engine).hold(sources[0].id):
            started.set()
            await finish.wait()

    task = asyncio.create_task(run())
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with PostgreSQLCrawlAdmissionGuard(engine).hold(sources[0].id):
        pass


def item(source, identity="1", title="Engineer", url=None):
    return DiscoveredJobDTO(
        external_job_id=identity,
        url=url or f"https://example.com/a2/{source.id}/{identity}",
        title=title,
        raw_content='{"observed":true}',
        content_type="application/json",
        metadata={"description": "Python engineering"},
    )


@pytest.mark.asyncio
async def test_cancelled_crawl_records_failure_and_releases_admission(db):
    engine, factory, sources = db
    started = asyncio.Event()
    never_finished = asyncio.Event()

    class WaitingAdapter:
        ats_type = "lever"

        async def crawl(self, source):
            started.set()
            await never_finished.wait()

    task = asyncio.create_task(
        orchestrator(engine, factory, WaitingAdapter()).crawl_source(sources[0].id)
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with factory() as session:
        run = await session.scalar(
            select(CrawlRunModel).where(CrawlRunModel.source_id == sources[0].id)
        )
        assert run.status == CrawlStatus.FAILED and run.finished_at is not None
    async with PostgreSQLCrawlAdmissionGuard(engine).hold(sources[0].id):
        pass


class StaticAdapter:
    ats_type = "lever"

    def __init__(self, jobs):
        self.jobs = jobs
        self.called = 0

    async def crawl(self, source):
        self.called += 1
        return CrawlResultDTO(
            source_id=source.id, ats_type="lever", jobs=self.jobs, is_complete=True
        )


def orchestrator(engine, factory, adapter, **kwargs):
    return CrawlerOrchestrator(
        SQLAlchemyRuntimeSourceProvider(factory),
        ATSAdapterRegistry([adapter]),
        SQLAlchemyCrawlPersistenceManager(factory),
        PostgreSQLCrawlAdmissionGuard(engine),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_busy_request_creates_no_run_and_source_read_connection_is_released(db):
    engine, factory, sources = db
    source = sources[0]
    adapter = StaticAdapter([item(source)])
    crawl = orchestrator(engine, factory, adapter)
    async with PostgreSQLCrawlAdmissionGuard(engine).hold(source.id):
        result = await crawl.crawl_source(source.id)
        assert result.error_type == "SOURCE_CRAWL_BUSY" and result.crawl_run_id is None
        assert adapter.called == 0
        async with factory() as session:
            assert (
                await session.scalar(
                    select(CrawlRunModel.id).where(CrawlRunModel.source_id == source.id)
                )
                is None
            )

    class SlowAdapter(StaticAdapter):
        async def crawl(self, snapshot):
            # Source SELECT and initial-run sessions already returned to the pool.
            assert engine.pool.checkedout() == 1  # dedicated lock connection only
            assert snapshot.id == source.id
            return await super().crawl(snapshot)

    result = await orchestrator(
        engine, factory, SlowAdapter([item(source)])
    ).crawl_source(source.id)
    assert result.status == CrawlStatus.COMPLETED and result.jobs_created == 1
    assert engine.pool.checkedout() == 0
    # Batch DTO lookup also returns its connection before any network acquisition.
    snapshots = await SQLAlchemyRuntimeSourceProvider(factory).get_crawlable_sources(
        limit=2
    )
    assert snapshots and engine.pool.checkedout() == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, "different"])
async def test_cross_source_url_collision_commits_safe_items_and_suppresses_closure(
    db, external_id
):
    engine, factory, sources = db
    a, b = sources
    original = item(a)
    await orchestrator(engine, factory, StaticAdapter([original])).crawl_source(a.id)
    old_b = item(b, identity="absent")
    await orchestrator(engine, factory, StaticAdapter([old_b])).crawl_source(b.id)
    conflict = replace(
        item(b),
        external_job_id=external_id,
        url=original.url,
        title="Do not overwrite owner",
    )
    result = await orchestrator(
        engine,
        factory,
        StaticAdapter(
            [item(b, identity="safe-before"), conflict, item(b, identity="safe-after")]
        ),
    ).crawl_source(b.id)
    assert result.status == CrawlStatus.PARTIAL and result.error_count == 1
    assert result.jobs_created == 2 and result.jobs_closed == 0
    async with factory() as session:
        owner = await session.scalar(
            select(JobModel).where(JobModel.canonical_url == original.url)
        )
        assert owner.source_id == a.id and owner.title == "Engineer"
        jobs = (
            await session.scalars(select(JobModel).where(JobModel.source_id == b.id))
        ).all()
        assert len(jobs) == 3 and all(job.status == JobStatus.ACTIVE for job in jobs)


@pytest.mark.asyncio
async def test_actual_sql_failure_rolls_back_whole_source_and_stops_processing(db):
    engine, factory, sources = db
    source = sources[0]
    await orchestrator(
        engine, factory, StaticAdapter([item(source, identity="old")])
    ).crawl_source(source.id)
    # A real varchar(255) INSERT failure after one successfully flushed item.
    result = await orchestrator(
        engine,
        factory,
        StaticAdapter(
            [
                item(source, identity="before"),
                item(source, identity="bad", title="x" * 256),
                item(source, identity="after"),
            ]
        ),
    ).crawl_source(source.id)
    assert (
        result.status == CrawlStatus.FAILED and result.error_type == "INGESTION_FAILURE"
    )
    async with factory() as session:
        jobs = (
            await session.scalars(
                select(JobModel).where(JobModel.source_id == source.id)
            )
        ).all()
        assert [job.external_job_id for job in jobs] == ["old"]
        assert jobs[0].status == JobStatus.ACTIVE
        run = await session.get(CrawlRunModel, result.crawl_run_id)
        assert run.status == CrawlStatus.FAILED and run.jobs_created == 0
    # Lock and database are usable on a later independent crawl.
    retry = await orchestrator(
        engine, factory, StaticAdapter([item(source, identity="old")])
    ).crawl_source(source.id)
    assert retry.status == CrawlStatus.COMPLETED


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["body", "requests", "bytes", "duration"])
async def test_acquisition_limits_fail_without_ingestion_or_closure(
    db, monkeypatch, failure
):
    engine, factory, sources = db
    source = sources[0]
    await orchestrator(
        engine, factory, StaticAdapter([item(source, identity="old")])
    ).crawl_source(source.id)
    monkeypatch.setattr(
        "backend.infrastructure.http.safe_client.validate_target_url_safety",
        lambda url: (True, None, None),
    )
    now = [0.0]

    def handler(r):
        if failure == "duration":
            now[0] = 10
        return httpx.Response(
            200, json=[{"id": "new", "text": "Engineer", "descriptionPlain": "Python"}]
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        safe = HttpSafeClient(
            client=client, max_response_bytes=10 if failure == "body" else 10000
        )
        registry = create_adapter_registry(safe)
        adapter = registry.get_adapter("lever")
        source.pagination_config = {"page_size": 1}
        async with factory() as session:
            stored = await session.get(SourceModel, source.id)
            stored.pagination_config = source.pagination_config
            await session.commit()

        def budgets():
            return AcquisitionBudget(
                max_requests=1 if failure == "requests" else 100,
                max_bytes=10 if failure == "bytes" else 10000,
                max_seconds=10,
                clock=lambda: now[0],
            )

        result = await orchestrator(
            engine, factory, adapter, budget_factory=budgets
        ).crawl_source(source.id)
    assert result.status == CrawlStatus.FAILED
    assert result.error_type in {
        "RESPONSE_BODY_LIMIT_EXCEEDED",
        "ACQUISITION_BUDGET_EXHAUSTED",
    }
    async with factory() as session:
        jobs = (
            await session.scalars(
                select(JobModel).where(JobModel.source_id == source.id)
            )
        ).all()
        assert len(jobs) == 1 and jobs[0].status == JobStatus.ACTIVE
        run = await session.get(CrawlRunModel, result.crawl_run_id)
        assert run.status == CrawlStatus.FAILED
