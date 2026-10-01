"""Logging configuration and setup."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SecretMaskingFilter(logging.Filter):
    """Logging filter to mask sensitive values (passwords, tokens, credentials)."""

    PATTERNS: list[tuple[re.Pattern[str], str]] = [
        # Database URL with credentials: scheme://user:password@host
        (re.compile(r"(://[^:]+:)([^@]+)(@)"), r"\1***\3"),
        # Key-value pairs: password=secret, token=secret, api_key=secret
        (
            re.compile(
                r"(password|token|secret|api_key|api-key)\s*[:=]\s*['\"]?([^'\"\s,]+)['\"]?",
                re.IGNORECASE,
            ),
            r"\1=***",
        ),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and redact sensitive patterns in log messages."""
        try:
            if record.args:
                record.msg = record.getMessage()
                record.args = ()
        except Exception:
            pass

        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)

        return True


class JSONFormatter(logging.Formatter):
    """Machine-readable JSON log formatter with structured fields."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a LogRecord into a single-line JSON string."""
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        message = record.getMessage()

        payload: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            payload["exception"] = record.exc_text

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "console",
    log_dir: str | None = None,
) -> None:
    """Configure structured logging for stdout and optional file logging."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.FileHandler(log_path / "jobscope.log", encoding="utf-8")
        )

    # Attach secret masking filter and appropriate formatter to each handler
    masking_filter = SecretMaskingFilter()
    formatter: logging.Formatter
    if log_format.lower() == "json":
        formatter = JSONFormatter()
    else:
        fmt_str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        formatter = logging.Formatter(fmt_str)

    for handler in handlers:
        handler.addFilter(masking_filter)
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True,
    )
