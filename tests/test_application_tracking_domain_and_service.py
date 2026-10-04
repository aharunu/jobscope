"""Domain unit and service tests for candidate Application Tracking.

Validates Clean Architecture domain independence, status transition state machine,
in-memory application service orchestration, and strict candidate scoping.
"""

from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.application_tracking.exceptions import (
    ApplicationAlreadyExistsError,
    ApplicationNotFoundError,
    ApplicationValidationError,
    InvalidStatusTransitionError,
    JobNotFoundError,
)
from backend.application.application_tracking.services import (
    ApplicationTrackingService,
)
from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
    InvalidDomainTransitionError,
)
from backend.domain.application.enums import ApplicationStatus
from backend.domain.application.repositories import ApplicationRepository
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.repositories.application_repository import (
    SQLAlchemyApplicationRepository,
)

# ============================================================================
# 1. Clean Architecture & Protocol Conformance Tests
# ============================================================================


def test_application_domain_independence() -> None:
    """Verify application domain has zero persistence framework dependencies."""
    for mod_name in [
        "backend.domain.application.enums",
        "backend.domain.application.entities",
        "backend.domain.application.repositories",
    ]:
        mod = sys.modules.get(mod_name)
        assert mod is not None, f"Module {mod_name} not loaded"
        for attr_name, attr_val in mod.__dict__.items():
            if hasattr(attr_val, "__module__") and attr_val.__module__:
                err_msg = (
                    f"Domain module {mod_name} imports persistence: "
                    f"{attr_name} ({attr_val.__module__})"
                )
                assert "sqlalchemy" not in attr_val.__module__.lower(), err_msg
                assert "alembic" not in attr_val.__module__.lower(), err_msg


