"""Source repository protocol interface."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.source.entities import Source


@runtime_checkable
class SourceRepository(Protocol):
    """Repository interface for Source entities.

    Pure Python typing Protocol completely decoupled from persistence
    technologies and ORM frameworks.
    """

    async def get_by_id(self, source_id: uuid.UUID) -> Source | None:
        """Retrieve a source by its unique ID."""
        ...

    async def get_by_url(self, url: str) -> Source | None:
        """Retrieve a source by its exact career page / API URL."""
        ...

    async def list_all(
        self,
        active_only: bool = False,
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Source]:
        """List sources matching the given filters and pagination."""
        ...

    async def save(self, source: Source) -> Source:
        """Persist a single source entity (insert or update)."""
        ...

    async def save_bulk(self, sources: list[Source]) -> list[Source]:
        """Persist multiple source entities in batch."""
        ...

    async def count(
        self,
        active_only: bool = False,
        is_active: bool | None = None,
        ats_type: str | None = None,
        search_query: str | None = None,
    ) -> int:
        """Count sources matching the given filters."""
        ...

    async def count_by_ats_type(self) -> dict[str, int]:
        """Aggregate total sources grouped by ATS platform type."""
        ...

    async def count_by_country(self) -> dict[str, int]:
        """Aggregate total sources grouped by country code."""
        ...
