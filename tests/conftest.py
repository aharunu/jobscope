"""Pytest fixtures and test configuration."""

import pytest
from fastapi.testclient import TestClient

from backend.infrastructure.config.settings import Settings, get_settings
from backend.interfaces.api.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Fixture providing isolated settings for test execution."""
    return Settings(
        app_name="JobScope-Test",
        app_version="0.1.0-test",
        environment="test",
        debug=True,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
        log_level="DEBUG",
    )


@pytest.fixture
def app(test_settings: Settings):
    """Fixture providing a configured FastAPI app with test settings."""
    application = create_app(settings=test_settings)
    application.dependency_overrides[get_settings] = lambda: test_settings
    yield application
    application.dependency_overrides.clear()


@pytest.fixture
def client(app) -> TestClient:
    """Fixture providing a synchronous TestClient for endpoint testing."""
    return TestClient(app)
