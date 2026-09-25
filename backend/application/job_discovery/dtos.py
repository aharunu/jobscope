"""Job discovery data transfer objects (DTOs)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class SourceFilterDTO:
    """Filter criteria for querying registered job sources."""

    active_only: bool = False
    is_active: bool | None = None
    ats_type: str | None = None
    search_query: str | None = None
    limit: int = 100
    offset: int = 0


@dataclass(slots=True)
class SourceCreateDTO:
    """DTO for programmatic source registration (service/importer foundation)."""

    name: str
    url: str
    ats_type: str
    id: uuid.UUID | None = None
    company: str | None = None
    country: str | None = None
    active: bool = True
    adapter_config: dict[str, Any] = field(default_factory=dict)
    pagination_config: dict[str, Any] = field(default_factory=dict)
    endpoint_config: dict[str, Any] = field(default_factory=dict)
    rate_limit_config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SyncResultDTO:
    """Summary of source catalog synchronization."""

    total_scanned: int
    created: int
    updated: int
    skipped: int
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SourceProbeResultDTO:
    """Diagnostic health result for an individual source probe."""

    source_id: uuid.UUID | None
    url: str
    is_reachable: bool
    status_code: int | None
    latency_ms: float | None
    final_url: str | None
    redirect_count: int
    error_type: str | None
    error_message: str | None
    ats_type: str | None = None
    probed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SourceBatchProbeResultDTO:
    """Summary of batch source health probing."""

    total_probed: int
    reachable_count: int
    unreachable_count: int
    results: list[SourceProbeResultDTO] = field(default_factory=list)


@dataclass(slots=True)
class SourceUpdateDTO:
    """DTO for operational configuration updates. Does NOT contain active status."""

    name: str | None = None
    adapter_config: dict[str, Any] | None = None
    pagination_config: dict[str, Any] | None = None
    endpoint_config: dict[str, Any] | None = None
    rate_limit_config: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class SourceStatsDTO:
    """Aggregated operational statistics for registered sources."""

    total_sources: int
    active_sources: int
    inactive_sources: int
    by_ats_type: dict[str, int] = field(default_factory=dict)
    by_country: dict[str, int] = field(default_factory=dict)
