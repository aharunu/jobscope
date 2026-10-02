"""Tests for Phase 0: config, exception hierarchy, logging, and security."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.application.common.exceptions import JobScopeError
from backend.application.matching.exceptions import (
    BaseProfileNotFoundError,
    JobNotFoundError,
    MatchingError,
    SearchProfileNotFoundError,
)
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.database.models.job import JobModel
from backend.infrastructure.logging.logger import (
    JSONFormatter,
    SecretMaskingFilter,
    SecretMaskingFormatter,
    setup_logging,
)
from backend.interfaces.api.errors import register_exception_handlers

# ==============================================================================
# 1. Configuration & .env.example Tests
# ==============================================================================


def test_env_example_matches_settings_fields() -> None:
    """Verify that .env.example defines all critical configuration settings."""
    env_example_path = Path(".env.example")
    assert env_example_path.exists(), ".env.example file must exist at repo root"

    content = env_example_path.read_text(encoding="utf-8")

    # Critical variables that must be documented in .env.example
    expected_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "APP_NAME",
        "APP_VERSION",
        "HOST",
        "PORT",
        "DATABASE_URL",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "SOURCE_CATALOG_PATH",
        "SOURCE_PROBE_TIMEOUT_SECONDS",
        "SOURCE_PROBE_USER_AGENT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]

    for var in expected_vars:
        assert f"{var}=" in content, f"Expected {var} to be defined in .env.example"


def test_settings_log_format_configuration(monkeypatch) -> None:
    """Verify log_format default value and environment override."""
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    default_settings = Settings(_env_file=None)
    assert default_settings.log_format == "console"

    monkeypatch.setenv("LOG_FORMAT", "json")
    json_settings = Settings()
    assert json_settings.log_format == "json"


def test_database_url_validation() -> None:
    """Verify that invalid database URL schemes are rejected."""
    with pytest.raises(ValueError, match="DATABASE_URL must start with"):
        Settings(database_url="sqlite:///test.db")

    with pytest.raises(ValueError, match="DATABASE_URL must start with"):
        Settings(database_url="mysql://user:pass@localhost/db")

    # Valid schemes should succeed
    s_async = Settings(database_url="postgresql+asyncpg://user:pass@localhost:5432/db")
    assert s_async.database_url.startswith("postgresql+asyncpg://")

    s_sync = Settings(database_url="postgresql://user:pass@localhost:5432/db")
    assert s_sync.database_url.startswith("postgresql://")


# ==============================================================================
# 2. Exception Hierarchy Tests
# ==============================================================================


def test_matching_exception_hierarchy() -> None:
    """Verify that matching exceptions correctly inherit from JobScopeError."""
    assert issubclass(MatchingError, JobScopeError)
    assert issubclass(JobNotFoundError, MatchingError)
    assert issubclass(JobNotFoundError, JobScopeError)
    assert issubclass(SearchProfileNotFoundError, MatchingError)
    assert issubclass(SearchProfileNotFoundError, JobScopeError)
    assert issubclass(BaseProfileNotFoundError, MatchingError)
    assert issubclass(BaseProfileNotFoundError, JobScopeError)


def test_matching_exception_attributes() -> None:
    """Verify status codes, error codes, and message semantics on exceptions."""
    base_err = MatchingError(message="Generic match error")
    assert base_err.status_code == 400
    assert base_err.code == "MATCHING_ERROR"
    assert str(base_err) == "Generic match error"

    job_err = JobNotFoundError("Job 'abc' not found")
    assert job_err.status_code == 404
    assert job_err.code == "JOB_NOT_FOUND"
    assert str(job_err) == "Job 'abc' not found"

    sp_err = SearchProfileNotFoundError("SearchProfile 'xyz' not found")
    assert sp_err.status_code == 404
    assert sp_err.code == "SEARCH_PROFILE_NOT_FOUND"

    bp_err = BaseProfileNotFoundError("BaseProfile '123' not found")
    assert bp_err.status_code == 404
    assert bp_err.code == "BASE_PROFILE_NOT_FOUND"


def test_matching_exceptions_in_fastapi_error_handler() -> None:
    """Verify that JobScopeError exception handler formats standardized response."""
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/trigger-matching-error")
    def trigger_matching_error(param: str):
        if param == "job":
            raise JobNotFoundError("Custom job not found")
        if param == "matching":
            raise MatchingError("Calculation failed", details={"step": "eval"})
        return {"status": "ok"}

    client = TestClient(test_app)

    # 404 response for JobNotFoundError
    res1 = client.get("/trigger-matching-error?param=job")
    assert res1.status_code == 404
    d1 = res1.json()
    assert d1["error"]["code"] == "JOB_NOT_FOUND"
    assert d1["error"]["message"] == "Custom job not found"

    # 400 response for MatchingError
    res2 = client.get("/trigger-matching-error?param=matching")
    assert res2.status_code == 400
    d2 = res2.json()
    assert d2["error"]["code"] == "MATCHING_ERROR"
    assert d2["error"]["message"] == "Calculation failed"
    assert d2["error"]["details"] == {"step": "eval"}


# ==============================================================================
# 3. Structured Logging & Secret Masking Tests
# ==============================================================================


def test_json_formatter_structure() -> None:
    """Verify JSONFormatter produces parseable JSON with required machine fields."""
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="module.py",
        lineno=42,
        msg="Service started on port %s",
        args=(8000,),
        exc_info=None,
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert "timestamp" in parsed
    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Service started on port 8000"
    assert "exception" not in parsed


def test_json_formatter_with_exception() -> None:
    """Verify JSONFormatter formats exceptions into machine-readable field."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Invalid configuration parameter")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="error_logger",
        level=logging.ERROR,
        pathname="module.py",
        lineno=10,
        msg="Failed to initialize service",
        args=(),
        exc_info=exc_info,
    )

    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    assert parsed["level"] == "ERROR"
    assert "exception" in parsed
    assert "ValueError: Invalid configuration parameter" in parsed["exception"]


