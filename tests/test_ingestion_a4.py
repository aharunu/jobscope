"""A4 pure policy, PostgreSQL isolation, background and API acceptance proofs."""

import asyncio
import uuid
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.application.common.exceptions import JobScopeError
from backend.application.ingestion.policy import (
    CountryResolver,
    PolicySnapshot,
    resolve_policy,
)
from backend.application.ingestion.runner import IngestionRunner
from backend.application.job_discovery.adapter_registry import ATSAdapterRegistry
from backend.application.job_discovery.budget import AcquisitionBudget
from backend.application.job_discovery.dtos import CrawlResultDTO, DiscoveredJobDTO
from backend.domain.job.enums import JobStatus
from backend.domain.source.entities import Source
from backend.infrastructure.config.settings import get_settings
from backend.infrastructure.database.crawl_runtime import PostgreSQLCrawlAdmissionGuard
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.ingestion_store import SQLAlchemyIngestionStore
from backend.infrastructure.database.models.application import ApplicationModel
from backend.infrastructure.database.models.crawl_run import CrawlRunModel
from backend.infrastructure.database.models.dedup import (
    DedupCandidateModel,
    JobOccurrenceModel,
)
from backend.infrastructure.database.models.ingestion import (
    IngestionRunModel,
)
from backend.infrastructure.database.models.job import (
    JobModel,
    JobRequirementModel,
    RawJobModel,
)
from backend.infrastructure.database.models.matching import MatchResultModel
from backend.infrastructure.database.models.source import SourceModel
from backend.interfaces.api.main import create_app
from backend.interfaces.api.schemas.ingestion import (
    PolicyRequest,
    StartIngestionRequest,
)


def job(location="Istanbul", identity="1", country=None):
    return DiscoveredJobDTO(
        identity,
        f"https://jobs.example.com/{identity}",
        "Python Engineer",
        '{"full":"provider payload"}',
        "application/json",
        {"location": location, "description": "Required Python and SQL experience"},
        country_code=country,
    )


@pytest.mark.parametrize(
    "location",
    [
        "Turkey",
        "Türkiye",
        "TR",
        "Istanbul",
        "İstanbul",
        "Ankara",
        "Izmir",
        "İzmir",
        "Bursa",
        "Kocaeli",
        "Gebze",
        "TR Remote",
        "Remote - Turkey",
        "Turkey - Remote",
        "Şanlıurfa",
        "Düzce",
        "IĞDIR",
    ],
)
def test_turkish_country_aliases(location):
    assert CountryResolver().resolve(job(location)) == "TR"


@pytest.mark.parametrize(
    "location",
    [
        "Remote",
        "Worldwide",
        "Anywhere",
        "EMEA",
        "Europe",
        "Global",
        "",
        "Turkeys",
        "Istanbul, Germany",
        "unknown",
    ],
)
def test_unknown_and_conflicting_locations(location):
    assert CountryResolver().resolve(job(location)) is None


def test_precedence_unknown_and_validation():
    resolver = CountryResolver()
    assert resolver.resolve(job("Istanbul", country="DE")) == "DE"
    structured = job("Istanbul")
    structured.metadata["country"] = "US"
    assert resolver.resolve(structured) == "US"
    unknown = job("Remote")
    unknown.metadata["work_mode"] = "Remote"
    assert PolicySnapshot("RUN_OVERRIDE", ("TR",)).decide(unknown)[:2] == (
        "REJECTED",
        "COUNTRY_UNKNOWN",
    )
    assert PolicySnapshot("RUN_OVERRIDE", ("TR",), True).decide(unknown)[:2] == (
        "ACCEPTED",
        "UNKNOWN_INCLUDED",
    )
    assert (
        PolicySnapshot("SOURCE_OVERRIDE", ("TR",), enabled=False).decide(job("US"))[1]
        == "NO_COUNTRY_FILTER"
    )
    assert PolicyRequest(
        allowed_country_codes=["tr", "TR", "de"]
    ).allowed_country_codes == ["DE", "TR"]
    with pytest.raises(ValueError):
        PolicyRequest(allowed_country_codes=["ZZ"])
    with pytest.raises(ValueError):
        StartIngestionRequest(mode="PREVIEW", source_ids=[])
    with pytest.raises(ValueError):
        StartIngestionRequest(mode="PREVIEW", ats_types=["bogus"])
    assert (
        PolicySnapshot("NO_FILTER").decide(replace(job(), title=None))[1]
        == "INVALID_DISCOVERED_JOB"
    )


