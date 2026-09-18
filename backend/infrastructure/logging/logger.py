"""Logging configuration and setup."""

import logging
import re
import sys
from pathlib import Path


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
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logging(
    log_level: str = "INFO",
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

    # Attach secret masking filter to each handler
    masking_filter = SecretMaskingFilter()
    for handler in handlers:
        handler.addFilter(masking_filter)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