def test_secret_masking_in_json_logging() -> None:
    """Verify credentials and passwords are masked before formatting in JSON."""
    masking_filter = SecretMaskingFilter()
    formatter = JSONFormatter()

    record = logging.LogRecord(
        name="db_logger",
        level=logging.INFO,
        pathname="db.py",
        lineno=1,
        msg="Connecting to %s with token: '%s'",
        args=(
            "postgresql+asyncpg://admin:super_secret_pass@localhost:5432/db",
            "token_abc_123",
        ),
        exc_info=None,
    )

    masking_filter.filter(record)
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    # Neither password nor token should appear in the JSON message
    assert "super_secret_pass" not in parsed["message"]
    assert "token_abc_123" not in parsed["message"]
    assert "postgresql+asyncpg://admin:***@localhost:5432/db" in parsed["message"]
    assert "token=***" in parsed["message"]


def test_setup_logging_json_mode(tmp_path: Path) -> None:
    """Verify setup_logging configures JSONFormatter when log_format='json'."""
    log_dir = tmp_path / "logs"
    setup_logging(log_level="DEBUG", log_format="json", log_dir=str(log_dir))

    root_logger = logging.getLogger()
    assert len(root_logger.handlers) >= 1

    # Verify handlers have JSONFormatter attached
    for handler in root_logger.handlers:
        assert isinstance(handler.formatter, JSONFormatter)

    # Reset logging back to default console to avoid polluting other tests
    setup_logging(log_level="INFO", log_format="console")


@pytest.mark.parametrize("formatter", [JSONFormatter(), SecretMaskingFormatter()])
def test_exception_tracebacks_mask_credentials(formatter) -> None:
    """Unhandled failures must not reveal secrets through traceback text."""
    import sys

    try:
        raise ValueError("postgresql://user:private_test_password@host/db token=abc123")
    except ValueError:
        record = logging.LogRecord(
            "test", logging.ERROR, __file__, 1, "Failed", (), sys.exc_info()
        )
    result = formatter.format(record)
    assert "private_test_password" not in result
    assert "abc123" not in result
    assert "ValueError" in result


def test_recoverable_parsing_logs_without_raw_content(caplog) -> None:
    """Malformed dates and JSON retain fallbacks without logging raw input."""
    from backend.application.job_processing.content_cleaning import (
        normalize_job_description_and_responsibilities,
    )
    from backend.application.job_processing.normalizer import JobNormalizer

    with caplog.at_level(logging.WARNING):
        assert JobNormalizer._parse_datetime(float("inf")) is None
        assert JobNormalizer._parse_datetime("9" * 100) is None
        assert JobNormalizer._parse_datetime("private invalid date") is None
        raw = "{private invalid payload}"
        assert normalize_job_description_and_responsibilities(raw) == (raw, None)
    assert len(caplog.records) == 4
    assert "private invalid" not in caplog.text


# ==============================================================================
# 4. Database Model Index Tests
# ==============================================================================


def test_job_model_location_and_work_mode_indexed() -> None:
    """Verify that JobModel defines indexes on location and work_mode columns."""
    columns = JobModel.__table__.columns
    assert "location" in columns
    assert columns["location"].index is True

    assert "work_mode" in columns
    assert columns["work_mode"].index is True


def test_migration_revisions_fit_alembic_version_column() -> None:
    """Every revision must be persistable in Alembic's default version table."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert len(scripts.get_heads()) == 1
    assert all(len(script.revision) <= 32 for script in scripts.walk_revisions())