@pytest.fixture
async def db():
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    sources = [
        Source(
            name=f"A4 {i}",
            url=f"https://jobs.lever.co/a4-{uuid.uuid4().hex}",
            ats_type="lever",
            active=i == 0,
        )
        for i in range(2)
    ]
    store = SQLAlchemyIngestionStore(factory)
    run_ids = []
    try:
        async with factory() as session:
            session.add_all([SourceModel.from_domain(s) for s in sources])
            await session.commit()
        yield engine, factory, sources, store, run_ids
    finally:
        async with factory() as session:
            await session.execute(
                delete(IngestionRunModel).where(IngestionRunModel.id.in_(run_ids))
            )
            ids = [s.id for s in sources]
            await session.execute(
                delete(CrawlRunModel).where(CrawlRunModel.source_id.in_(ids))
            )
            await session.execute(delete(JobModel).where(JobModel.source_id.in_(ids)))
            await session.execute(delete(SourceModel).where(SourceModel.id.in_(ids)))
            await session.commit()
        await engine.dispose()


def request(sources, mode="PREVIEW", **changes):
    values = {
        "mode": mode,
        "source_ids": [s.id for s in sources],
        "policy_mode": "OVERRIDE_SELECTED_SOURCES",
        "allowed_country_codes": ["TR"],
        **changes,
    }
    return StartIngestionRequest(**values).model_dump(mode="json")


async def create(db, mode="PREVIEW", **changes):
    _, _, sources, store, ids = db
    run, units = await store.create_run(request(sources[:1], mode, **changes))
    ids.append(run["id"])
    await store.mark_running(run["id"])
    return run, units[0]


async def counts(factory):
    async with factory() as session:
        return [
            await session.scalar(select(func.count()).select_from(m))
            for m in (
                JobOccurrenceModel,
                DedupCandidateModel,
                JobModel,
                RawJobModel,
                JobRequirementModel,
                MatchResultModel,
                ApplicationModel,
                CrawlRunModel,
            )
        ]


async def complete(db, run, unit, jobs, complete=True):
    store = db[3]
    unit_id, source, policy = unit
    await store.complete_source(
        run["id"],
        unit_id,
        source,
        policy,
        CrawlResultDTO(source.id, source.ats_type, jobs=jobs, is_complete=complete),
        run["mode"],
        10,
    )
    await store.finish(run["id"])
    return await store.detail(run["id"])


async def test_preview_zero_canonical_mutations_and_compact_decisions(db):
    before = await counts(db[1])
    run, unit = await create(db)
    result = await complete(
        db,
        run,
        unit,
        [
            job("Istanbul", "tr1"),
            job("Ankara", "tr2"),
            job("United States", "us"),
            job("Germany", "de"),
            job("Remote", "unknown"),
        ],
    )
    assert await counts(db[1]) == before
    assert (
        result["jobs_discovered"],
        result["jobs_accepted"],
        result["jobs_rejected"],
    ) == (5, 2, 3)
    rows = await db[3].decisions(run["id"], decision="REJECTED")
    assert rows["total"] == 3
    assert not any(
        k in rows["items"][0] for k in ("description", "raw_content", "requirements")
    )
    assert (await db[3].sources(run["id"]))["items"][0][
        "closure_suppression_reason"
    ] == "PREVIEW_MODE"


async def test_persist_item_conflict_is_visible_in_source_audit(db):
    first, unit = await create(db, "PERSIST")
    await complete(db, first, unit, [job("Istanbul", "conflict")])
    second, units = await db[3].create_run(
        request(db[2][1:], "PERSIST", active_sources_only=False)
    )
    db[4].append(second["id"])
    await complete(db, second, units[0], [job("Istanbul", "conflict")])
    row = (await db[3].sources(second["id"]))["items"][0]
    assert row["status"] == "FAILED"
    assert row["error_type"] == "INGESTION_ITEM_FAILURE"
    assert "JOB_URL_OWNERSHIP_CONFLICT" in row["error_message"]
    assert "JOB_URL_OWNERSHIP_CONFLICT" in row["warnings"]
    assert row["jobs_accepted"] == 1 and row["jobs_created"] == 0
    assert not row["closure_authorized"]


