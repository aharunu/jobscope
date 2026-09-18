"""SQLAlchemy async session management and FastAPI dependency injection."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from backend.infrastructure.database.engine import get_engine

_session_factory: async_sessionmaker[AsyncSession] | None = None


def create_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Create an async sessionmaker bound to the given engine."""
    if engine is None:
        engine = get_engine()

    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Retrieve or initialize the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for yielding transactional async sessions.

    Automatically commits on normal completion, rolls back on exceptions,
    and closes the session upon request termination.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context(
    engine: AsyncEngine | None = None,
) -> AsyncIterator[AsyncSession]:
    """Async context manager for standalone operations, CLI commands, or scripts."""
    factory = create_session_factory(engine) if engine else get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