def test_application_repository_satisfies_protocol() -> None:
    """Verify concrete repository satisfies domain ApplicationRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyApplicationRepository(mock_session)
    assert isinstance(repo, ApplicationRepository)


# ============================================================================
# 2. Domain Entity and Status Transition State Machine Tests
# ============================================================================


def test_application_domain_entity_creation_and_defaults() -> None:
    """Verify Application domain entity defaults and slots."""
    job_id = uuid.uuid4()
    user_id = uuid.uuid4()

    app = Application(job_id=job_id, user_id=user_id)

    assert isinstance(app.id, uuid.UUID)
    assert app.job_id == job_id
    assert app.user_id == user_id
    assert app.status == ApplicationStatus.INTERESTED
    assert app.notes is None
    assert app.created_at is None
    assert app.updated_at is None
    assert app.job is None
    assert app.status_history == []


def test_status_transition_matrix_valid_paths() -> None:
    """Verify all valid lifecycle transition pathways defined in the state machine."""
    app_id = uuid.uuid4()

    valid_transitions = [
        # From INTERESTED
        (ApplicationStatus.INTERESTED, ApplicationStatus.APPLYING),
        (ApplicationStatus.INTERESTED, ApplicationStatus.APPLIED),
        (ApplicationStatus.INTERESTED, ApplicationStatus.REJECTED),
        # From APPLYING
        (ApplicationStatus.APPLYING, ApplicationStatus.INTERESTED),
        (ApplicationStatus.APPLYING, ApplicationStatus.APPLIED),
        (ApplicationStatus.APPLYING, ApplicationStatus.REJECTED),
        # From APPLIED
        (ApplicationStatus.APPLIED, ApplicationStatus.INTERVIEW),
        (ApplicationStatus.APPLIED, ApplicationStatus.OFFER),
        (ApplicationStatus.APPLIED, ApplicationStatus.REJECTED),
        # From INTERVIEW
        (ApplicationStatus.INTERVIEW, ApplicationStatus.APPLIED),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.REJECTED),
        # From OFFER
        (ApplicationStatus.OFFER, ApplicationStatus.REJECTED),
        # Reopening from REJECTED
        (ApplicationStatus.REJECTED, ApplicationStatus.INTERESTED),
        (ApplicationStatus.REJECTED, ApplicationStatus.APPLYING),
        (ApplicationStatus.REJECTED, ApplicationStatus.APPLIED),
        (ApplicationStatus.REJECTED, ApplicationStatus.INTERVIEW),
    ]

    for from_st, to_st in valid_transitions:
        app = Application(
            id=app_id,
            job_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            status=from_st,
        )
        assert app.can_transition_to(to_st) is True, f"Failed for {from_st} -> {to_st}"
        history = app.transition_to(to_st)
        assert app.status == to_st
        assert history.from_status == from_st
        assert history.to_status == to_st
        assert history.application_id == app.id
        assert len(app.status_history) == 1
        assert app.updated_at is not None


def test_status_transition_matrix_invalid_paths() -> None:
    """Verify invalid transition attempts raise InvalidDomainTransitionError."""
    invalid_transitions = [
        # Cannot skip to interview or offer before applying
        (ApplicationStatus.INTERESTED, ApplicationStatus.INTERVIEW),
        (ApplicationStatus.INTERESTED, ApplicationStatus.OFFER),
        (ApplicationStatus.APPLYING, ApplicationStatus.INTERVIEW),
        (ApplicationStatus.APPLYING, ApplicationStatus.OFFER),
        # Cannot revert backwards without rejection
        (ApplicationStatus.APPLIED, ApplicationStatus.INTERESTED),
        (ApplicationStatus.APPLIED, ApplicationStatus.APPLYING),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.INTERESTED),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.APPLYING),
        (ApplicationStatus.OFFER, ApplicationStatus.INTERESTED),
        (ApplicationStatus.OFFER, ApplicationStatus.APPLYING),
        (ApplicationStatus.OFFER, ApplicationStatus.APPLIED),
        (ApplicationStatus.OFFER, ApplicationStatus.INTERVIEW),
        # Same status transitions
        (ApplicationStatus.INTERESTED, ApplicationStatus.INTERESTED),
        (ApplicationStatus.APPLYING, ApplicationStatus.APPLYING),
        (ApplicationStatus.APPLIED, ApplicationStatus.APPLIED),
        (ApplicationStatus.INTERVIEW, ApplicationStatus.INTERVIEW),
        (ApplicationStatus.OFFER, ApplicationStatus.OFFER),
        (ApplicationStatus.REJECTED, ApplicationStatus.REJECTED),
    ]

    for from_st, to_st in invalid_transitions:
        app = Application(
            job_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            status=from_st,
        )
        assert app.can_transition_to(to_st) is False, (
            f"Expected can_transition_to({to_st}) False for {from_st}"
        )
        with pytest.raises(InvalidDomainTransitionError) as exc_info:
            app.transition_to(to_st)
        assert exc_info.value.from_status == from_st
        assert exc_info.value.to_status == to_st


def test_application_update_notes() -> None:
    """Verify notes updating modifies field and updates timestamp."""
    app = Application(job_id=uuid.uuid4(), user_id=uuid.uuid4())
    assert app.notes is None

    app.update_notes("Had intro chat with HR recruiter.")
    assert app.notes == "Had intro chat with HR recruiter."
    assert app.updated_at is not None

    app.update_notes(None)
    assert app.notes is None


# ============================================================================
# 3. In-Memory Test Doubles for Service Testing
# ============================================================================


class InMemoryApplicationRepository(ApplicationRepository):
    """In-memory test double conforming to ApplicationRepository."""

    def __init__(self) -> None:
        self.items: dict[uuid.UUID, Application] = {}
        self.history: list[ApplicationStatusHistory] = []

    async def get_by_id(self, application_id: uuid.UUID) -> Application | None:
        return self.items.get(application_id)

    async def get_by_id_and_user_id(
        self,
        application_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Application | None:
        app = self.items.get(application_id)
        if app is not None and app.user_id == user_id:
            return app
        return None

    async def get_by_job_and_user(
        self, job_id: uuid.UUID, user_id: uuid.UUID
    ) -> Application | None:
        for app in self.items.values():
            if app.job_id == job_id and app.user_id == user_id:
                return app
        return None

    async def list_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Application]:
        filtered = [
            app
            for app in self.items.values()
            if app.user_id == user_id and (status is None or app.status == status)
        ]
        return filtered[offset : offset + limit]

    async def count_by_user_id(
        self,
        user_id: uuid.UUID,
        status: ApplicationStatus | None = None,
    ) -> int:
        return len(
            [
                app
                for app in self.items.values()
                if app.user_id == user_id and (status is None or app.status == status)
            ]
        )

    async def save(self, application: Application) -> Application:
        self.items[application.id] = application
        return application

    async def delete(self, application_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        app = self.items.get(application_id)
        if app is not None and app.user_id == user_id:
            del self.items[application_id]
            self.history = [
                h for h in self.history if h.application_id != application_id
            ]
            return True
        return False

    async def add_status_history(
        self, history: ApplicationStatusHistory
    ) -> ApplicationStatusHistory:
        self.history.append(history)
        return history

    async def list_status_history(
        self, application_id: uuid.UUID
    ) -> list[ApplicationStatusHistory]:
        return [h for h in self.history if h.application_id == application_id]


class InMemoryJobRepository:
    """Minimal in-memory JobRepository test double."""

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self.jobs: dict[uuid.UUID, Job] = {j.id: j for j in (jobs or [])}

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)


# ============================================================================
# 4. Application Tracking Service Tests
# ============================================================================


@pytest.fixture
def mock_job() -> Job:
    """Fixture providing a sample canonical Job entity."""
    return Job(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        canonical_url="https://jobs.example.com/senior-backend-engineer",
        company="Acme Corp",
        title="Senior Backend Engineer",
        description="We are looking for a Python / async specialist.",
        content_hash="hash123",
        status=JobStatus.ACTIVE,
    )


@pytest.fixture
def tracking_service(
    mock_job: Job,
) -> tuple[
    ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
]:
    """Fixture providing configured service and in-memory test doubles."""
    app_repo = InMemoryApplicationRepository()
    job_repo = InMemoryJobRepository([mock_job])
    service = ApplicationTrackingService(app_repo=app_repo, job_repo=job_repo)
    return service, app_repo, job_repo


@pytest.mark.asyncio
async def test_track_application_happy_path(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify tracking a new application with defaults and notes."""
    service, app_repo, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        notes="Applied via company portal.",
    )

    assert app.id in app_repo.items
    assert app.user_id == user_id
    assert app.job_id == mock_job.id
    assert app.status == ApplicationStatus.INTERESTED
    assert app.notes == "Applied via company portal."


