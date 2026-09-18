"""Tests for database base, session factory, health, and Alembic."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic.config import Config
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.config.settings import Settings
from backend.infrastructure.database import (
    Base,
    BaseModel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    check_database_health,
    create_database_engine,
    create_session_factory,
    dispose_engine,
    get_db_context,
    get_db_session,
    get_engine,
    get_session_factory,
)
from backend.infrastructure.database.migrations import env as alembic_env


class ConcreteSampleModel(BaseModel):
    """Concrete model subclassing BaseModel for schema and metadata tests."""

    __tablename__ = "test_sample_table"

    title: Mapped[str] = mapped_column(String(100), nullable=False)


class ConcreteCustomModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Concrete model combining Base and mixins directly."""

    __tablename__ = "test_custom_table"

    name: Mapped[str] = mapped_column(String(50), nullable=False)


def test_base_and_mixins_structure() -> None:
    """Verify that BaseModel and mixins define the required columns and metadata."""
    assert "test_sample_table" in Base.metadata.tables
    assert "test_custom_table" in Base.metadata.tables

    sample_table = Base.metadata.tables["test_sample_table"]

    # Check ID primary key column
    assert "id" in sample_table.columns
    id_col = sample_table.columns["id"]
    assert id_col.primary_key is True
    assert isinstance(id_col.type, UUID)

    # Check timestamp columns
    assert "created_at" in sample_table.columns
    created_col = sample_table.columns["created_at"]
    assert isinstance(created_col.type, DateTime)
    assert created_col.type.timezone is True
    assert created_col.nullable is False
    assert created_col.server_default is not None

    assert "updated_at" in sample_table.columns
    updated_col = sample_table.columns["updated_at"]
    assert isinstance(updated_col.type, DateTime)
    assert updated_col.type.timezone is True
    assert updated_col.nullable is False
    assert updated_col.server_default is not None


def test_model_instantiation() -> None:
    """Verify default values during model Python instantiation."""
    instance = ConcreteSampleModel(title="Sample Job")
    assert instance.title == "Sample Job"
    assert isinstance(instance.id, uuid.UUID)


def test_database_engine_creation(test_settings: Settings) -> None:
    """Verify AsyncEngine creation with application settings."""
    engine = create_database_engine(test_settings)
    assert isinstance(engine, AsyncEngine)
    assert "asyncpg" in str(engine.url)


def test_get_and_dispose_engine() -> None:
    """Verify singleton engine retrieval and lifecycle disposal."""
    engine1 = get_engine()
    assert isinstance(engine1, AsyncEngine)
    engine2 = get_engine()
    assert engine1 is engine2


@pytest.mark.asyncio
async def test_dispose_engine_cleans_up() -> None:
    """Verify engine disposal resets the singleton instance."""
    engine = get_engine()
    assert engine is not None
    await dispose_engine()
    new_engine = get_engine()
    assert new_engine is not engine
    await dispose_engine()


def test_session_factory_creation() -> None:
    """Verify sessionmaker creates AsyncSession instances bound to an engine."""
    factory = create_session_factory()
    assert isinstance(factory, async_sessionmaker)
    assert issubclass(factory.class_, AsyncSession)


def test_get_session_factory_singleton() -> None:
    """Verify session factory singleton retrieval."""
    f1 = get_session_factory()
    f2 = get_session_factory()
    assert f1 is f2


@pytest.mark.asyncio
async def test_get_db_session_dependency() -> None:
    """Verify get_db_session dependency generator commits and closes session."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None

    import backend.infrastructure.database.session as session_module

    original_factory = session_module._session_factory
    session_module._session_factory = mock_factory

    try:
        gen = get_db_session()
        yielded_session = await anext(gen)
        assert yielded_session is mock_session
        with pytest.raises(StopAsyncIteration):
            await anext(gen)

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()
    finally:
        session_module._session_factory = original_factory


@pytest.mark.asyncio
async def test_get_db_session_rollback_on_error() -> None:
    """Verify get_db_session rolls back when an unhandled exception occurs."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session
    mock_factory.return_value.__aexit__.return_value = None

    import backend.infrastructure.database.session as session_module

    original_factory = session_module._session_factory
    session_module._session_factory = mock_factory

    try:
        gen = get_db_session()
        await anext(gen)
        with pytest.raises(RuntimeError, match="Simulated failure"):
            await gen.athrow(RuntimeError("Simulated failure"))

        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()
    finally:
        session_module._session_factory = original_factory


@pytest.mark.asyncio
async def test_get_db_context() -> None:
    """Verify standalone get_db_context context manager commits and closes."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_engine = MagicMock(spec=AsyncEngine)

    import backend.infrastructure.database.session as session_module

    original_factory = session_module._session_factory

    def mock_create_factory(engine=None):
        m = MagicMock()
        m.return_value.__aenter__.return_value = mock_session
        m.return_value.__aexit__.return_value = None
        return m

    orig_create = session_module.create_session_factory
    session_module.create_session_factory = mock_create_factory

    try:
        async with get_db_context(mock_engine) as session:
            assert session is mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.close.assert_awaited_once()
    finally:
        session_module._session_factory = original_factory
        session_module.create_session_factory = orig_create


@pytest.mark.asyncio
async def test_check_database_health_success() -> None:
    """Verify check_database_health reports healthy when SELECT 1 succeeds."""
    mock_conn = AsyncMock()
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    result = await check_database_health(mock_engine)
    assert result["status"] == "healthy"
    assert result["database"] == "reachable"
    mock_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_database_health_failure() -> None:
    """Verify check_database_health catches error and returns unhealthy status."""
    mock_engine = MagicMock(spec=AsyncEngine)
    mock_engine.connect.side_effect = ConnectionRefusedError("Database unreachable")

    result = await check_database_health(mock_engine)
    assert result["status"] == "unhealthy"
    assert result["database"] == "unreachable"
    assert "Database unreachable" in result["error"]


def test_alembic_configuration_and_importability() -> None:
    """Verify Alembic configuration file and metadata importability."""
    alembic_cfg = Config("alembic.ini")
    script_loc = alembic_cfg.get_main_option("script_location")
    assert script_loc == "backend/infrastructure/database/migrations"

    # Verify target_metadata is imported and matches Base.metadata
    assert alembic_env.target_metadata is Base.metadata
