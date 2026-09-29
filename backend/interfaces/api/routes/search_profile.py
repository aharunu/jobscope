"""API routes for candidate Search Profile management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from backend.application.profile_management.exceptions import (
    ProfileValidationError,
    SearchProfileNotFoundError,
)
from backend.interfaces.api.dependencies.auth import CurrentUserDep
from backend.interfaces.api.dependencies.profile import SearchProfileServiceDep
from backend.interfaces.api.schemas.search_profile import (
    SearchProfileCreateRequest,
    SearchProfileResponse,
    SearchProfileUpdateRequest,
)

router = APIRouter(prefix="/search-profiles", tags=["Search Profiles"])


@router.get(
    "",
    response_model=list[SearchProfileResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate search profiles",
    description=(
        "List all search profiles belonging to authenticated user's base profile."
    ),
)
async def list_search_profiles(
    current_user_id: CurrentUserDep,
    search_profile_service: SearchProfileServiceDep,
) -> list[SearchProfileResponse]:
    """List all search profiles belonging to authenticated user."""
    profiles = await search_profile_service.list_search_profiles(
        user_id=current_user_id
    )
    return [SearchProfileResponse.model_validate(p) for p in profiles]


@router.post(
    "",
    response_model=SearchProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create search profile",
    description=(
        "Create and attach a new search profile to the authenticated candidate profile."
    ),
)
async def create_search_profile(
    payload: SearchProfileCreateRequest,
    current_user_id: CurrentUserDep,
    search_profile_service: SearchProfileServiceDep,
) -> SearchProfileResponse:
    """Create a new search profile for caller."""
    try:
        sp = await search_profile_service.create_search_profile(
            user_id=current_user_id,
            name=payload.name,
            target_roles=payload.target_roles,
            seniority=payload.seniority,
            target_skills=payload.target_skills,
            locations=payload.locations,
            work_modes=payload.work_modes,
            industries=payload.industries,
            salary_min=payload.salary_min,
            salary_max=payload.salary_max,
        )
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return SearchProfileResponse.model_validate(sp)


@router.get(
    "/{search_profile_id}",
    response_model=SearchProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get search profile by ID",
    description="Retrieve a specific search profile ensuring caller ownership.",
)
async def get_search_profile(
    search_profile_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    search_profile_service: SearchProfileServiceDep,
) -> SearchProfileResponse:
    """Retrieve an existing search profile belonging to caller."""
    try:
        sp = await search_profile_service.get_search_profile(
            user_id=current_user_id,
            search_profile_id=search_profile_id,
        )
    except SearchProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    return SearchProfileResponse.model_validate(sp)


@router.patch(
    "/{search_profile_id}",
    response_model=SearchProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update search profile",
    description="Partially update an existing search profile belonging to caller.",
)
async def update_search_profile(
    search_profile_id: uuid.UUID,
    payload: SearchProfileUpdateRequest,
    current_user_id: CurrentUserDep,
    search_profile_service: SearchProfileServiceDep,
) -> SearchProfileResponse:
    """Partially update an existing search profile belonging to caller."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await search_profile_service.update_search_profile(
            user_id=current_user_id,
            search_profile_id=search_profile_id,
            updates=updates,
        )
    except SearchProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return SearchProfileResponse.model_validate(updated)


@router.delete(
    "/{search_profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete search profile",
    description="Delete an existing search profile belonging to caller.",
)
async def delete_search_profile(
    search_profile_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    search_profile_service: SearchProfileServiceDep,
) -> None:
    """Delete a search profile belonging to caller."""
    try:
        await search_profile_service.delete_search_profile(
            user_id=current_user_id,
            search_profile_id=search_profile_id,
        )
    except SearchProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