async def test_persist_rejects_unenriched_accepted_summary_atomically(db):
    run, unit = await create(db, "PERSIST")
    before = await counts(db[1])
    summary = job()
    summary.metadata["acquisition_detail_deferred"] = "PREVIEW"
    with pytest.raises(JobScopeError) as caught:
        await complete(db, run, unit, [summary])
    assert caught.value.code == "INGESTION_DETAILS_REQUIRED"
    assert await counts(db[1]) == before
    await db[3].finish(run["id"], "FAILED")


async def test_country_rejected_summary_is_audited_without_persisting(db):
    run, unit = await create(db, "PERSIST")
    before = await counts(db[1])
    rejected = job("France", "fr")
    rejected.metadata["acquisition_detail_deferred"] = "COUNTRY_POLICY"
    result = await complete(db, run, unit, [rejected])
    # A crawl audit is allowed; canonical/provider history remains unchanged.
    assert (await counts(db[1]))[:7] == before[:7]
    assert result["jobs_accepted"] == 0 and result["jobs_rejected"] == 1
    rows = await db[3].sources(run["id"])
    assert not rows["items"][0]["closure_authorized"]


@pytest.mark.parametrize("mode", ["PREVIEW", "PERSIST"])
@pytest.mark.parametrize("ats_type", ["kariyer_net", "custom"])
async def test_ineligible_sources_rejected_explicitly_and_excluded_from_all_scope(
    db, mode, ats_type
):
    factory, sources, store, ids = db[1], db[2], db[3], db[4]
    async with factory() as session, session.begin():
        source = await session.get(SourceModel, sources[1].id)
        source.ats_type, source.active = ats_type, True
    before = await counts(factory)
    for selection in (
        request(sources[1:], mode, active_sources_only=False),
        # Store also rejects excluded types defensively; API schema already
        # rejects custom ATS selectors before reaching persistence.
        {**request([], mode, source_ids=None), "ats_types": [ats_type]},
    ):
        with pytest.raises(JobScopeError) as error:
            await store.create_run(selection)
        assert error.value.code == "INVALID_INGESTION_SCOPE"
        assert error.value.status_code == 422
    run, units = await store.create_run(
        request([], mode, source_ids=None, active_sources_only=False)
    )
    ids.append(run["id"])
    assert sources[0].id in {unit[1].id for unit in units}
    assert all(unit[1].ats_type not in ("kariyer_net", "custom") for unit in units)
    assert run["sources_total"] == len(units)
    await store.finish(run["id"], "FAILED")
    assert await counts(factory) == before
    async with factory() as session:
        assert (await session.get(SourceModel, sources[1].id)).ats_type == ats_type


async def test_persist_from_preview_reuses_frozen_scope_and_policy(db):
    preview, unit = await create(db)
    await complete(db, preview, unit, [job("TR", "preview-tr")])
    await db[3].policy(
        db[2][0].id,
        {
            "allowed_country_codes": ["DE"],
            "include_unknown_country": True,
            "enabled": True,
        },
    )
    body = StartIngestionRequest(
        mode="PERSIST", from_preview_run_id=preview["id"]
    ).model_dump(mode="json")
    persisted, units = await db[3].create_run(body)
    db[4].append(persisted["id"])
    assert len(units) == 1 and units[0][1].id == unit[1].id
    assert units[0][2] == unit[2]
    assert persisted["scope"]["from_preview_run_id"] == str(preview["id"])
    result = await complete(
        db,
        persisted,
        units[0],
        [job("TR", str(db[2][0].id)), job("DE", "not-accepted")],
    )
    assert result["jobs_created"] == 1
    assert result["jobs_accepted"] == 1 and result["jobs_rejected"] == 1
    assert result["jobs_closed"] == 0


@pytest.mark.parametrize(
    "mode,status",
    [
        ("PREVIEW", "INTERRUPTED"),
        ("PREVIEW", "FAILED"),
        ("PREVIEW", "CANCELLED"),
        ("PERSIST", "COMPLETED"),
    ],
)
async def test_persist_from_preview_rejects_ineligible_run(db, mode, status):
    previous, _ = await create(db, mode)
    await db[3].finish(previous["id"], status)
    with pytest.raises(JobScopeError, match="completed preview"):
        await db[3].create_run(
            StartIngestionRequest(
                mode="PERSIST", from_preview_run_id=previous["id"]
            ).model_dump(mode="json")
        )


