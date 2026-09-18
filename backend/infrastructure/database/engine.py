"""Database engine creation and lifecycle management."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.infrastructure.config.settings import Settings, get_settings

_engine: AsyncEngine | None = None


def create_database_engine(settings: Settings | None = None) -> AsyncEngine:
    """Instantiate a new AsyncEngine configured with application settings."""
    if settings is None:
        settings = get_settings()

    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )


def get_engine() -> AsyncEngine:
    """Retrieve or initialize the singleton AsyncEngine instance."""
    global _engine
    if _engine is None:
        _engine = create_database_engine()
    return _engine


async def dispose_engine() -> None:
    """Gracefully dispose of the engine connection pool."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
