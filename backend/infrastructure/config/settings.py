"""Typed application settings using Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
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
        default="postgresql+asyncpg://jobscope:jobscope@localhost:5432/jobscope",
        description="PostgreSQL connection URL with async driver",
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log verbosity level")

    # Source Catalog Configuration
    source_catalog_path: str = Field(
        default="data/turkish-job-sources.md",
        description="Path to the canonical Markdown source catalog",
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