@pytest.mark.asyncio
async def test_track_application_custom_status(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify tracking directly with custom status (e.g. APPLIED)."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        status=ApplicationStatus.APPLIED,
    )
    assert app.status == ApplicationStatus.APPLIED


@pytest.mark.asyncio
async def test_track_application_non_existent_job_fails(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
) -> None:
    """Verify tracking a non-existent job raises JobNotFoundError."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()
    missing_job_id = uuid.uuid4()

    with pytest.raises(JobNotFoundError) as exc_info:
        await service.track_application(user_id=user_id, job_id=missing_job_id)
    assert str(missing_job_id) in str(exc_info.value)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_track_application_duplicate_fails(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify tracking duplicate job by same user raises error."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    await service.track_application(user_id=user_id, job_id=mock_job.id)

    with pytest.raises(ApplicationAlreadyExistsError) as exc_info:
        await service.track_application(user_id=user_id, job_id=mock_job.id)
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_track_application_exceeding_notes_length_fails(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify notes length limit is enforced."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    with pytest.raises(ApplicationValidationError) as exc_info:
        await service.track_application(
            user_id=user_id,
            job_id=mock_job.id,
            notes="a" * 5001,
        )
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_list_and_count_applications(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify listing and counting with status filtering and pagination."""
    service, _, job_repo = tracking_service
    user_id = uuid.uuid4()

    # Create additional jobs
    job2 = Job(
        id=uuid.uuid4(),
        source_id=mock_job.source_id,
        canonical_url="https://jobs.example.com/job-2",
        company="Beta Ltd",
        title="Frontend Dev",
        description="React",
        content_hash="h2",
    )
    job3 = Job(
        id=uuid.uuid4(),
        source_id=mock_job.source_id,
        canonical_url="https://jobs.example.com/job-3",
        company="Gamma Inc",
        title="DevOps Engineer",
        description="K8s",
        content_hash="h3",
    )
    job_repo.jobs[job2.id] = job2
    job_repo.jobs[job3.id] = job3

    await service.track_application(
        user_id=user_id, job_id=mock_job.id, status=ApplicationStatus.INTERESTED
    )
    await service.track_application(
        user_id=user_id, job_id=job2.id, status=ApplicationStatus.APPLIED
    )
    await service.track_application(
        user_id=user_id, job_id=job3.id, status=ApplicationStatus.APPLIED
    )

    # List all
    items, total = await service.list_applications(user_id=user_id)
    assert total == 3
    assert len(items) == 3

    # Filter by APPLIED
    applied_items, applied_total = await service.list_applications(
        user_id=user_id, status=ApplicationStatus.APPLIED
    )
    assert applied_total == 2
    assert len(applied_items) == 2
    assert all(a.status == ApplicationStatus.APPLIED for a in applied_items)

    # Pagination bounds validation
    with pytest.raises(ApplicationValidationError):
        await service.list_applications(user_id=user_id, limit=0)
    with pytest.raises(ApplicationValidationError):
        await service.list_applications(user_id=user_id, limit=101)
    with pytest.raises(ApplicationValidationError):
        await service.list_applications(user_id=user_id, offset=-1)


