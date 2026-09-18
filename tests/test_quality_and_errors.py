"""Tests for error handling baseline, log secret masking, and developer tooling."""

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.application.common.exceptions import InfrastructureError, JobScopeError
from backend.infrastructure.config.settings import Settings
from backend.infrastructure.logging.logger import SecretMaskingFilter
from backend.interfaces.api.main import create_app
from scripts.dev import parse_dev_args


def test_jobscope_error_handling(app: FastAPI, client: TestClient) -> None:
    """Verify JobScopeError generates structured, predictable HTTP error responses."""

    @app.get("/test-application-error")
    async def sample_app_error_route():
        raise JobScopeError(
            message="Item not found or invalid",
            code="RESOURCE_INVALID",
            status_code=422,
            details={"field": "id", "reason": "non_positive"},
        )

    response = client.get("/test-application-error")
    assert response.status_code == 422

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_INVALID"
    assert data["error"]["message"] == "Item not found or invalid"
    assert data["error"]["details"] == {"field": "id", "reason": "non_positive"}


def test_infrastructure_error_handling(app: FastAPI, client: TestClient) -> None:
    """Verify InfrastructureError generates HTTP 500 with infrastructure error code."""

    @app.get("/test-infrastructure-error")
    async def sample_infra_error_route():
        raise InfrastructureError("Database pool exhausted")

    response = client.get("/test-infrastructure-error")
    assert response.status_code == 500

    data = response.json()
    assert data["error"]["code"] == "INFRASTRUCTURE_ERROR"
    assert data["error"]["message"] == "Database pool exhausted"


def test_unhandled_exception_handling_sanitizes_output() -> None:
    """Verify unhandled exceptions return 500 without leaking stack traces
    or internal secrets in non-debug mode.
    """
    settings = Settings(
        app_name="JobScope-Test",
        app_version="0.1.0-test",
        environment="production",
        debug=False,
        database_url="postgresql+asyncpg://test:test@localhost:5432/jobscope_test",
    )
    prod_app = create_app(settings=settings)

    @prod_app.get("/test-unhandled-exception")
    async def sample_unhandled_route():
        raise ZeroDivisionError("internal calculation crash on 10.0.0.5")

    client = TestClient(prod_app, raise_server_exceptions=False)
    response = client.get("/test-unhandled-exception")
    assert response.status_code == 500

    data = response.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected server error occurred."
    assert "ZeroDivisionError" not in str(data)
    assert "10.0.0.5" not in str(data)


def test_secret_masking_log_filter() -> None:
    """Verify SecretMaskingFilter masks database credentials and passwords in logs."""
    masking_filter = SecretMaskingFilter()

    # Test database URL credentials masking
    record1 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Connecting to postgresql://jobscope:topsecret123@localhost:5432/jobscope",
        args=(),
        exc_info=None,
    )
    masking_filter.filter(record1)
    assert "topsecret123" not in record1.msg
    assert "postgresql://jobscope:***@localhost:5432/jobscope" in record1.msg

    # Test key-value password masking
    record2 = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Auth failed with password: 'my_raw_password'",
        args=(),
        exc_info=None,
    )
    masking_filter.filter(record2)
    assert "my_raw_password" not in record2.msg
    assert "password=***" in record2.msg


def test_dev_cli_parser_commands() -> None:
    """Verify developer CLI parser resolves task subcommands and arguments."""
    # test
    args = parse_dev_args(["test", "-k", "health"])
    assert args.command == "test"
    assert args.extra_args == ["-k", "health"]

    # lint
    args = parse_dev_args(["lint", "--fix"])
    assert args.command == "lint"
    assert args.fix is True

    # format
    args = parse_dev_args(["format", "--check"])
    assert args.command == "format"
    assert args.check is True

    # run
    args = parse_dev_args(["run", "--port", "8080", "--host", "0.0.0.0"])
    assert args.command == "run"
    assert args.port == 8080
    assert args.host == "0.0.0.0"

    # check
    args = parse_dev_args(["check"])
    assert args.command == "check"
