"""Unit tests for JobQueryService application logic and architecture boundaries."""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backend.application.job_processing.dtos import (
    JobDetailDTO,
    JobFilterDTO,
    JobSummaryDTO,
)
from backend.application.job_processing.query_service import JobQueryService
from backend.domain.job.entities import Job
from backend.domain.job.enums import JobStatus
from backend.domain.job.repositories import JobRepository


def _make_dummy_job(
    job_id: uuid.UUID | None = None,
    source_id: uuid.UUID | None = None,
    source_name: str | None = "Acme Lever",
    ats_type: str | None = "lever",
    source_url: str | None = "https://jobs.lever.co/acme",
) -> Job:
    return Job(
        id=job_id or uuid.uuid4(),
        source_id=source_id or uuid.uuid4(),
        canonical_url="https://jobs.lever.co/acme/job-123",
        company="Acme Corp",
        title="Lead Platform Architect",
        description="Lead platform architecture.",
        responsibilities="Guide team.",
        location="Berlin, Germany",
        work_mode="Hybrid",
        employment_type="Full-time",
        salary="EUR 100k-120k",
        published_at=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
        first_seen_at=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
        last_seen_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        closed_at=None,
        status=JobStatus.ACTIVE,
        content_hash="hash_platform_123",
        created_at=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
        updated_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
        source_name=source_name,
        ats_type=ats_type,
        source_url=source_url,
    )


def test_job_query_service_clean_architecture_boundary() -> None:
    """Verify JobQueryService has zero imports from infrastructure or ORM."""
    mod = sys.modules.get("backend.application.job_processing.query_service")
    assert mod is not None, "query_service module not loaded"
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"JobQueryService imports from SQLAlchemy: {attr_name}"
            )
            assert "infrastructure" not in attr_val.__module__.lower(), (
                f"JobQueryService imports from infrastructure: {attr_name}"
            )


@pytest.mark.asyncio
async def test_list_jobs_success_and_dto_mapping() -> None:
    """Verify list_jobs queries repository and maps domain Job to JobSummaryDTO."""
    mock_repo = AsyncMock(spec=JobRepository)
    dummy_job = _make_dummy_job()
    mock_repo.list_jobs.return_value = [dummy_job]
    mock_repo.count_jobs.return_value = 1

    service = JobQueryService(job_repo=mock_repo)
    filter_dto = JobFilterDTO(limit=20, offset=0, company=" Acme Corp ")

    items, total = await service.list_jobs(filter_dto)

    assert total == 1
    assert len(items) == 1
    dto = items[0]
    assert isinstance(dto, JobSummaryDTO)
    assert dto.id == dummy_job.id
    assert dto.company == "Acme Corp"
    assert dto.title == "Lead Platform Architect"
    assert dto.source_name == "Acme Lever"
    assert dto.ats_type == "lever"
    assert dto.source_url == "https://jobs.lever.co/acme"

    # Verify whitespace normalization
    mock_repo.list_jobs.assert_awaited_once()
    _, kwargs = mock_repo.list_jobs.call_args
    assert kwargs["company"] == "Acme Corp"
    assert kwargs["limit"] == 20
    assert kwargs["offset"] == 0


@pytest.mark.asyncio
async def test_list_jobs_defensive_fallbacks() -> None:
    """Verify list_jobs applies defensive fallback defaults when source is None."""
    mock_repo = AsyncMock(spec=JobRepository)
    dummy_job = _make_dummy_job(source_name=None, ats_type=None, source_url=None)
    mock_repo.list_jobs.return_value = [dummy_job]
    mock_repo.count_jobs.return_value = 1

    service = JobQueryService(job_repo=mock_repo)
    filter_dto = JobFilterDTO()

    items, total = await service.list_jobs(filter_dto)
    assert len(items) == 1
    dto = items[0]
    assert dto.source_name == "Unknown"
    assert dto.ats_type == "unknown"
    assert dto.source_url == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_limit, invalid_offset",
    [
        (0, 0),
        (101, 0),
        (-5, 0),
        (50, -1),
    ],
)
async def test_list_jobs_pagination_validation(
    invalid_limit: int, invalid_offset: int
) -> None:
    """Verify list_jobs raises ValueError for out-of-bounds pagination."""
    mock_repo = AsyncMock(spec=JobRepository)
    service = JobQueryService(job_repo=mock_repo)
    filter_dto = JobFilterDTO(limit=invalid_limit, offset=invalid_offset)

    with pytest.raises(ValueError):
        await service.list_jobs(filter_dto)

    mock_repo.list_jobs.assert_not_called()
    mock_repo.count_jobs.assert_not_called()


@pytest.mark.asyncio
async def test_get_job_found_and_detail_dto_mapping() -> None:
    """Verify get_job retrieves domain Job and returns JobDetailDTO."""
    mock_repo = AsyncMock(spec=JobRepository)
    job_id = uuid.uuid4()
    dummy_job = _make_dummy_job(job_id=job_id)
    mock_repo.get_job_detail.return_value = dummy_job

    service = JobQueryService(job_repo=mock_repo)
    result = await service.get_job(job_id)

    assert result is not None
    assert isinstance(result, JobDetailDTO)
    assert result.id == job_id
    assert result.description == "Lead platform architecture."
    assert result.responsibilities == "Guide team."
    assert result.source_name == "Acme Lever"
    assert result.ats_type == "lever"
    assert result.source_url == "https://jobs.lever.co/acme"
    assert result.requirements == []
    mock_repo.get_job_detail.assert_awaited_once_with(job_id)


@pytest.mark.asyncio
async def test_get_job_not_found() -> None:
    """Verify get_job returns None when job is not found."""
    mock_repo = AsyncMock(spec=JobRepository)
    mock_repo.get_job_detail.return_value = None

    service = JobQueryService(job_repo=mock_repo)
    result = await service.get_job(uuid.uuid4())

    assert result is None
