"""FastAPI dependencies for profile and child collection management."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.profile_management.child_services import (
    ProfileEducationService,
    ProfileExperienceService,
    ProfileProjectService,
    ProfileSkillService,
)
from backend.application.profile_management.search_profile_service import (
    SearchProfileService,
)
from backend.application.profile_management.services import BaseProfileService
from backend.application.profile_management.skill_suggestions import SkillSuggestions
from backend.domain.profile.repositories import (
    ProfileEducationRepository,
    ProfileExperienceRepository,
    ProfileProjectRepository,
    ProfileSkillRepository,
)
from backend.infrastructure.database.repositories.profile_child_repositories import (
    SQLAlchemyProfileEducationRepository,
    SQLAlchemyProfileExperienceRepository,
    SQLAlchemyProfileProjectRepository,
    SQLAlchemyProfileSkillRepository,
)
from backend.infrastructure.extraction.taxonomy import TECHNICAL_SKILLS
from backend.interfaces.api.dependencies.database import DbSession
from backend.interfaces.api.dependencies.matching import (
    BaseProfileRepositoryDep,
    SearchProfileRepositoryDep,
)


def get_base_profile_service(
    base_profile_repo: BaseProfileRepositoryDep,
) -> BaseProfileService:
    """Provide a BaseProfileService instance bound to the request."""
    return BaseProfileService(base_profile_repo=base_profile_repo)


BaseProfileServiceDep = Annotated[BaseProfileService, Depends(get_base_profile_service)]


def get_skill_suggestions() -> SkillSuggestions:
    return SkillSuggestions(tuple(name for name, _, _ in TECHNICAL_SKILLS))


SkillSuggestionsDep = Annotated[SkillSuggestions, Depends(get_skill_suggestions)]


# ============================================================================
# Skill Dependencies
# ============================================================================


def get_profile_skill_repository(session: DbSession) -> ProfileSkillRepository:
    """Provide a ProfileSkillRepository instance bound to request session."""
    return SQLAlchemyProfileSkillRepository(session)


ProfileSkillRepositoryDep = Annotated[
    ProfileSkillRepository, Depends(get_profile_skill_repository)
]


def get_profile_skill_service(
    base_profile_repo: BaseProfileRepositoryDep,
    skill_repo: ProfileSkillRepositoryDep,
) -> ProfileSkillService:
    """Provide a ProfileSkillService instance bound to the request."""
    return ProfileSkillService(
        base_profile_repo=base_profile_repo,
        skill_repo=skill_repo,
    )


ProfileSkillServiceDep = Annotated[
    ProfileSkillService, Depends(get_profile_skill_service)
]


# ============================================================================
# Experience Dependencies
# ============================================================================


def get_profile_experience_repository(
    session: DbSession,
) -> ProfileExperienceRepository:
    """Provide a ProfileExperienceRepository instance bound to request session."""
    return SQLAlchemyProfileExperienceRepository(session)


ProfileExperienceRepositoryDep = Annotated[
    ProfileExperienceRepository, Depends(get_profile_experience_repository)
]


def get_profile_experience_service(
    base_profile_repo: BaseProfileRepositoryDep,
    experience_repo: ProfileExperienceRepositoryDep,
) -> ProfileExperienceService:
    """Provide a ProfileExperienceService instance bound to the request."""
    return ProfileExperienceService(
        base_profile_repo=base_profile_repo,
        experience_repo=experience_repo,
    )


ProfileExperienceServiceDep = Annotated[
    ProfileExperienceService, Depends(get_profile_experience_service)
]


# ============================================================================
# Education Dependencies
# ============================================================================


def get_profile_education_repository(
    session: DbSession,
) -> ProfileEducationRepository:
    """Provide a ProfileEducationRepository instance bound to request session."""
    return SQLAlchemyProfileEducationRepository(session)


ProfileEducationRepositoryDep = Annotated[
    ProfileEducationRepository, Depends(get_profile_education_repository)
]


def get_profile_education_service(
    base_profile_repo: BaseProfileRepositoryDep,
    education_repo: ProfileEducationRepositoryDep,
) -> ProfileEducationService:
    """Provide a ProfileEducationService instance bound to the request."""
    return ProfileEducationService(
        base_profile_repo=base_profile_repo,
        education_repo=education_repo,
    )


ProfileEducationServiceDep = Annotated[
    ProfileEducationService, Depends(get_profile_education_service)
]


# ============================================================================
# Project Dependencies
# ============================================================================


def get_profile_project_repository(
    session: DbSession,
) -> ProfileProjectRepository:
    """Provide a ProfileProjectRepository instance bound to request session."""
    return SQLAlchemyProfileProjectRepository(session)


ProfileProjectRepositoryDep = Annotated[
    ProfileProjectRepository, Depends(get_profile_project_repository)
]


def get_profile_project_service(
    base_profile_repo: BaseProfileRepositoryDep,
    project_repo: ProfileProjectRepositoryDep,
) -> ProfileProjectService:
    """Provide a ProfileProjectService instance bound to the request."""
    return ProfileProjectService(
        base_profile_repo=base_profile_repo,
        project_repo=project_repo,
    )


ProfileProjectServiceDep = Annotated[
    ProfileProjectService, Depends(get_profile_project_service)
]


# ============================================================================
# Search Profile Dependencies
# ============================================================================


def get_search_profile_service(
    base_profile_repo: BaseProfileRepositoryDep,
    search_profile_repo: SearchProfileRepositoryDep,
) -> SearchProfileService:
    """Provide a SearchProfileService instance bound to the request."""
    return SearchProfileService(
        base_profile_repo=base_profile_repo,
        search_profile_repo=search_profile_repo,
    )


SearchProfileServiceDep = Annotated[
    SearchProfileService, Depends(get_search_profile_service)
]
