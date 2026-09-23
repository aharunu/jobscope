"""Job discovery data transfer objects (DTOs)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceFilterDTO:
    """Filter criteria for querying registered job sources."""

    active_only: bool = False
    ats_type: str | None = None
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
