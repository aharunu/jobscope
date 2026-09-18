"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.infrastructure.config.settings import Settings, get_settings
from backend.infrastructure.logging.logger import setup_logging
from backend.interfaces.api.routes.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager handling startup and shutdown events."""
    settings = get_settings()
    setup_logging(log_level=settings.log_level)
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
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

    # Health check endpoint mounted at root and API prefix
    app.include_router(health_router)
    app.include_router(health_router, prefix="/api")

    return app


app = create_app()
