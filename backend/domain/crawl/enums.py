"""Crawl domain enums."""

import enum


class CrawlStatus(enum.StrEnum):
    """Execution status of a crawl run."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    SUCCESS = "COMPLETED"  # Canonical alias for completed crawl run status


class CrawlJobAction(enum.StrEnum):
    """Action performed on a specific job during a crawl run."""

    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    CLOSED = "CLOSED"
