"""API routes for candidate Base Profile and child collection management."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from backend.application.profile_management.exceptions import (
    ProfileNotFoundError,
    ProfileValidationError,
)
from backend.interfaces.api.dependencies.auth import CurrentUserDep
from backend.interfaces.api.dependencies.profile import (
    BaseProfileServiceDep,
    ProfileEducationServiceDep,
    ProfileExperienceServiceDep,
    ProfileProjectServiceDep,
    ProfileSkillServiceDep,
)
from backend.interfaces.api.schemas.profile import (
    BaseProfileResponse,
    BaseProfileUpdateRequest,
    ProfileEducationCreateRequest,
    ProfileEducationResponse,
    ProfileEducationUpdateRequest,
    ProfileExperienceCreateRequest,
    ProfileExperienceResponse,
    ProfileExperienceUpdateRequest,
    ProfileProjectCreateRequest,
    ProfileProjectResponse,
    ProfileProjectUpdateRequest,
    ProfileSkillCreateRequest,
    ProfileSkillResponse,
    ProfileSkillUpdateRequest,
)

router = APIRouter(prefix="/profile", tags=["Profile"])


# ============================================================================
# Root BaseProfile Endpoints
# ============================================================================


@router.get(
    "",
    response_model=BaseProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current candidate base profile",
    description=(
        "Retrieve the authenticated candidate's Base Profile along with all "
        "skills, experiences, educations, and projects. Auto-provisions a blank "
        "profile if one does not already exist."
    ),
)
async def get_current_profile(
    current_user_id: CurrentUserDep,
    profile_service: BaseProfileServiceDep,
) -> BaseProfileResponse:
    """Retrieve base profile for current user context."""
    profile = await profile_service.get_or_create_profile(user_id=current_user_id)
    return BaseProfileResponse.model_validate(profile)


@router.patch(
    "",
    response_model=BaseProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update candidate base profile metadata",
    description=(
        "Partially update root metadata (name, summary) for the authenticated "
        "candidate's Base Profile without altering child collections."
    ),
)
async def update_current_profile(
    payload: BaseProfileUpdateRequest,
    current_user_id: CurrentUserDep,
    profile_service: BaseProfileServiceDep,
) -> BaseProfileResponse:
    """Update root metadata for caller's base profile."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await profile_service.update_profile(
            user_id=current_user_id,
            updates=updates,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err

    return BaseProfileResponse.model_validate(updated)


# ============================================================================
# Skill Endpoints
# ============================================================================


