"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.database.engine import dispose_engine, get_engine
from backend.infrastructure.logging.logger import setup_logging
from backend.interfaces.api.errors import register_exception_handlers
from backend.interfaces.api.routes.health import router as health_router
from backend.interfaces.api.routes.sources import router as sources_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager handling startup and shutdown events."""
    settings = getattr(app.state, "settings", None) or get_settings()
    setup_logging(log_level=settings.log_level)

    # Startup: ensure database engine is initialized
    if getattr(app.state, "db_engine", None) is None:
        app.state.db_engine = get_engine()

    yield

    # Shutdown: cleanly dispose of the database engine
    engine = getattr(app.state, "db_engine", None)
    if engine is not None:
        await engine.dispose()
        await dispose_engine()
        app.state.db_engine = None


def create_app(
    settings: Settings | None = None,
    engine: AsyncEngine | None = None,
) -> FastAPI:
    """Application factory for creating and configuring the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        description="Personal Job Intelligence & Decision Support System API",
        lifespan=lifespan,
    )

    app.state.settings = settings
    if engine is not None:
        app.state.db_engine = engine

    # Health and readiness check endpoints mounted at root and API prefix
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api")

    # Sources registry endpoint
    app.include_router(sources_router, prefix="/api")

    # Centralized exception handlers for safe, standardized error responses
    register_exception_handlers(app)

    return app


app = create_app()
