"""Integration tests for application lifecycle and readiness checks."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.infrastructure.config.settings import Settings
from backend.interfaces.api.dependencies.database import DbSession, get_db_session
from backend.interfaces.api.main import create_app, lifespan
from backend.interfaces.api.routes.health import get_db_health_checker


@pytest.mark.asyncio
async def test_application_lifespan_initialization_and_disposal() -> None:
    """Verify that lifespan initializes db_engine and disposes on shutdown."""
    mock_engine = AsyncMock(spec=AsyncEngine)
    test_app = create_app(engine=mock_engine)

    async with lifespan(test_app):
        assert test_app.state.db_engine is mock_engine

    # Ensure engine disposal was called on exit
    mock_engine.dispose.assert_awaited_once()


def test_database_readiness_success(client: TestClient, app: FastAPI) -> None:
    """Verify GET /health/ready returns 200 when database connectivity is healthy."""

    async def mock_checker():
        return {"status": "healthy", "database": "reachable"}

    app.dependency_overrides[get_db_health_checker] = lambda: mock_checker

    response = client.get("/health/ready")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"


def test_database_readiness_failure_returns_503(
    client: TestClient, app: FastAPI
) -> None:
    """Verify GET /health/ready returns 503 without leaking credentials on failure."""

    async def mock_checker():
        return {
            "status": "unhealthy",
            "database": "unreachable",
            "error": "FATAL: password authentication failed for user 'secret_user'",
        }

    app.dependency_overrides[get_db_health_checker] = lambda: mock_checker

    response = client.get("/health/ready")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database"] == "disconnected"
    # Ensure raw error / credentials are not leaked to API response
    assert "password" not in str(data)
    assert "secret_user" not in str(data)


def test_liveness_remains_healthy_when_database_unreachable(
    client: TestClient, app: FastAPI
) -> None:
    """Verify GET /health process liveness probe is decoupled from database status."""

    async def mock_checker():
        return {"status": "unhealthy", "database": "unreachable", "error": "Timeout"}

    app.dependency_overrides[get_db_health_checker] = lambda: mock_checker

    # /health must remain 200 OK even when database is down
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_dependency_wiring_with_db_session(app: FastAPI, client: TestClient) -> None:
    """Verify DbSession dependency is correctly injectable into FastAPI routes."""
    mock_session = AsyncMock(spec=AsyncSession)

    # Temporary test route demonstrating DbSession injection
    @app.get("/test-db-dependency")
    async def sample_db_route(session: DbSession):
        return {"session_available": session is not None}

    async def mock_session_gen():
        yield mock_session

    app.dependency_overrides[get_db_session] = mock_session_gen

    response = client.get("/test-db-dependency")
    assert response.status_code == 200
    assert response.json() == {"session_available": True}


def test_database_url_validation() -> None:
    """Verify database_url validation rejects non-PostgreSQL schemes."""
    with pytest.raises(ValueError, match="DATABASE_URL must start with"):
        Settings(database_url="mysql://user:pass@localhost/db")
