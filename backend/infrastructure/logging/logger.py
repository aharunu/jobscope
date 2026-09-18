"""Logging configuration and setup."""

import logging
import sys
from pathlib import Path


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

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
