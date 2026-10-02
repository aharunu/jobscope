"""Typed application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """JobScope application configuration loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    app_name: str = Field(default="JobScope", description="Application name")
    app_version: str = Field(
        default="0.1.0", description="Semantic application version"
    )
    environment: str = Field(
        default="development",
        description="Runtime environment (development, test, production)",
    )
    debug: bool = Field(default=True, description="Enable debug mode")

    # Server Configuration
    host: str = Field(default="127.0.0.1", description="Server host bind address")
    port: int = Field(default=8000, description="Server port")

    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://jobscope:CHANGE_ME@localhost:5432/jobscope",
        description="PostgreSQL connection URL with async driver",
    )

    # Logging Configuration
    ai_enabled: bool = False
    openai_api_key: SecretStr = Field(default=SecretStr(""), repr=False)
    ai_model: str = Field(
        default="gpt-4.1-mini-2025-04-14", min_length=1, max_length=100
    )
    ai_timeout_seconds: float = Field(default=30, ge=1, le=120)

    log_level: str = Field(default="INFO", description="Log verbosity level")
    log_format: str = Field(
        default="console",
        description="Log output format ('console' or 'json')",
    )

    # Source Catalog Configuration
    source_catalog_path: str = Field(
        default="data/turkish-job-sources.md",
        description="Path to the canonical Markdown source catalog",
    )

    # Source Health Probe Configuration
    source_probe_timeout_seconds: float = Field(
        default=10.0,
        description="Timeout in seconds for source health probe HTTP requests",
    )
    source_probe_user_agent: str = Field(
        default="JobScope/0.1.0 (source-health-probe)",
        description="User-Agent header sent during source health probing",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that the database URL scheme is PostgreSQL-compatible."""
        if not v.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError(
                "DATABASE_URL must start with 'postgresql+asyncpg://' or 'postgresql://'"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of application settings."""
    return Settings()
