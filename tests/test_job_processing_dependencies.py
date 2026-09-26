"""Unit tests for Job Processing FastAPI dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.job_processing.extraction import (
    RequirementExtractionService,
)
from backend.application.job_processing.lifecycle import JobLifecycleService
from backend.application.job_processing.normalizer import JobNormalizer
from backend.application.job_processing.services import JobIngestionService
from backend.infrastructure.database.repositories.crawl_run_repository import (
    SQLAlchemyCrawlRunRepository,
)
from backend.infrastructure.database.repositories.job_repository import (
    SQLAlchemyJobRepository,
    SQLAlchemyRawJobRepository,
)
from backend.infrastructure.database.repositories.job_requirement_repository import (
    SQLAlchemyJobRequirementRepository,
)
from backend.infrastructure.extraction.deterministic_extractor import (
    DeterministicRequirementExtractor,
)
from backend.interfaces.api.dependencies.job_processing import (
    get_crawl_run_repository,
    get_job_ingestion_service,
    get_job_lifecycle_service,
    get_job_normalizer,
    get_job_repository,
    get_job_requirement_repository,
    get_raw_job_repository,
    get_requirement_extraction_service,
    get_requirement_extractor,
)


def test_dependency_providers() -> None:
    """Verify that dependency provider functions instantiate components with session."""
    mock_session = AsyncMock(spec=AsyncSession)

    job_repo = get_job_repository(mock_session)
    assert isinstance(job_repo, SQLAlchemyJobRepository)
    assert job_repo.session == mock_session

    raw_repo = get_raw_job_repository(mock_session)
    assert isinstance(raw_repo, SQLAlchemyRawJobRepository)
    assert raw_repo.session == mock_session

    crawl_repo = get_crawl_run_repository(mock_session)
    assert isinstance(crawl_repo, SQLAlchemyCrawlRunRepository)
    assert crawl_repo.session == mock_session

    normalizer = get_job_normalizer()
    assert isinstance(normalizer, JobNormalizer)

    lifecycle_service = get_job_lifecycle_service(
        job_repo=job_repo,
        crawl_run_repo=crawl_repo,
    )
    assert isinstance(lifecycle_service, JobLifecycleService)

    req_repo = get_job_requirement_repository(mock_session)
    assert isinstance(req_repo, SQLAlchemyJobRequirementRepository)
    assert req_repo.session == mock_session

    extractor = get_requirement_extractor()
    assert isinstance(extractor, DeterministicRequirementExtractor)

    req_service = get_requirement_extraction_service(
        requirement_repo=req_repo,
        extractor=extractor,
    )
    assert isinstance(req_service, RequirementExtractionService)

    service = get_job_ingestion_service(
        job_repo=job_repo,
        raw_job_repo=raw_repo,
        crawl_run_repo=crawl_repo,
        normalizer=normalizer,
        job_requirement_repo=req_repo,
        requirement_service=req_service,
        lifecycle_service=lifecycle_service,
    )
    assert isinstance(service, JobIngestionService)
    assert service.job_repo == job_repo
    assert service.raw_job_repo == raw_repo
    assert service.crawl_run_repo == crawl_repo
    assert service.normalizer == normalizer
    assert service.job_requirement_repo == req_repo
    assert service.requirement_service == req_service
    assert service.lifecycle_service == lifecycle_service
