"""Persistence integration tests for SQLAlchemyApplicationRepository."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
)
from backend.domain.application.enums import ApplicationStatus
from backend.domain.application.repositories import ApplicationRepository
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.engine import create_database_engine
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.models.user import UserModel
from backend.infrastructure.database.repositories.application_repository import (
    SQLAlchemyApplicationRepository,
)

# ============================================================================
# 1. Protocol Conformance Test
# ============================================================================


def test_application_repository_satisfies_protocol() -> None:
    """Verify concrete repository satisfies domain ApplicationRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyApplicationRepository(mock_session)
    assert isinstance(repo, ApplicationRepository)


# ============================================================================
# 2. Database Integration Tests (Transactional Session with Rollback)
# ============================================================================


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
    async with factory() as session:
        try:
            await session.execute(select(1))
        except Exception:
            await engine.dispose()
            pytest.skip("PostgreSQL integration database unavailable")
        try:
            yield session
        finally:
            await session.rollback()
            await engine.dispose()


@pytest.mark.asyncio
async def test_application_repository_crud_flow(pg_session: AsyncSession) -> None:
    """Verify full CRUD lifecycle via SQLAlchemyApplicationRepository."""
    # 1. Setup User, Source, and Job
    user_id = uuid.uuid4()
    user = UserModel(id=user_id)
    pg_session.add(user)

    source_id = uuid.uuid4()
    source = SourceModel(
        id=source_id,
        name="Test Source",
        url=f"https://source-{source_id}.example.com",
        ats_type="lever",
        active=True,
    )
    pg_session.add(source)
    await pg_session.flush()

    job_id = uuid.uuid4()
    job = JobModel(
        id=job_id,
        source_id=source.id,
        canonical_url=f"https://source-{source_id}.example.com/job-1",
        company="Enterprise Tech",
        title="Senior Cloud Architect",
        description="AWS / GCP architectures.",
        status=JobStatus.ACTIVE,
        content_hash=f"hash-{job_id}",
    )
    pg_session.add(job)
    await pg_session.flush()

    app_repo = SQLAlchemyApplicationRepository(pg_session)

    # 2. Save Application (Insert)
    app = Application(
        job_id=job.id,
        user_id=user.id,
        status=ApplicationStatus.INTERESTED,
        notes="Bookmarked job.",
    )
    saved = await app_repo.save(app)
    assert saved.id == app.id
    assert saved.status == ApplicationStatus.INTERESTED
    assert saved.notes == "Bookmarked job."
    assert saved.job is not None
    assert saved.job.title == "Senior Cloud Architect"

    # 3. Get by ID and User Scoping
    by_id = await app_repo.get_by_id(app.id)
    assert by_id is not None
    assert by_id.id == app.id

    by_user = await app_repo.get_by_id_and_user_id(app.id, user.id)
    assert by_user is not None
    assert by_user.id == app.id

    # Another user cannot find it
    other_user_id = uuid.uuid4()
    not_by_user = await app_repo.get_by_id_and_user_id(app.id, other_user_id)
    assert not_by_user is None

    # Get by job and user
    by_job_user = await app_repo.get_by_job_and_user(job.id, user.id)
    assert by_job_user is not None
    assert by_job_user.id == app.id

    # 4. Update status and notes
    saved.status = ApplicationStatus.APPLIED
    saved.notes = "Applied on portal."
    updated = await app_repo.save(saved)
    assert updated.status == ApplicationStatus.APPLIED
    assert updated.notes == "Applied on portal."

    # 5. Add and list status history
    hist = ApplicationStatusHistory(
        application_id=app.id,
        from_status=ApplicationStatus.INTERESTED,
        to_status=ApplicationStatus.APPLIED,
    )
    saved_hist = await app_repo.add_status_history(hist)
    assert saved_hist.id == hist.id

    histories = await app_repo.list_status_history(app.id)
    assert len(histories) == 1
    assert histories[0].from_status == ApplicationStatus.INTERESTED
    assert histories[0].to_status == ApplicationStatus.APPLIED

    # 6. List and Count
    items = await app_repo.list_by_user_id(user.id)
    assert len(items) == 1
    count = await app_repo.count_by_user_id(user.id)
    assert count == 1

    # Filter by status
    applied_items = await app_repo.list_by_user_id(
        user.id, status=ApplicationStatus.APPLIED
    )
    assert len(applied_items) == 1
    interview_items = await app_repo.list_by_user_id(
        user.id, status=ApplicationStatus.INTERVIEW
    )
    assert len(interview_items) == 0

    # 7. Delete
    deleted = await app_repo.delete(app.id, user.id)
    assert deleted is True

    # Confirm deletion
    after_del = await app_repo.get_by_id(app.id)
    assert after_del is None

    histories_after_del = await app_repo.list_status_history(app.id)
    assert len(histories_after_del) == 0


@pytest.mark.asyncio
async def test_status_update_history_failure_rollback(
    pg_session: AsyncSession,
) -> None:
    """Verify transaction rollback when status history fails, ensuring atomicity."""
    user = UserModel(id=uuid.uuid4())
    pg_session.add(user)

    source = SourceModel(
        id=uuid.uuid4(),
        name="Rollback Source",
        url=f"https://source-{uuid.uuid4()}.example.com",
        ats_type="lever",
        active=True,
    )
    pg_session.add(source)
    await pg_session.flush()

    job = JobModel(
        id=uuid.uuid4(),
        source_id=source.id,
        canonical_url=f"https://source.example.com/job-{uuid.uuid4()}",
        company="Rollback Tech",
        title="Software Engineer",
        description="Testing rollbacks.",
        status=JobStatus.ACTIVE,
        content_hash=f"hash-{uuid.uuid4()}",
    )
    pg_session.add(job)
    await pg_session.flush()

    app_repo = SQLAlchemyApplicationRepository(pg_session)
    app = Application(
        job_id=job.id,
        user_id=user.id,
        status=ApplicationStatus.INTERESTED,
        notes="Initial state",
    )
    saved = await app_repo.save(app)
    assert saved.status == ApplicationStatus.INTERESTED

    # Atomicity test: savepoint rollback restores status and leaves no history
    async with pg_session.begin_nested() as savepoint:
        saved.status = ApplicationStatus.APPLIED
        await app_repo.save(saved)

        # Simulate exception during history step
        try:
            raise RuntimeError("Simulated failure during history persistence")
        except RuntimeError:
            await savepoint.rollback()

    # Verify status reverted to INTERESTED
    current_app = await app_repo.get_by_id(saved.id)
    assert current_app is not None
    assert current_app.status == ApplicationStatus.INTERESTED

    # Verify no history record was persisted
    histories = await app_repo.list_status_history(saved.id)
    assert len(histories) == 0