@router.get(
    "/skills",
    response_model=list[ProfileSkillResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate skills",
)
async def list_skills(
    current_user_id: CurrentUserDep,
    skill_service: ProfileSkillServiceDep,
) -> list[ProfileSkillResponse]:
    """List all skills belonging to authenticated user's base profile."""
    skills = await skill_service.list_skills(user_id=current_user_id)
    return [ProfileSkillResponse.model_validate(s) for s in skills]


@router.post(
    "/skills",
    response_model=ProfileSkillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add skill to profile",
)
async def create_skill(
    payload: ProfileSkillCreateRequest,
    current_user_id: CurrentUserDep,
    skill_service: ProfileSkillServiceDep,
) -> ProfileSkillResponse:
    """Create and attach a new skill to the authenticated candidate profile."""
    try:
        skill = await skill_service.create_skill(
            user_id=current_user_id,
            name=payload.name,
            category=payload.category,
            years_of_experience=payload.years_of_experience,
            level=payload.level,
        )
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileSkillResponse.model_validate(skill)


@router.patch(
    "/skills/{skill_id}",
    response_model=ProfileSkillResponse,
    status_code=status.HTTP_200_OK,
    summary="Update skill",
)
async def update_skill(
    skill_id: uuid.UUID,
    payload: ProfileSkillUpdateRequest,
    current_user_id: CurrentUserDep,
    skill_service: ProfileSkillServiceDep,
) -> ProfileSkillResponse:
    """Partially update an existing skill belonging to caller."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await skill_service.update_skill(
            user_id=current_user_id,
            skill_id=skill_id,
            updates=updates,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileSkillResponse.model_validate(updated)


@router.delete(
    "/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete skill",
)
async def delete_skill(
    skill_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    skill_service: ProfileSkillServiceDep,
) -> None:
    """Delete a skill from caller's base profile."""
    try:
        await skill_service.delete_skill(
            user_id=current_user_id,
            skill_id=skill_id,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


# ============================================================================
# Experience Endpoints
# ============================================================================


@router.get(
    "/experiences",
    response_model=list[ProfileExperienceResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate work experiences",
)
async def list_experiences(
    current_user_id: CurrentUserDep,
    experience_service: ProfileExperienceServiceDep,
) -> list[ProfileExperienceResponse]:
    """List all work experiences belonging to authenticated user's base profile."""
    experiences = await experience_service.list_experiences(user_id=current_user_id)
    return [ProfileExperienceResponse.model_validate(e) for e in experiences]


@router.post(
    "/experiences",
    response_model=ProfileExperienceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add experience to profile",
)
async def create_experience(
    payload: ProfileExperienceCreateRequest,
    current_user_id: CurrentUserDep,
    experience_service: ProfileExperienceServiceDep,
) -> ProfileExperienceResponse:
    """Create and attach a work experience to the authenticated candidate profile."""
    try:
        experience = await experience_service.create_experience(
            user_id=current_user_id,
            company=payload.company,
            title=payload.title,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_current=payload.is_current,
            description=payload.description,
            skills_used=payload.skills_used,
        )
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileExperienceResponse.model_validate(experience)


@router.patch(
    "/experiences/{experience_id}",
    response_model=ProfileExperienceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update experience",
)
async def update_experience(
    experience_id: uuid.UUID,
    payload: ProfileExperienceUpdateRequest,
    current_user_id: CurrentUserDep,
    experience_service: ProfileExperienceServiceDep,
) -> ProfileExperienceResponse:
    """Partially update an existing work experience belonging to caller."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await experience_service.update_experience(
            user_id=current_user_id,
            experience_id=experience_id,
            updates=updates,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileExperienceResponse.model_validate(updated)


@router.delete(
    "/experiences/{experience_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete experience",
)
async def delete_experience(
    experience_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    experience_service: ProfileExperienceServiceDep,
) -> None:
    """Delete a work experience from caller's base profile."""
    try:
        await experience_service.delete_experience(
            user_id=current_user_id,
            experience_id=experience_id,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


# ============================================================================
# Education Endpoints
# ============================================================================


@router.get(
    "/educations",
    response_model=list[ProfileEducationResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate education records",
)
async def list_educations(
    current_user_id: CurrentUserDep,
    education_service: ProfileEducationServiceDep,
) -> list[ProfileEducationResponse]:
    """List all education records belonging to authenticated user's base profile."""
    educations = await education_service.list_educations(user_id=current_user_id)
    return [ProfileEducationResponse.model_validate(e) for e in educations]


@router.post(
    "/educations",
    response_model=ProfileEducationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add education record to profile",
)
async def create_education(
    payload: ProfileEducationCreateRequest,
    current_user_id: CurrentUserDep,
    education_service: ProfileEducationServiceDep,
) -> ProfileEducationResponse:
    """Create and attach an education record to the authenticated candidate profile."""
    try:
        education = await education_service.create_education(
            user_id=current_user_id,
            school=payload.school,
            degree=payload.degree,
            field_of_study=payload.field_of_study,
            start_year=payload.start_year,
            end_year=payload.end_year,
        )
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileEducationResponse.model_validate(education)


@router.patch(
    "/educations/{education_id}",
    response_model=ProfileEducationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update education record",
)
async def update_education(
    education_id: uuid.UUID,
    payload: ProfileEducationUpdateRequest,
    current_user_id: CurrentUserDep,
    education_service: ProfileEducationServiceDep,
) -> ProfileEducationResponse:
    """Partially update an existing education record belonging to caller."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await education_service.update_education(
            user_id=current_user_id,
            education_id=education_id,
            updates=updates,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileEducationResponse.model_validate(updated)


@router.delete(
    "/educations/{education_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete education record",
)
async def delete_education(
    education_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    education_service: ProfileEducationServiceDep,
) -> None:
    """Delete an education record from caller's base profile."""
    try:
        await education_service.delete_education(
            user_id=current_user_id,
            education_id=education_id,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


# ============================================================================
# Project Endpoints
# ============================================================================


@router.get(
    "/projects",
    response_model=list[ProfileProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate projects",
)
async def list_projects(
    current_user_id: CurrentUserDep,
    project_service: ProfileProjectServiceDep,
) -> list[ProfileProjectResponse]:
    """List all projects belonging to authenticated user's base profile."""
    projects = await project_service.list_projects(user_id=current_user_id)
    return [ProfileProjectResponse.model_validate(p) for p in projects]


@router.post(
    "/projects",
    response_model=ProfileProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add project to profile",
)
async def create_project(
    payload: ProfileProjectCreateRequest,
    current_user_id: CurrentUserDep,
    project_service: ProfileProjectServiceDep,
) -> ProfileProjectResponse:
    """Create and attach a project item to the authenticated candidate profile."""
    try:
        project = await project_service.create_project(
            user_id=current_user_id,
            title=payload.title,
            description=payload.description,
            skills_used=payload.skills_used,
            url=payload.url,
        )
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileProjectResponse.model_validate(project)


@router.patch(
    "/projects/{project_id}",
    response_model=ProfileProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project",
)
async def update_project(
    project_id: uuid.UUID,
    payload: ProfileProjectUpdateRequest,
    current_user_id: CurrentUserDep,
    project_service: ProfileProjectServiceDep,
) -> ProfileProjectResponse:
    """Partially update an existing project item belonging to caller."""
    updates = payload.model_dump(exclude_unset=True)
    try:
        updated = await project_service.update_project(
            user_id=current_user_id,
            project_id=project_id,
            updates=updates,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ProfileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        ) from err
    return ProfileProjectResponse.model_validate(updated)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user_id: CurrentUserDep,
    project_service: ProfileProjectServiceDep,
) -> None:
    """Delete a project item from caller's base profile."""
    try:
        await project_service.delete_project(
            user_id=current_user_id,
            project_id=project_id,
        )
    except ProfileNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
