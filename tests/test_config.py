"""Configuration and settings tests."""

from backend.infrastructure.config.settings import Settings, get_settings


def test_default_settings_instantiation() -> None:
    """Verify that Settings can be instantiated with default values."""
    settings = Settings()
    assert settings.app_name == "JobScope"
    assert settings.app_version == "0.1.0"
    assert settings.environment in ("development", "test", "production")
    assert "postgresql" in settings.database_url


def test_settings_environment_override(monkeypatch) -> None:
    """Verify that environment variables take precedence over defaults."""
    monkeypatch.setenv("APP_NAME", "JobScope-Custom")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("DEBUG", "false")

    settings = Settings()
    assert settings.app_name == "JobScope-Custom"
    assert settings.port == 9000
    assert settings.debug is False


def test_get_settings_caching() -> None:
    """Verify that get_settings returns a cached instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
