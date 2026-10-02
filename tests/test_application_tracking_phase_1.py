"""Real PostgreSQL/API regression checks for Application Tracking acceptance."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.application_tracking.exceptions import (
    ApplicationAlreadyExistsError,
)
from backend.application.application_tracking.services import ApplicationTrackingService
from backend.domain.application.entities import Application, ApplicationStatusHistory
from backend.domain.application.enums import ApplicationStatus
from backend.domain.job.enums import JobStatus
from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database import session as session_module
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.application import ApplicationModel
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.repositories.application_repository import (
    SQLAlchemyApplicationRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
)
from backend.interfaces.api.dependencies.application import get_application_repository
from backend.interfaces.api.dependencies.database import DbSession
from backend.interfaces.api.main import create_app
from tests.test_application_tracking_persistence import pg_session as pg_session


@pytest.fixture
async def database_api(pg_session: AsyncSession, monkeypatch):
    """Use real request commit/rollback inside an outer test-only transaction."""
    user_id, other_user_id, source_id, job_id = [uuid.uuid4() for _ in range(4)]
    pg_session.add_all([UserModel(id=user_id), UserModel(id=other_user_id)])
    pg_session.add(
        SourceModel(
            id=source_id,
            name="Phase 1 source",
            url=f"https://example.com/{source_id}",
            ats_type="lever",
            active=True,
        )
    )
    await pg_session.flush()
    pg_session.add(
        JobModel(
            id=job_id,
            source_id=source_id,
            canonical_url=f"https://example.com/jobs/{job_id}",
            company="Phase 1",
            title="Engineer",
            description="Test job",
            content_hash=str(job_id),
            status=JobStatus.ACTIVE,
        )
    )
    await pg_session.flush()
    connection = await pg_session.connection()
    factory = async_sessionmaker(
        connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    monkeypatch.setattr(session_module, "_session_factory", factory)
    settings = Settings(_env_file=None, environment="test", debug=False)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, app, factory, user_id, other_user_id, job_id


async def create_tracked(client, user_id, job_id, **fields):
    response = await client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_id)},
        json={"job_id": str(job_id), **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_real_api_creation_history_and_closed_job_independence(database_api):
    client, _, factory, user_id, _, job_id = database_api
    created = await create_tracked(client, user_id, job_id, notes="  Initial note  ")
    assert created["status"] == "INTERESTED"
    assert created["notes"] == "Initial note"
    assert created["status_history"] == []
    assert created["created_at"] and created["updated_at"]
    path = f"/api/applications/{created['id']}"
    headers = {"X-User-Id": str(user_id)}
    for target in ("APPLYING", "APPLIED", "INTERVIEW"):
        response = await client.patch(
            f"{path}/status", headers=headers, json={"status": target}
        )
        assert response.status_code == 200, response.text
    async with factory() as session:
        job = await session.get(JobModel, job_id)
        job.status = JobStatus.CLOSED
        await session.commit()
    detail = (await client.get(path, headers=headers)).json()
    assert detail["status"] == "INTERVIEW"
    assert detail["job"]["status"] == "CLOSED"
    history = (await client.get(f"{path}/history", headers=headers)).json()
    assert [(h["from_status"], h["to_status"]) for h in history] == [
        ("INTERESTED", "APPLYING"),
        ("APPLYING", "APPLIED"),
        ("APPLIED", "INTERVIEW"),
    ]
    assert detail["status_history"] == history
    assert all(
        h["changed_at"] and h["application_id"] == created["id"] for h in history
    )
    no_op = await client.patch(
        f"{path}/status", headers=headers, json={"status": "INTERVIEW"}
    )
    assert no_op.status_code == 422
    assert (await client.get(f"{path}/history", headers=headers)).json() == history
    cleared = await client.patch(f"{path}/notes", headers=headers, json={"notes": " "})
    assert cleared.status_code == 200
    assert cleared.json()["notes"] is None
    assert cleared.json()["status_history"] == history


@pytest.mark.asyncio
async def test_real_api_ownership_and_duplicate_isolation(database_api):
    client, _, _, user_id, other_id, job_id = database_api
    created = await create_tracked(client, user_id, job_id, status="APPLIED")
    assert created["status_history"] == []
    path = f"/api/applications/{created['id']}"
    own = await client.get(
        "/api/applications?status=APPLIED&limit=1&offset=0",
        headers={"X-User-Id": str(user_id)},
    )
    assert own.status_code == 200
    assert own.json()["total"] == 1
    assert own.json()["items"][0]["id"] == created["id"]
    other_headers = {"X-User-Id": str(other_id)}
    listed = (await client.get("/api/applications", headers=other_headers)).json()
    assert listed["total"] == 0 and listed["items"] == []
    for suffix in ("", "/history"):
        assert (
            await client.get(path + suffix, headers=other_headers)
        ).status_code == 404
    for suffix, payload in (
        ("/status", {"status": "INTERVIEW"}),
        ("/notes", {"notes": "intrusion"}),
    ):
        response = await client.patch(
            path + suffix, headers=other_headers, json=payload
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "APPLICATION_NOT_FOUND"
    duplicate = await client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_id)},
        json={"job_id": str(job_id)},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "APPLICATION_ALREADY_EXISTS"
    assert (await client.delete(path, headers=other_headers)).status_code == 404
    # Uniqueness is per user, rather than globally per job.
    await create_tracked(client, other_id, job_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"status": "DISCOVERED"}, {"status": "unknown"}, {"job_id": "bad-uuid"}],
)
async def test_real_api_validation_rejects_invalid_input(database_api, payload):
    client, _, _, user_id, _, job_id = database_api
    headers = {"X-User-Id": str(user_id)}
    response = await client.post(
        "/api/applications", headers=headers, json={"job_id": str(job_id), **payload}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_status_validation_missing_job_and_untrusted_identity(database_api):
    client, _, _, user_id, other_id, job_id = database_api
    headers = {"X-User-Id": str(user_id)}
    forbidden = await client.post(
        "/api/applications",
        headers=headers,
        json={"job_id": str(job_id), "user_id": str(other_id)},
    )
    assert forbidden.status_code == 422
    missing = await client.post(
        "/api/applications", headers=headers, json={"job_id": str(uuid.uuid4())}
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "JOB_NOT_FOUND"
    created = await create_tracked(client, user_id, job_id)
    invalid = await client.patch(
        f"/api/applications/{created['id']}/status",
        headers=headers,
        json={"status": "DISCOVERED"},
    )
    assert invalid.status_code == 422
    malformed = await client.get("/api/applications/bad-uuid", headers=headers)
    assert malformed.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_database_race_becomes_safe_api_conflict(database_api):
    client, app, factory, user_id, _, job_id = database_api
    await create_tracked(client, user_id, job_id)

    class StaleDuplicateCheckRepository(SQLAlchemyApplicationRepository):
        async def get_by_job_and_user(self, job_id, user_id):
            return None  # Simulate another request inserting after the pre-check.

    def stale_repository(session: DbSession):
        return StaleDuplicateCheckRepository(session)

    app.dependency_overrides[get_application_repository] = stale_repository
    response = await client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_id)},
        json={"job_id": str(job_id)},
    )
    assert response.status_code == 409, response.text
    assert response.json() == {
        "error": {
            "code": "APPLICATION_ALREADY_EXISTS",
            "message": "Application already exists for this job",
            "details": {},
        }
    }
    async with factory() as session:
        assert (
            await SQLAlchemyApplicationRepository(session).count_by_user_id(user_id)
            == 1
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("fail_after_insert", [False, True])
async def test_real_request_rolls_back_status_and_inserted_history_on_failure(
    database_api,
    fail_after_insert,
):
    client, app, _, user_id, _, job_id = database_api
    created = await create_tracked(client, user_id, job_id, status="APPLIED")

    class FailingHistoryRepository(SQLAlchemyApplicationRepository):
        async def add_status_history(self, history):
            if fail_after_insert:
                await super().add_status_history(history)
            raise RuntimeError("Simulated failure after history flush")

    def failing_repository(session: DbSession):
        return FailingHistoryRepository(session)

    app.dependency_overrides[get_application_repository] = failing_repository
    path = f"/api/applications/{created['id']}"
    headers = {"X-User-Id": str(user_id)}
    response = await client.patch(
        f"{path}/status", headers=headers, json={"status": "INTERVIEW"}
    )
    assert response.status_code == 500
    assert "Simulated failure" not in response.text
    app.dependency_overrides.clear()
    detail = (await client.get(path, headers=headers)).json()
    assert detail["status"] == "APPLIED"
    assert detail["status_history"] == []


@pytest.mark.asyncio
async def test_embedded_history_sorted_and_locked_read_refreshes_cache(database_api):
    _, _, factory, user_id, _, job_id = database_api
    async with factory() as session:
        repo = SQLAlchemyApplicationRepository(session)
        tracked = await repo.save(Application(job_id=job_id, user_id=user_id))
        moment = datetime.now(UTC)
        for offset in (2, 0, 1):
            await repo.add_status_history(
                ApplicationStatusHistory(
                    application_id=tracked.id,
                    from_status=ApplicationStatus.INTERESTED,
                    to_status=ApplicationStatus.APPLIED,
                    changed_at=moment + timedelta(seconds=offset),
                )
            )
        # Keep an ORM identity cached, then change the underlying row without
        # session synchronization to mimic a stale request identity map.
        from sqlalchemy import update

        cached = await session.get(ApplicationModel, tracked.id)
        await session.execute(
            update(ApplicationModel)
            .where(ApplicationModel.id == tracked.id)
            .values(status=ApplicationStatus.APPLIED)
            .execution_options(synchronize_session=False)
        )
        assert cached.status == ApplicationStatus.INTERESTED
        loaded = await repo.get_by_id_and_user_id(tracked.id, user_id, for_update=True)
        assert loaded.status == ApplicationStatus.APPLIED
        assert loaded.status_history == await repo.list_status_history(tracked.id)


@pytest.mark.asyncio
async def test_real_unique_constraint_preserves_other_integrity_errors(database_api):
    _, _, factory, user_id, _, job_id = database_api
    from sqlalchemy.exc import IntegrityError

    async with factory() as session:
        repo = SQLAlchemyApplicationRepository(session)
        await repo.save(Application(job_id=job_id, user_id=user_id))
        async with session.begin_nested():
            with pytest.raises(ApplicationAlreadyExistsError):
                await repo.save(Application(job_id=job_id, user_id=user_id))
            await session.rollback()
    async with factory() as session:
        repo = SQLAlchemyApplicationRepository(session)
        with pytest.raises(IntegrityError):
            await repo.save(Application(job_id=uuid.uuid4(), user_id=user_id))
        await session.rollback()


@pytest.fixture
async def committed_application():
    """Give concurrent connections visible, uniquely identified test records."""
    engine = create_database_engine(get_settings().model_copy(update={"debug": False}))
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id, source_id, job_id, application_id = [uuid.uuid4() for _ in range(4)]
    try:
        async with factory() as session:
            session.add(UserModel(id=user_id))
            session.add(
                SourceModel(
                    id=source_id,
                    name="Concurrency test",
                    url=f"https://example.com/{source_id}",
                    ats_type="lever",
                    active=True,
                )
            )
            await session.flush()
            session.add(
                JobModel(
                    id=job_id,
                    source_id=source_id,
                    canonical_url=f"https://example.com/{job_id}",
                    company="Concurrency test",
                    title="Engineer",
                    description="Test",
                    content_hash=str(job_id),
                )
            )
            await session.flush()
            await SQLAlchemyApplicationRepository(session).save(
                Application(
                    id=application_id,
                    user_id=user_id,
                    job_id=job_id,
                    status=ApplicationStatus.APPLIED,
                )
            )
            await session.commit()
        yield factory, user_id, application_id
    finally:
        # Remove only records created by this fixture; no developer data touched.
        async with factory() as session:
            await session.execute(delete(UserModel).where(UserModel.id == user_id))
            await session.execute(delete(JobModel).where(JobModel.id == job_id))
            await session.execute(
                delete(SourceModel).where(SourceModel.id == source_id)
            )
            await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_status_updates_record_committed_predecessor(
    committed_application,
):
    factory, user_id, application_id = committed_application
    attempted = asyncio.Event()

    class SignallingRepository(SQLAlchemyApplicationRepository):
        async def get_by_id_and_user_id(
            self, application_id, user_id, *, for_update=False
        ):
            attempted.set()
            return await super().get_by_id_and_user_id(
                application_id, user_id, for_update=for_update
            )

    async with factory() as first, factory() as second:
        cached = await second.get(ApplicationModel, application_id)
        first_service = ApplicationTrackingService(
            SQLAlchemyApplicationRepository(first), SQLAlchemyJobRepository(first)
        )
        second_service = ApplicationTrackingService(
            SignallingRepository(second), SQLAlchemyJobRepository(second)
        )
        updated = await first_service.update_status(
            application_id, user_id, ApplicationStatus.INTERVIEW
        )
        assert updated.status_history[-1].to_status == ApplicationStatus.INTERVIEW
        task = asyncio.create_task(
            second_service.update_status(
                application_id, user_id, ApplicationStatus.OFFER
            )
        )
        try:
            await asyncio.wait_for(attempted.wait(), timeout=5)
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(task), timeout=0.1)
            await first.commit()
            result = await asyncio.wait_for(task, timeout=5)
            assert cached.status == ApplicationStatus.OFFER
            assert result.status == ApplicationStatus.OFFER
            assert [(h.from_status, h.to_status) for h in result.status_history] == [
                (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEW),
                (ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER),
            ]
            await second.commit()
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    async with factory() as session:
        histories = await SQLAlchemyApplicationRepository(session).list_status_history(
            application_id
        )
        assert [h.from_status for h in histories] == [
            ApplicationStatus.APPLIED,
            ApplicationStatus.INTERVIEW,
        ]
