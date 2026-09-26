"""Unit tests for JobRequirementRepository persistence and idempotency (Items 14-18)."""

from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.job.entities import JobRequirement
from backend.domain.job.enums import RequirementLevel, RequirementType
from backend.domain.job.repositories import JobRequirementRepository
from backend.infrastructure.database.models.job import JobRequirementModel
from backend.infrastructure.database.repositories.job_requirement_repository import (
    SQLAlchemyJobRequirementRepository,
)


def _make_req(
    job_id: uuid.UUID,
    skill: str = "Python",
    req_type: RequirementType = RequirementType.SKILL,
    level: RequirementLevel = RequirementLevel.REQUIRED,
) -> JobRequirement:
    return JobRequirement(
        id=uuid.uuid4(),
        job_id=job_id,
        type=req_type,
        description=f"Must know {skill}",
        normalized_skill=skill,
        required_level=level,
        importance="HIGH",
        criticality="NORMAL",
        evidence=f"Demonstrated {skill} expertise",
    )


def test_domain_requirement_repository_independence() -> None:
    """Verify domain repository protocols have zero SQLAlchemy or Alembic imports."""
    mod = sys.modules.get("backend.domain.job.repositories")
    assert mod is not None
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"Domain repository imports from SQLAlchemy: {attr_name}"
            )
            assert "alembic" not in attr_val.__module__.lower(), (
                f"Domain repository imports from Alembic: {attr_name}"
            )


def test_job_requirement_repository_protocol_conformance() -> None:
    """Verify SQLAlchemyJobRequirementRepository satisfies JobRequirementRepository."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRequirementRepository(mock_session)
    assert isinstance(repo, JobRequirementRepository)


# 14. Create requirements for a new Job
@pytest.mark.asyncio
async def test_create_requirements_for_new_job() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRequirementRepository(mock_session)
    job_id = uuid.uuid4()

    req1 = _make_req(job_id, "Python")
    req2 = _make_req(job_id, "Docker")

    saved = await repo.save_requirements(job_id, [req1, req2])

    assert len(saved) == 2
    assert {r.normalized_skill for r in saved} == {"Python", "Docker"}
    assert mock_session.add.call_count == 2
    mock_session.flush.assert_awaited_once()


# 15. Reprocess same Job without duplicates (atomic replacement)
@pytest.mark.asyncio
async def test_reprocess_same_job_without_duplicates() -> None:
    """Reprocessing the same job replaces previous requirements idempotently."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRequirementRepository(mock_session)
    job_id = uuid.uuid4()

    reqs = [_make_req(job_id, "Python"), _make_req(job_id, "FastAPI")]

    # First save
    saved1 = await repo.save_requirements(job_id, reqs)
    assert len(saved1) == 2

    # Second save (reprocess)
    saved2 = await repo.save_requirements(job_id, reqs)
    assert len(saved2) == 2

    # Verifies delete was executed before additions
    assert mock_session.execute.call_count == 2
    assert mock_session.add.call_count == 4
    assert mock_session.flush.await_count == 2


# 16. Changed requirements reconcile correctly
@pytest.mark.asyncio
async def test_changed_requirements_reconcile_correctly() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRequirementRepository(mock_session)
    job_id = uuid.uuid4()

    initial_reqs = [_make_req(job_id, "Python")]
    await repo.save_requirements(job_id, initial_reqs)

    # Updated job now has PostgreSQL instead of Python
    updated_reqs = [_make_req(job_id, "PostgreSQL"), _make_req(job_id, "AWS")]
    saved_updated = await repo.save_requirements(job_id, updated_reqs)

    assert len(saved_updated) == 2
    assert {r.normalized_skill for r in saved_updated} == {"PostgreSQL", "AWS"}


# 17. Empty extraction produces zero requirements safely
@pytest.mark.asyncio
async def test_empty_extraction_produces_zero_requirements_safely() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemyJobRequirementRepository(mock_session)
    job_id = uuid.uuid4()

    saved = await repo.save_requirements(job_id, [])

    assert saved == []
    mock_session.execute.assert_awaited_once()
    mock_session.add.assert_not_called()
    mock_session.flush.assert_awaited_once()


# 18. Repository does not commit transactions
@pytest.mark.asyncio
async def test_repository_does_not_commit_transactions() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.rowcount = 1
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRequirementRepository(mock_session)
    job_id = uuid.uuid4()

    await repo.save_requirements(job_id, [_make_req(job_id, "Python")])
    await repo.get_by_job_id(job_id)
    await repo.delete_by_job_id(job_id)

    # Invariant: repository must never call session.commit()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_by_job_id_returns_domain_entities() -> None:
    mock_session = AsyncMock(spec=AsyncSession)
    job_id = uuid.uuid4()

    orm_req = JobRequirementModel(
        id=uuid.uuid4(),
        job_id=job_id,
        type=RequirementType.SKILL,
        description="Experience with Python",
        normalized_skill="Python",
        required_level=RequirementLevel.REQUIRED,
        importance="HIGH",
        criticality="NORMAL",
        evidence="Clean code",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [orm_req]
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemyJobRequirementRepository(mock_session)
    results = await repo.get_by_job_id(job_id)

    assert len(results) == 1
    assert isinstance(results[0], JobRequirement)
    assert results[0].normalized_skill == "Python"
