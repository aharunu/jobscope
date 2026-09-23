"""Source registry application service."""

from __future__ import annotations

import uuid
from typing import Any

from backend.application.job_discovery.dtos import SourceCreateDTO, SourceFilterDTO
from backend.domain.source.entities import Source
from backend.domain.source.repositories import SourceRepository


class SourceRegistryService:
    """Application service for managing the job discovery source registry.

    Coordinates querying and programmatic persistence of job sources,
    decoupled from HTTP delivery and ORM models.
    """

    def __init__(self, repository: SourceRepository) -> None:
        self.repository = repository

    async def list_sources(
        self,
        filter_: SourceFilterDTO | None = None,
    ) -> list[Source]:
        """List sources matching the provided filter criteria."""
        if filter_ is None:
            filter_ = SourceFilterDTO()

        return await self.repository.list_all(
            active_only=filter_.active_only,
            ats_type=filter_.ats_type,
            limit=filter_.limit,
            offset=filter_.offset,
        )

    async def count_sources(
        self,
        active_only: bool = False,
        ats_type: str | None = None,
    ) -> int:
        """Count registered sources matching criteria."""
        return await self.repository.count(
            active_only=active_only,
            ats_type=ats_type,
        )

    async def get_source(self, source_id: uuid.UUID) -> Source | None:
        """Retrieve a source by its unique ID."""
        return await self.repository.get_by_id(source_id)

    async def get_source_by_url(self, url: str) -> Source | None:
        """Retrieve a source by its exact URL."""
        return await self.repository.get_by_url(url)

    async def register_source(self, dto: SourceCreateDTO) -> Source:
        """Programmatically register a source entity.

        Internal foundation used by crawler setups and upcoming importer.
        """
        kwargs: dict[str, Any] = {
            "name": dto.name,
            "url": dto.url,
            "ats_type": dto.ats_type,
            "company": dto.company,
            "country": dto.country,
            "active": dto.active,
            "adapter_config": dto.adapter_config,
            "pagination_config": dto.pagination_config,
            "endpoint_config": dto.endpoint_config,
            "rate_limit_config": dto.rate_limit_config,
            "metadata": dto.metadata,
        }
        if dto.id is not None:
            kwargs["id"] = dto.id

        source = Source(**kwargs)
        return await self.repository.save(source)

    async def save_sources(self, sources: list[Source]) -> list[Source]:
        """Programmatically bulk persist sources."""
        return await self.repository.save_bulk(sources)
