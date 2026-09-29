"""Search profile domain repository protocols."""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from backend.domain.search_profile.entities import SearchProfile


@runtime_checkable
class SearchProfileRepository(Protocol):
    """Protocol defining persistence operations for SearchProfile entities."""

    async def get_by_id(self, search_profile_id: uuid.UUID) -> SearchProfile | None:
        """Retrieve a search profile by its unique identifier."""
        ...

    async def get_by_id_and_base_profile_id(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> SearchProfile | None:
        """Retrieve a search profile strictly scoped to its base profile."""
        ...

    async def list_by_base_profile_id(
        self, base_profile_id: uuid.UUID
    ) -> list[SearchProfile]:
        """List all search profiles belonging to a given base profile."""
        ...

    async def save(self, search_profile: SearchProfile) -> SearchProfile:
        """Persist or update a search profile entity."""
        ...

    async def delete(
        self, search_profile_id: uuid.UUID, base_profile_id: uuid.UUID
    ) -> bool:
        """Delete a search profile scoped to base profile. Returns True if deleted."""
        ...