@pytest.mark.asyncio
async def test_update_status_and_history_logging(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify advancing status records transition history."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        status=ApplicationStatus.INTERESTED,
    )

    # 1. INTERESTED -> APPLYING
    updated = await service.update_status(
        application_id=app.id,
        user_id=user_id,
        new_status=ApplicationStatus.APPLYING,
    )
    assert updated.status == ApplicationStatus.APPLYING

    # 2. APPLYING -> APPLIED
    updated = await service.update_status(
        application_id=app.id,
        user_id=user_id,
        new_status=ApplicationStatus.APPLIED,
    )
    assert updated.status == ApplicationStatus.APPLIED

    # Check history
    history = await service.get_status_history(
        application_id=app.id,
        user_id=user_id,
    )
    assert len(history) == 2
    assert history[0].from_status == ApplicationStatus.INTERESTED
    assert history[0].to_status == ApplicationStatus.APPLYING
    assert history[1].from_status == ApplicationStatus.APPLYING
    assert history[1].to_status == ApplicationStatus.APPLIED


@pytest.mark.asyncio
async def test_update_status_invalid_transition_fails(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify illegal status transition raises InvalidStatusTransitionError."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        status=ApplicationStatus.INTERESTED,
    )

    # Cannot skip straight to OFFER
    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        await service.update_status(
            application_id=app.id,
            user_id=user_id,
            new_status=ApplicationStatus.OFFER,
        )
    assert exc_info.value.status_code == 422
    assert "Cannot transition" in exc_info.value.message


@pytest.mark.asyncio
async def test_update_status_same_status_fails(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify transitioning to current status is rejected."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        status=ApplicationStatus.INTERESTED,
    )

    with pytest.raises(InvalidStatusTransitionError) as exc_info:
        await service.update_status(
            application_id=app.id,
            user_id=user_id,
            new_status=ApplicationStatus.INTERESTED,
        )
    assert exc_info.value.status_code == 422
    assert "already in status" in exc_info.value.message


@pytest.mark.asyncio
async def test_update_notes(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify updating candidate notes."""
    service, _, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(
        user_id=user_id,
        job_id=mock_job.id,
        notes="Initial note",
    )

    updated = await service.update_notes(
        application_id=app.id,
        user_id=user_id,
        notes="Updated interview prep details.",
    )
    assert updated.notes == "Updated interview prep details."


@pytest.mark.asyncio
async def test_delete_application(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify deleting application removes it completely."""
    service, app_repo, _ = tracking_service
    user_id = uuid.uuid4()

    app = await service.track_application(user_id=user_id, job_id=mock_job.id)
    assert app.id in app_repo.items

    deleted = await service.delete_application(
        application_id=app.id,
        user_id=user_id,
    )
    assert deleted is True
    assert app.id not in app_repo.items

    with pytest.raises(ApplicationNotFoundError):
        await service.get_application(application_id=app.id, user_id=user_id)


@pytest.mark.asyncio
async def test_strict_user_scoping_and_cross_user_isolation(
    tracking_service: tuple[
        ApplicationTrackingService, InMemoryApplicationRepository, InMemoryJobRepository
    ],
    mock_job: Job,
) -> None:
    """Verify User A cannot read, modify, or delete User B's tracked application."""
    service, _, _ = tracking_service
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    app_a = await service.track_application(
        user_id=user_a,
        job_id=mock_job.id,
        notes="User A private notes",
    )

    # User B should NOT be able to view User A's application
    with pytest.raises(ApplicationNotFoundError):
        await service.get_application(application_id=app_a.id, user_id=user_b)

    # User B should NOT be able to update status
    with pytest.raises(ApplicationNotFoundError):
        await service.update_status(
            application_id=app_a.id,
            user_id=user_b,
            new_status=ApplicationStatus.APPLIED,
        )

    # User B should NOT be able to update notes
    with pytest.raises(ApplicationNotFoundError):
        await service.update_notes(
            application_id=app_a.id,
            user_id=user_b,
            notes="Malicious update",
        )

    # User B should NOT be able to view history
    with pytest.raises(ApplicationNotFoundError):
        await service.get_status_history(
            application_id=app_a.id,
            user_id=user_b,
        )

    # User B should NOT be able to delete User A's application
    with pytest.raises(ApplicationNotFoundError):
        await service.delete_application(
            application_id=app_a.id,
            user_id=user_b,
        )

    # User B can track the SAME job without conflict (user scoping on UNIQUE constraint)
    app_b = await service.track_application(
        user_id=user_b,
        job_id=mock_job.id,
        notes="User B private notes",
    )
    assert app_b.id != app_a.id
    assert app_b.user_id == user_b
