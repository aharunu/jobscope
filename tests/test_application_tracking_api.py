"""API integration tests for Application Tracking endpoints (/api/applications).

Validates:
- POST /api/applications (creation with defaults, custom status, notes, validation)
- GET /api/applications (listing, status filtering, pagination)
- GET /api/applications/{id} (detailed retrieval with job & history)
- PATCH /api/applications/{id}/status (lifecycle transitions and history logging)
- PATCH /api/applications/{id}/notes (candidate notes modification)
- DELETE /api/applications/{id} (removal)
- GET /api/applications/{id}/history (chronological status transition audit log)
- Strict multi-tenant isolation and user scoping
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from backend.application.application_tracking.services import (
    ApplicationTrackingService,
)
from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
)
from backend.domain.application.enums import ApplicationStatus
from backend.domain.application.repositories import ApplicationRepository
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository
from backend.infrastructure.config.settings import Settings, get_settings
from backend.interfaces.api.dependencies.application import (
    get_application_tracking_service,
)
from backend.interfaces.api.dependencies.database import get_db_session
from backend.interfaces.api.main import create_app

# ============================================================================
# In-Memory Test Doubles
# ============================================================================


class ApiTestApplicationRepository(ApplicationRepository):
    """In-memory ApplicationRepository for deterministic API testing."""

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


class ApiTestJobRepository(JobRepository):
    """In-memory JobRepository for API testing."""

    def __init__(self, jobs: list[Job] | None = None) -> None:
        self.jobs: dict[uuid.UUID, Job] = {j.id: j for j in (jobs or [])}

    async def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self.jobs.get(job_id)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_job() -> Job:
    """Fixture providing a canonical Job."""
    return Job(
        id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.uuid4(),
        canonical_url="https://jobs.example.com/staff-python-engineer",
        company="Nexus Dynamics",
        title="Staff Python Engineer",
        description="Lead backend architecture and event pipelines.",
        content_hash="contenthash999",
        status=JobStatus.ACTIVE,
        location="Remote, Worldwide",
        work_mode="remote",
        employment_type="full_time",
        salary="$160,000 - $190,000",
        source_name="Nexus Careers",
    )


@pytest.fixture
def user_a_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def user_b_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def api_context(sample_job: Job):
    """Setup configured FastAPI TestClient with in-memory double repositories."""
    settings = Settings(
        app_name="JobScope-AppTest",
        environment="test",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
    )
    app = create_app(settings=settings)

    app_repo = ApiTestApplicationRepository()
    job_repo = ApiTestJobRepository([sample_job])
    service = ApplicationTrackingService(app_repo=app_repo, job_repo=job_repo)

    from unittest.mock import AsyncMock

    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.infrastructure.database.models.user import UserModel

    users: dict[uuid.UUID, UserModel] = {}

    async def mock_get(model_cls, ident):
        if model_cls is UserModel:
            return users.get(ident)
        return None

    def mock_add(instance):
        if isinstance(instance, UserModel):
            users[instance.id] = instance

    session_inst = AsyncMock(spec=AsyncSession)
    session_inst.get.side_effect = mock_get
    session_inst.add.side_effect = mock_add
    session_inst.flush = AsyncMock()
    session_inst.commit = AsyncMock()
    session_inst.close = AsyncMock()

    async def mock_db_session_gen():
        yield session_inst

    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_db_session] = mock_db_session_gen
    app.dependency_overrides[get_application_tracking_service] = lambda: service

    client = TestClient(app)
    return client, service, app_repo, job_repo


# ============================================================================
# 1. POST /api/applications Tests
# ============================================================================


def test_create_application_success(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify creating application tracking record with 201 Created."""
    client, _, _, _ = api_context

    response = client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={
            "job_id": str(sample_job.id),
            "status": "INTERESTED",
            "notes": "Bookmarked for weekend application.",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["job_id"] == str(sample_job.id)
    assert data["user_id"] == str(user_a_id)
    assert data["status"] == "INTERESTED"
    assert data["notes"] == "Bookmarked for weekend application."
    assert "id" in data
    assert data["job"] is not None
    assert data["job"]["company"] == "Nexus Dynamics"
    assert data["job"]["title"] == "Staff Python Engineer"


def test_create_application_default_status(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify omitting status defaults to INTERESTED."""
    client, _, _, _ = api_context

    response = client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={"job_id": str(sample_job.id)},
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["status"] == "INTERESTED"
    assert data["notes"] is None


def test_create_application_non_existent_job_returns_404(
    api_context, user_a_id: uuid.UUID
) -> None:
    """Verify tracking unknown job returns 404."""
    client, _, _, _ = api_context
    missing_job_id = uuid.uuid4()

    response = client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={"job_id": str(missing_job_id)},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    error_data = response.json()
    assert error_data["error"]["code"] == "JOB_NOT_FOUND"


def test_create_application_duplicate_returns_409(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify tracking already tracked job returns 409 Conflict."""
    client, _, _, _ = api_context

    # First track
    client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={"job_id": str(sample_job.id)},
    )

    # Second track attempt
    response = client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={"job_id": str(sample_job.id)},
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    error_data = response.json()
    assert error_data["error"]["code"] == "APPLICATION_ALREADY_EXISTS"


def test_create_application_validation_error_forbidden_fields(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify extra payload fields are rejected with 422."""
    client, _, _, _ = api_context

    response = client.post(
        "/api/applications",
        headers={"X-User-Id": str(user_a_id)},
        json={
            "job_id": str(sample_job.id),
            "extra_field": "not_allowed",
        },
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# ============================================================================
# 2. GET /api/applications & GET /api/applications/{id} Tests
# ============================================================================


def test_list_applications_with_status_filter_and_pagination(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify listing applications with status filter and limit/offset."""
    client, _, app_repo, job_repo = api_context

    job2 = Job(
        id=uuid.uuid4(),
        source_id=sample_job.source_id,
        canonical_url="https://jobs.example.com/job-2",
        company="Second Corp",
        title="Frontend Dev",
        description="Vue",
        content_hash="h2",
    )
    job_repo.jobs[job2.id] = job2

    # Create 2 applications
    app1 = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app2 = Application(
        job_id=job2.id,
        user_id=user_a_id,
        status=ApplicationStatus.APPLIED,
        job=job2,
    )
    app_repo.items[app1.id] = app1
    app_repo.items[app2.id] = app2

    # List all
    res = client.get("/api/applications", headers={"X-User-Id": str(user_a_id)})
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2

    # Filter by APPLIED
    res_filtered = client.get(
        "/api/applications?status=APPLIED",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert res_filtered.status_code == status.HTTP_200_OK
    filtered_data = res_filtered.json()
    assert filtered_data["total"] == 1
    assert len(filtered_data["items"]) == 1
    assert filtered_data["items"][0]["status"] == "APPLIED"

    # Pagination: limit=1
    res_paged = client.get(
        "/api/applications?limit=1&offset=0",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert res_paged.status_code == status.HTTP_200_OK
    paged_data = res_paged.json()
    assert paged_data["total"] == 2
    assert len(paged_data["items"]) == 1
    assert paged_data["limit"] == 1


def test_get_application_by_id_success(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify getting application by primary key ID."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERVIEW,
        notes="Interview scheduled for Monday.",
        job=sample_job,
    )
    app_repo.items[app.id] = app

    res = client.get(
        f"/api/applications/{app.id}",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["id"] == str(app.id)
    assert data["status"] == "INTERVIEW"
    assert data["notes"] == "Interview scheduled for Monday."
    assert data["job"]["company"] == "Nexus Dynamics"


def test_get_application_by_id_not_found(api_context, user_a_id: uuid.UUID) -> None:
    """Verify 404 for non-existent application ID."""
    client, _, _, _ = api_context
    non_existent = uuid.uuid4()

    res = client.get(
        f"/api/applications/{non_existent}",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_get_application_cross_user_isolation_returns_404(
    api_context, sample_job: Job, user_a_id: uuid.UUID, user_b_id: uuid.UUID
) -> None:
    """Verify User B cannot access User A's application."""
    client, _, app_repo, _ = api_context

    app_a = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app_a.id] = app_a

    # User B requests User A's application
    res = client.get(
        f"/api/applications/{app_a.id}",
        headers={"X-User-Id": str(user_b_id)},
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND


# ============================================================================
# 3. PATCH /api/applications/{id}/status & PATCH notes Tests
# ============================================================================


def test_update_status_lifecycle_and_history(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify status transition records history and returns updated entity."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app.id] = app

    # Transition INTERESTED -> APPLYING
    res = client.patch(
        f"/api/applications/{app.id}/status",
        headers={"X-User-Id": str(user_a_id)},
        json={"status": "APPLYING"},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["status"] == "APPLYING"

    # Transition APPLYING -> APPLIED
    res2 = client.patch(
        f"/api/applications/{app.id}/status",
        headers={"X-User-Id": str(user_a_id)},
        json={"status": "APPLIED"},
    )
    assert res2.status_code == status.HTTP_200_OK
    assert res2.json()["status"] == "APPLIED"

    # Verify history endpoint
    hist_res = client.get(
        f"/api/applications/{app.id}/history",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert hist_res.status_code == status.HTTP_200_OK
    history = hist_res.json()
    assert len(history) == 2
    assert history[0]["from_status"] == "INTERESTED"
    assert history[0]["to_status"] == "APPLYING"
    assert history[1]["from_status"] == "APPLYING"
    assert history[1]["to_status"] == "APPLIED"


def test_update_status_illegal_transition_returns_422(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify illegal status jump returns 422 Unprocessable Entity."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app.id] = app

    # Cannot jump straight from INTERESTED to OFFER
    res = client.patch(
        f"/api/applications/{app.id}/status",
        headers={"X-User-Id": str(user_a_id)},
        json={"status": "OFFER"},
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error_data = res.json()
    assert error_data["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_update_status_same_status_returns_422(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify transitioning to identical status returns 422."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app.id] = app

    res = client.patch(
        f"/api/applications/{app.id}/status",
        headers={"X-User-Id": str(user_a_id)},
        json={"status": "INTERESTED"},
    )
    assert res.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    error_data = res.json()
    assert error_data["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_update_notes_success(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify updating candidate notes."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app.id] = app

    res = client.patch(
        f"/api/applications/{app.id}/notes",
        headers={"X-User-Id": str(user_a_id)},
        json={"notes": "Followed up with engineering manager on LinkedIn."},
    )
    assert res.status_code == status.HTTP_200_OK
    assert res.json()["notes"] == "Followed up with engineering manager on LinkedIn."


# ============================================================================
# 4. DELETE /api/applications/{id} Tests
# ============================================================================


def test_delete_application_success(
    api_context, sample_job: Job, user_a_id: uuid.UUID
) -> None:
    """Verify deleting application returns 204 and removes record."""
    client, _, app_repo, _ = api_context

    app = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app.id] = app

    # Delete
    del_res = client.delete(
        f"/api/applications/{app.id}",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert del_res.status_code == status.HTTP_204_NO_CONTENT

    # Verify subsequent GET returns 404
    get_res = client.get(
        f"/api/applications/{app.id}",
        headers={"X-User-Id": str(user_a_id)},
    )
    assert get_res.status_code == status.HTTP_404_NOT_FOUND


def test_delete_application_cross_user_fails(
    api_context, sample_job: Job, user_a_id: uuid.UUID, user_b_id: uuid.UUID
) -> None:
    """Verify User B cannot delete User A's application."""
    client, _, app_repo, _ = api_context

    app_a = Application(
        job_id=sample_job.id,
        user_id=user_a_id,
        status=ApplicationStatus.INTERESTED,
        job=sample_job,
    )
    app_repo.items[app_a.id] = app_a

    res = client.delete(
        f"/api/applications/{app_a.id}",
        headers={"X-User-Id": str(user_b_id)},
    )
    assert res.status_code == status.HTTP_404_NOT_FOUND
    assert app_a.id in app_repo.items