def test_preview_reference_cannot_mix_scope_or_policy_changes():
    for extra in (
        {"source_ids": [uuid.uuid4()]},
        {"allowed_country_codes": ["DE"]},
        {"active_sources_only": False},
        {"mode": "PREVIEW"},
    ):
        with pytest.raises(ValueError):
            StartIngestionRequest(
                **{"mode": "PERSIST", "from_preview_run_id": uuid.uuid4(), **extra}
            )


async def test_persist_from_preview_rejects_missing_and_now_inactive_sources(db):
    store = db[3]
    with pytest.raises(JobScopeError, match="not found"):
        await store.create_run(
            StartIngestionRequest(
                mode="PERSIST", from_preview_run_id=uuid.uuid4()
            ).model_dump(mode="json")
        )
    preview, unit = await create(db)
    await complete(db, preview, unit, [job()], complete=False)
    assert (await store.detail(preview["id"]))["status"] == "COMPLETED_WITH_WARNINGS"
    body = StartIngestionRequest(
        mode="PERSIST", from_preview_run_id=preview["id"]
    ).model_dump(mode="json")
    run, units = await store.create_run(body)
    db[4].append(run["id"])
    assert units[0][2] == unit[2]
    await store.finish(run["id"], "FAILED")
    async with db[1]() as session:
        source = await session.get(SourceModel, unit[1].id)
        source.active = False
        await session.commit()
    with pytest.raises(JobScopeError, match="no longer eligible"):
        await store.create_run(body)


async def test_preview_missing_source_snapshot_cannot_expand_to_all_sources(db):
    preview, unit = await create(db)
    await complete(db, preview, unit, [job()])
    async with db[1]() as session:
        row = await session.get(IngestionRunModel, preview["id"])
        row.sources_total += 1
        await session.commit()
    with pytest.raises(JobScopeError, match="snapshots are incomplete"):
        await db[3].create_run(
            StartIngestionRequest(
                mode="PERSIST", from_preview_run_id=preview["id"]
            ).model_dump(mode="json")
        )


async def test_filtered_persist_rejected_without_raw_and_repeat_unchanged(
    db,
):
    rows = [
        job("Istanbul", f"{db[2][0].id}-tr"),
        job("Ankara", f"{db[2][0].id}-tr2"),
        job("US", "rejected-us"),
        job("DE", "rejected-de"),
        job("Remote", "rejected-unknown"),
    ]
    for index in range(2):
        run, unit = await create(db, "PERSIST")
        result = await complete(db, run, unit, rows)
        assert result["jobs_created"] == (2 if index == 0 else 0)
        assert result["jobs_unchanged"] == (0 if index == 0 else 2)
        assert result["jobs_closed"] == 0
        unit_view = (await db[3].sources(run["id"]))["items"][0]
        assert unit_view["acquisition_complete"] and not unit_view["closure_authorized"]
        assert (
            unit_view["closure_suppression_reason"] == "INGESTION_POLICY_FILTER_ACTIVE"
        )
    async with db[1]() as session:
        jobs = list(
            (
                await session.scalars(
                    select(JobModel).where(JobModel.source_id == db[2][0].id)
                )
            ).all()
        )
        assert len(jobs) == 2
        assert (
            await session.scalar(
                select(func.count())
                .select_from(RawJobModel)
                .where(RawJobModel.source_id == db[2][0].id)
            )
            == 2
        )
        requirements = (
            await session.scalars(
                select(JobRequirementModel).where(
                    JobRequirementModel.job_id.in_([j.id for j in jobs])
                )
            )
        ).all()
        assert requirements


async def test_filter_blocks_historical_absence_but_unfiltered_closure_still_works(db):
    prefix = str(db[2][0].id)
    tr, us = job("TR", prefix + "tr"), job("US", prefix + "us")
    run, unit = await create(db, "PERSIST", allowed_country_codes=[])
    await complete(db, run, unit, [tr, us])
    run, unit = await create(db, "PERSIST")
    await complete(db, run, unit, [tr, us])
    async with db[1]() as session:
        assert (
            await session.scalar(
                select(JobModel).where(
                    JobModel.source_id == db[2][0].id,
                    JobModel.external_job_id == us.external_job_id,
                )
            )
        ).status == JobStatus.ACTIVE
    run, unit = await create(db, "PERSIST", allowed_country_codes=[])
    result = await complete(db, run, unit, [tr])
    assert result["jobs_closed"] == 1


