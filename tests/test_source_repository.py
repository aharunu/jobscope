"""Unit tests for SourceRepository protocol and SQLAlchemySourceRepository."""

from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.source import Source, SourceRepository
from backend.infrastructure.database.models.source import SourceModel
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)


def test_domain_repository_independence() -> None:
    """Verify domain repository protocol has zero SQLAlchemy or Alembic imports."""
    mod = sys.modules.get("backend.domain.source.repositories")
    assert mod is not None, "backend.domain.source.repositories module not loaded"
    for attr_name, attr_val in mod.__dict__.items():
        if hasattr(attr_val, "__module__") and attr_val.__module__:
            assert "sqlalchemy" not in attr_val.__module__.lower(), (
                f"Domain repository imports from SQLAlchemy: {attr_name}"
            )
            assert "alembic" not in attr_val.__module__.lower(), (
                f"Domain repository imports from Alembic: {attr_name}"
            )


def test_source_repository_protocol_conformance() -> None:
    """Verify SQLAlchemySourceRepository satisfies the SourceRepository protocol."""
    mock_session = AsyncMock(spec=AsyncSession)
    repo = SQLAlchemySourceRepository(mock_session)
    assert isinstance(repo, SourceRepository)


def test_absence_of_delete_method() -> None:
    """Verify that SourceRepository and its implementation do not define delete()."""
    assert not hasattr(SourceRepository, "delete"), (
        "SourceRepository protocol must not have a delete method"
    )
    assert not hasattr(SQLAlchemySourceRepository, "delete"), (
        "SQLAlchemySourceRepository must not have a delete method"
    )


@pytest.mark.asyncio
async def test_repository_get_by_id_found() -> None:
    """Verify get_by_id returns domain Source when found."""
    mock_session = AsyncMock(spec=AsyncSession)
    test_id = uuid.uuid4()
    orm_model = SourceModel(
        id=test_id,
        name="Trendyol Greenhouse",
        company="Trendyol",
        url="https://boards.greenhouse.io/trendyol",
        country="TR",
        ats_type="greenhouse",
        active=True,
    )
    mock_session.get.return_value = orm_model

    repo = SQLAlchemySourceRepository(mock_session)
    result = await repo.get_by_id(test_id)

    assert result is not None
    assert isinstance(result, Source)
    assert result.id == test_id
    assert result.name == "Trendyol Greenhouse"
    assert result.ats_type == "greenhouse"
    mock_session.get.assert_awaited_once_with(SourceModel, test_id)


@pytest.mark.asyncio
async def test_repository_get_by_id_not_found() -> None:
    """Verify get_by_id returns None when source is not found."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.get.return_value = None

    repo = SQLAlchemySourceRepository(mock_session)
    result = await repo.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_repository_get_by_url_found() -> None:
    """Verify get_by_url queries by URL and returns domain Source."""
    mock_session = AsyncMock(spec=AsyncSession)
    test_url = "https://jobs.lever.co/getir"
    orm_model = SourceModel(
        name="Getir Lever",
        url=test_url,
        ats_type="lever",
        company="Getir",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = orm_model
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemySourceRepository(mock_session)
    result = await repo.get_by_url(test_url)

    assert result is not None
    assert result.url == test_url
    assert result.name == "Getir Lever"
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_list_all_with_filters() -> None:
    """Verify list_all applies active_only, ats_type, limit, and offset."""
    mock_session = AsyncMock(spec=AsyncSession)
    orm_sources = [
        SourceModel(
            name="Source A",
            url="https://a.com",
            ats_type="greenhouse",
            active=True,
        ),
        SourceModel(
            name="Source B",
            url="https://b.com",
            ats_type="greenhouse",
            active=True,
        ),
    ]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = orm_sources
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemySourceRepository(mock_session)
    results = await repo.list_all(
        active_only=True,
        ats_type="greenhouse",
        limit=10,
        offset=0,
    )

    assert len(results) == 2
    assert all(isinstance(s, Source) for s in results)
    assert results[0].name == "Source A"
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_save() -> None:
    """Verify save merges model, flushes session, and returns domain entity."""
    mock_session = AsyncMock(spec=AsyncSession)
    source = Source(
        name="New Source",
        url="https://newsource.com",
        ats_type="ashby",
    )
    orm_merged = SourceModel.from_domain(source)
    mock_session.merge.return_value = orm_merged

    repo = SQLAlchemySourceRepository(mock_session)
    saved = await repo.save(source)

    assert isinstance(saved, Source)
    assert saved.name == "New Source"
    mock_session.merge.assert_awaited_once()
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_save_bulk() -> None:
    """Verify save_bulk persists multiple sources and flushes."""
    mock_session = AsyncMock(spec=AsyncSession)
    sources = [
        Source(name="S1", url="https://s1.com", ats_type="lever"),
        Source(name="S2", url="https://s2.com", ats_type="ashby"),
    ]
    mock_session.merge.side_effect = lambda m: m

    repo = SQLAlchemySourceRepository(mock_session)
    saved_list = await repo.save_bulk(sources)

    assert len(saved_list) == 2
    assert mock_session.merge.await_count == 2
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_repository_count() -> None:
    """Verify count executes query and returns int."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    mock_session.execute.return_value = mock_result

    repo = SQLAlchemySourceRepository(mock_session)
    total = await repo.count(active_only=True, ats_type="workday")

    assert total == 42
    mock_session.execute.assert_awaited_once()
