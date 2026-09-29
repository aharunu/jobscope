"""FastAPI dependencies for the matching subsystem."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.matching.services import MatchingService
from backend.domain.matching.repositories import MatchResultRepository
from backend.domain.profile.repositories import BaseProfileRepository
from backend.domain.search_profile.repositories import SearchProfileRepository
from backend.infrastructure.database.repositories.base_profile_repository import (
    SQLAlchemyBaseProfileRepository,
)
from backend.infrastructure.database.repositories.matching_repository import (
    SQLAlchemyMatchResultRepository,
)
from backend.infrastructure.database.repositories.search_profile_repository import (
    SQLAlchemySearchProfileRepository,
)
from backend.interfaces.api.dependencies.database import DbSession
from backend.interfaces.api.dependencies.job_processing import (
    JobRepositoryDep,
)


def get_match_result_repository(session: DbSession) -> MatchResultRepository:
    """Provide a MatchResultRepository instance bound to request session."""
    return SQLAlchemyMatchResultRepository(session)


MatchResultRepositoryDep = Annotated[
    MatchResultRepository, Depends(get_match_result_repository)
]


def get_base_profile_repository(session: DbSession) -> BaseProfileRepository:
    """Provide a BaseProfileRepository instance bound to request session."""
    return SQLAlchemyBaseProfileRepository(session)


BaseProfileRepositoryDep = Annotated[
    BaseProfileRepository, Depends(get_base_profile_repository)
]


def get_search_profile_repository(
    session: DbSession,
) -> SearchProfileRepository:
    """Provide a SearchProfileRepository instance bound to request session."""
    return SQLAlchemySearchProfileRepository(session)


SearchProfileRepositoryDep = Annotated[
    SearchProfileRepository, Depends(get_search_profile_repository)
]


def get_matching_service(
    job_repo: JobRepositoryDep,
    base_profile_repo: BaseProfileRepositoryDep,
    search_profile_repo: SearchProfileRepositoryDep,
    match_result_repo: MatchResultRepositoryDep,
) -> MatchingService:
    """Provide a configured MatchingService instance."""
    return MatchingService(
        job_repo=job_repo,
        base_profile_repo=base_profile_repo,
        search_profile_repo=search_profile_repo,
        match_result_repo=match_result_repo,
    )


MatchingServiceDep = Annotated[MatchingService, Depends(get_matching_service)]
