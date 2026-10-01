"""API routes for candidate Application Tracking management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from backend.domain.application.entities import Application
from backend.domain.application.enums import ApplicationStatus
from backend.interfaces.api.dependencies.application import (
    ApplicationTrackingServiceDep,
)
from backend.interfaces.api.dependencies.auth import CurrentUserDep
from backend.interfaces.api.schemas.application import (
    ApplicationCreateRequest,
    ApplicationJobSummaryResponse,
    ApplicationListResponse,
    ApplicationNotesUpdateRequest,
    ApplicationResponse,
    ApplicationStatusHistoryResponse,
    ApplicationStatusUpdateRequest,
)

router = APIRouter(prefix="/applications", tags=["Application Tracking"])


def _to_application_response(app: Application) -> ApplicationResponse:
    """Transform domain Application entity to ApplicationResponse schema."""
    job_summary = None
    if app.job is not None:
        job_summary = ApplicationJobSummaryResponse(
            id=app.job.id,
            canonical_url=app.job.canonical_url,
            company=app.job.company,
            title=app.job.title,
            status=getattr(app.job.status, "value", app.job.status),
            location=app.job.location,
            work_mode=app.job.work_mode,
            employment_type=app.job.employment_type,
            salary=app.job.salary,
            source_name=app.job.source_name,
        )

    history_items = [
        ApplicationStatusHistoryResponse(
            id=h.id,
            application_id=h.application_id,
            from_status=getattr(h.from_status, "value", h.from_status),
            to_status=getattr(h.to_status, "value", h.to_status),
            changed_at=h.changed_at,
        )
        for h in app.status_history
    ]

    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        user_id=app.user_id,
        status=getattr(app.status, "value", app.status),
        notes=app.notes,
        created_at=app.created_at,
        updated_at=app.updated_at,
        job=job_summary,
        status_history=history_items,
    )


@router.get(
    "",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List candidate tracked applications",
    description=(
        "Retrieve all job applications tracked by the authenticated user "
        "with optional status filter."
    ),
)
async def list_applications(
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
    status_filter: ApplicationStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by lifecycle status (e.g. INTERESTED, APPLIED, INTERVIEW)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Page size limit",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Pagination offset",
    ),
) -> ApplicationListResponse:
    """List tracked applications for authenticated user."""
    items, total = await tracking_service.list_applications(
        user_id=current_user_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ApplicationListResponse(
        items=[_to_application_response(app) for app in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Track a job application",
    description=(
        "Start tracking a canonical job with an initial lifecycle status "
        "and optional notes."
    ),
)
async def create_application(
    payload: ApplicationCreateRequest,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> ApplicationResponse:
    """Create a new application tracking record."""
    saved = await tracking_service.track_application(
        user_id=current_user_id,
        job_id=payload.job_id,
        status=payload.status,
        notes=payload.notes,
    )
    # Re-retrieve to include job projection if needed
    detailed = await tracking_service.get_application(
        application_id=saved.id,
        user_id=current_user_id,
    )
    return _to_application_response(detailed)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application details",
    description=(
        "Retrieve detailed application data including canonical job summary "
        "and status transition history."
    ),
)
async def get_application(
    application_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> ApplicationResponse:
    """Retrieve tracked application details scoped to caller."""
    app = await tracking_service.get_application(
        application_id=application_id,
        user_id=current_user_id,
    )
    return _to_application_response(app)


@router.patch(
    "/{application_id}/status",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application lifecycle status",
    description=(
        "Advance or update an application's lifecycle status and record "
        "a status history audit entry."
    ),
)
async def update_application_status(
    application_id: uuid.UUID,
    payload: ApplicationStatusUpdateRequest,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> ApplicationResponse:
    """Transition application to a new status."""
    await tracking_service.update_status(
        application_id=application_id,
        user_id=current_user_id,
        new_status=payload.status,
    )
    # Re-retrieve fresh entity with populated job and history
    detailed = await tracking_service.get_application(
        application_id=application_id,
        user_id=current_user_id,
    )
    return _to_application_response(detailed)


@router.patch(
    "/{application_id}/notes",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate notes",
    description="Update private candidate notes for an existing tracked application.",
)
async def update_application_notes(
    application_id: uuid.UUID,
    payload: ApplicationNotesUpdateRequest,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> ApplicationResponse:
    """Update application candidate notes."""
    await tracking_service.update_notes(
        application_id=application_id,
        user_id=current_user_id,
        notes=payload.notes,
    )
    detailed = await tracking_service.get_application(
        application_id=application_id,
        user_id=current_user_id,
    )
    return _to_application_response(detailed)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop tracking application",
    description=(
        "Remove a tracked application and all associated status transition history."
    ),
)
async def delete_application(
    application_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> None:
    """Delete an application tracking record."""
    await tracking_service.delete_application(
        application_id=application_id,
        user_id=current_user_id,
    )


@router.get(
    "/{application_id}/history",
    response_model=list[ApplicationStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get status transition history",
    description=(
        "Retrieve chronological status transition audit log for an application."
    ),
)
async def get_application_history(
    application_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    tracking_service: ApplicationTrackingServiceDep,
) -> list[ApplicationStatusHistoryResponse]:
    """Retrieve status history for an owned application."""
    history = await tracking_service.get_status_history(
        application_id=application_id,
        user_id=current_user_id,
    )
    return [
        ApplicationStatusHistoryResponse(
            id=h.id,
            application_id=h.application_id,
            from_status=getattr(h.from_status, "value", h.from_status),
            to_status=getattr(h.to_status, "value", h.to_status),
            changed_at=h.changed_at,
        )
        for h in history
    ]
