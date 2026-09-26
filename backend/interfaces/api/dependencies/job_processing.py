"""FastAPI dependencies for the Job Processing & Ingestion subsystem."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.domain.crawl.repositories import CrawlRunRepository
from backend.domain.job.repositories import JobRepository, RawJobRepository
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)
from backend.interfaces.api.dependencies.database import DbSession


def get_job_repository(session: DbSession) -> JobRepository:
    """Provide a JobRepository instance bound to the request's database session."""
    return SQLAlchemyJobRepository(session)


JobRepositoryDep = Annotated[JobRepository, Depends(get_job_repository)]


def get_raw_job_repository(session: DbSession) -> RawJobRepository:
    """Provide a RawJobRepository instance bound to the request's database session."""
    return SQLAlchemyRawJobRepository(session)


RawJobRepositoryDep = Annotated[RawJobRepository, Depends(get_raw_job_repository)]


def get_crawl_run_repository(session: DbSession) -> CrawlRunRepository:
    """Provide a CrawlRunRepository instance bound to the request's database session."""
    return SQLAlchemyCrawlRunRepository(session)


CrawlRunRepositoryDep = Annotated[CrawlRunRepository, Depends(get_crawl_run_repository)]


def get_job_normalizer() -> JobNormalizer:
    """Provide a stateless JobNormalizer instance."""
    return JobNormalizer()


JobNormalizerDep = Annotated[JobNormalizer, Depends(get_job_normalizer)]


def get_job_ingestion_service(
    job_repo: JobRepositoryDep,
    raw_job_repo: RawJobRepositoryDep,
    crawl_run_repo: CrawlRunRepositoryDep,
    normalizer: JobNormalizerDep,
) -> JobIngestionService:
    """Provide a JobIngestionService injected with request-scoped repositories."""
    return JobIngestionService(
        job_repo=job_repo,
        raw_job_repo=raw_job_repo,
        crawl_run_repo=crawl_run_repo,
        normalizer=normalizer,
    )


JobIngestionServiceDep = Annotated[
    JobIngestionService, Depends(get_job_ingestion_service)
]

__all__ = [
    "CrawlRunRepositoryDep",
    "JobIngestionServiceDep",
    "JobNormalizerDep",
    "JobRepositoryDep",
    "RawJobRepositoryDep",
    "get_crawl_run_repository",
    "get_job_ingestion_service",
    "get_job_normalizer",
    "get_job_repository",
    "get_raw_job_repository",
]