async def test_policy_snapshot_scope_precedence_and_delete(db):
    store, source = db[3], db[2][0]
    await store.policy(
        source.id,
        {
            "allowed_country_codes": ["DE"],
            "include_unknown_country": False,
            "enabled": True,
        },
    )
    body = request([source])
    body["policy_mode"] = "USE_SAVED_POLICIES"
    run, units = await store.create_run(body)
    db[4].append(run["id"])
    assert units[0][2].origin == "SOURCE_OVERRIDE"
    await store.policy(
        source.id,
        {
            "allowed_country_codes": ["TR"],
            "include_unknown_country": True,
            "enabled": True,
        },
    )
    assert units[0][2].allowed_country_codes == ("DE",)
    assert (await store.sources(run["id"]))["items"][0]["policy_snapshot"][
        "allowed_country_codes"
    ] == ["DE"]
    await store.finish(run["id"], "FAILED")
    run, unit = await create(db)
    assert unit[2].origin == "RUN_OVERRIDE" and unit[2].allowed_country_codes == ("TR",)
    await store.finish(run["id"], "FAILED")
    await store.policy(source.id, remove=True)
    assert await store.policy(source.id) is None
    with pytest.raises(JobScopeError, match="Unknown source"):
        await store.create_run(request([replace(source, id=uuid.uuid4())]))
    with pytest.raises(JobScopeError, match="No sources"):
        await store.create_run(request(db[2][1:]))
    run, units = await store.create_run(request(db[2], active_sources_only=False))
    db[4].append(run["id"])
    assert len(units) == 2
    await store.finish(run["id"], "FAILED")


async def test_background_prompt_busy_cancel_and_live_worker_recovery_guard(db):
    engine, factory, sources, store, ids = db
    started, release = asyncio.Event(), asyncio.Event()

    class Adapter:
        ats_type = "lever"

        async def crawl(self, source):
            started.set()
            async with engine.connect() as observer:
                states = (
                    await observer.execute(
                        text(
                            "SELECT a.state, a.xact_start FROM pg_locks l "
                            "JOIN pg_stat_activity a ON a.pid=l.pid "
                            "WHERE l.locktype='advisory' AND l.granted "
                            "AND a.datname=current_database()"
                        )
                    )
                ).all()
                assert all(state == "idle" and tx is None for state, tx in states)
            await release.wait()
            return CrawlResultDTO(
                source.id, source.ats_type, jobs=[job()], is_complete=True
            )

    registry = ATSAdapterRegistry()
    registry.register(Adapter())
    runner = IngestionRunner(
        store,
        registry,
        PostgreSQLCrawlAdmissionGuard(engine),
        AcquisitionBudget,
        max_concurrent_sources=1,
    )
    app = create_app(engine=engine)
    app.state.ingestion_runner = runner
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await asyncio.wait_for(
                client.post(
                    "/api/ingestion/runs",
                    json=request(sources, active_sources_only=False),
                ),
                2,
            )
            assert response.status_code == 202
            run_id = uuid.UUID(response.json()["id"])
            ids.append(run_id)
            await started.wait()
            busy = await client.post("/api/ingestion/runs", json=request(sources[:1]))
            assert (
                busy.status_code == 409
                and busy.json()["error"]["code"] == "INGESTION_RUN_BUSY"
            )
            other = IngestionRunner(
                store,
                registry,
                PostgreSQLCrawlAdmissionGuard(engine),
                AcquisitionBudget,
            )
            await other.reconcile()
            assert (await store.detail(run_id))["status"] == "RUNNING"
            assert (
                await client.post(f"/api/ingestion/runs/{run_id}/cancel")
            ).status_code == 200
            release.set()
            await runner.shutdown()
            detail = await store.detail(run_id)
            assert detail["status"] == "CANCELLED" and detail["sources_completed"] == 2
            units = (await store.sources(run_id))["items"]
            assert [r["status"] for r in units] == ["COMPLETED", "CANCELLED"]
    finally:
        release.set()
        await runner.shutdown()


async def test_restart_interrupts_stale_run_and_atomic_failure_rollback(
    db, monkeypatch
):
    run, unit = await create(db, "PERSIST")
    runner = IngestionRunner(
        db[3], None, PostgreSQLCrawlAdmissionGuard(db[0]), AcquisitionBudget
    )
    await runner.reconcile()
    assert (await db[3].detail(run["id"]))["status"] == "INTERRUPTED"
    run, unit = await create(db, "PERSIST")
    before = await counts(db[1])
    service = AsyncMock()
    service.ingest_crawl_result.side_effect = RuntimeError("transaction failure")
    monkeypatch.setattr(
        "backend.infrastructure.database.ingestion_store.build_ingestion_service",
        lambda _: service,
    )
    with pytest.raises(RuntimeError):
        await complete(db, run, unit, [job()])
    assert await counts(db[1]) == before
    assert (await db[3].decisions(run["id"]))["total"] == 0
    await db[3].fail_source(run["id"], unit[0], "TEST_FAILURE", 0)
    await db[3].finish(run["id"])
    assert (await db[3].detail(run["id"]))["status"] == "FAILED"


def test_saved_global_and_disabled_override_precedence():
    saved = {
        "allowed_country_codes": ["TR"],
        "include_unknown_country": False,
        "enabled": True,
    }
    request = {"policy_mode": "USE_SAVED_POLICIES"}
    assert resolve_policy(request, None, saved).origin == "GLOBAL_DEFAULT"
    assert resolve_policy(request, None, None).origin == "NO_FILTER"
    disabled = {**saved, "enabled": False}
    policy = resolve_policy(request, disabled, saved)
    assert policy.origin == "SOURCE_OVERRIDE" and not policy.active
    assert policy.decide(job("US"))[0] == "ACCEPTED"


@pytest.mark.parametrize("code", ["tr", "TR", "Tr", " tr ", "es", "ES", "Es", " es "])
def test_whole_location_iso_codes_are_case_insensitive(code):
    resolved = code.strip().upper()
    posting = job(code)
    assert CountryResolver().resolve(posting) == resolved
    assert PolicySnapshot("RUN_OVERRIDE", (resolved,)).decide(posting)[:2] == (
        "ACCEPTED",
        "COUNTRY_ALLOWED",
    )
    posting.country_code = code
    assert CountryResolver().resolve(posting) == resolved


@pytest.mark.parametrize("location", ["Spain", "España", "İspanya"])
def test_spanish_country_aliases(location):
    assert CountryResolver().resolve(job(location)) == "ES"


@pytest.mark.parametrize("location", ["Work in Europe", "troubleshooting", "estimates"])
def test_lowercase_codes_inside_prose_are_not_guessed(location):
    assert CountryResolver().resolve(job(location)) is None


@pytest.mark.parametrize(
    "url",
    [
        "https://",
        "https://[malformed",
        "javascript:alert(1)",
        "https://user:password@example.com/1",
    ],
)
def test_invalid_urls_rejected_before_canonical_pipeline(url):
    assert (
        PolicySnapshot("NO_FILTER").decide(replace(job(), url=url))[1]
        == "INVALID_DISCOVERED_JOB"
    )


async def test_unknown_included_partial_cannot_close_and_decision_filters(db):
    run, unit = await create(db, "PERSIST", include_unknown_country=True)
    result = await complete(
        db, run, unit, [job("Remote", str(db[2][0].id))], complete=False
    )
    assert result["status"] == "COMPLETED_WITH_WARNINGS"
    assert result["jobs_created"] == result["jobs_accepted"] == 1
    source = (await db[3].sources(run["id"]))["items"][0]
    assert source["status"] == "PARTIAL" and not source["closure_authorized"]
    page = await db[3].decisions(
        run["id"], reason="UNKNOWN_INCLUDED", source_id=db[2][0].id, limit=1, offset=0
    )
    assert page["total"] == len(page["items"]) == 1
    assert (await db[3].decisions(run["id"], resolved_country="TR"))["total"] == 0


async def test_source_ats_scope_intersection_and_api_policy_validation(db):
    store = db[3]
    with pytest.raises(JobScopeError, match="No sources"):
        await store.create_run(request(db[2][:1], ats_types=["ashby"]))
    app = create_app(engine=db[0])
    app.state.ingestion_runner = IngestionRunner(
        store, None, PostgreSQLCrawlAdmissionGuard(db[0]), AcquisitionBudget
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (
            await client.put(
                f"/api/ingestion/policies/sources/{db[2][0].id}",
                json={"allowed_country_codes": ["tr", "TR"]},
            )
        ).json()["allowed_country_codes"] == ["TR"]
        assert (
            await client.put(
                f"/api/ingestion/policies/sources/{db[2][0].id}",
                json={"allowed_country_codes": ["ZZ"]},
            )
        ).status_code == 422
        assert (
            await client.delete(f"/api/ingestion/policies/sources/{db[2][0].id}")
        ).status_code == 204
        assert (
            await client.get(f"/api/ingestion/runs/{uuid.uuid4()}")
        ).status_code == 404
