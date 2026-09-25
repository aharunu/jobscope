"""Source registry application service."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.application.job_discovery.dtos import (
    SourceBatchProbeResultDTO,
    SourceCreateDTO,
    SourceFilterDTO,
    SourceProbeResultDTO,
    SyncResultDTO,
)
from backend.application.job_discovery.ports import (
    CatalogParser,
    SourceHealthProbe,
)
from backend.domain.source.entities import Source
from backend.domain.source.normalization import normalize_source_url
from backend.domain.source.repositories import SourceRepository

logger = logging.getLogger(__name__)


class SourceRegistryService:
    """Application service for managing the job discovery source registry.

    Coordinates querying, synchronization, and persistence of job sources,
    decoupled from HTTP delivery, database ORM models, and parser implementations.
    """

    def __init__(
        self,
        repository: SourceRepository,
        catalog_parser: CatalogParser | None = None,
        health_probe: SourceHealthProbe | None = None,
        default_catalog_path: str = "data/turkish-job-sources.md",
    ) -> None:
        self.repository = repository
        self.catalog_parser = catalog_parser
        self.health_probe = health_probe
        self.default_catalog_path = default_catalog_path

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
        """Retrieve a source by its exact or normalized URL."""
        normalized = normalize_source_url(url)
        return await self.repository.get_by_url(normalized)

    async def register_source(self, dto: SourceCreateDTO) -> Source:
        """Programmatically register a source entity.

        Internal foundation used by crawler setups and importer.
        """
        normalized_url = normalize_source_url(dto.url)
        kwargs: dict[str, Any] = {
            "name": dto.name,
            "url": normalized_url,
            "ats_type": dto.ats_type,
            "company": dto.company,
            "country": dto.country or "TR",
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

    async def sync_sources(
        self,
        dtos: list[SourceCreateDTO],
        initial_warnings: list[str] | None = None,
    ) -> SyncResultDTO:
        """Synchronize a list of SourceCreateDTOs into the database idempotently.

        1. Normalizes URLs and deduplicates within the batch.
        2. Preserves existing operational configurations (adapter_config, active).
        3. Creates new entries or non-destructively updates existing entries.
        """

        warnings: list[str] = list(initial_warnings or [])
        total_scanned = len(dtos) + len(warnings)
        created = 0
        updated = 0
        skipped = len(warnings)

        # In-memory deduplication by normalized URL
        deduped: dict[str, SourceCreateDTO] = {}
        for dto in dtos:
            norm_url = normalize_source_url(dto.url)
            if not norm_url:
                skipped += 1
                warnings.append(
                    f"Skipped source '{dto.name}' due to invalid or empty URL."
                )
                continue

            if norm_url in deduped:
                # Merge metadata from duplicate entry
                existing_dto = deduped[norm_url]
                merged_meta = {**existing_dto.metadata, **dto.metadata}
                alt_urls = set(existing_dto.metadata.get("alternate_urls", []))
                alt_urls.update(dto.metadata.get("alternate_urls", []))
                if alt_urls:
                    merged_meta["alternate_urls"] = sorted(alt_urls)
                existing_dto.metadata = merged_meta
                skipped += 1
                warnings.append(
                    f"Merged duplicate catalog entry for '{norm_url}' ({dto.name})."
                )
            else:
                dto.url = norm_url
                deduped[norm_url] = dto

        for norm_url, dto in deduped.items():
            existing = await self.repository.get_by_url(norm_url)
            if existing is None:
                source_id = dto.id if dto.id is not None else uuid.uuid4()
                new_source = Source(
                    id=source_id,
                    name=dto.name,
                    url=norm_url,
                    ats_type=dto.ats_type,
                    company=dto.company,
                    country=dto.country or "TR",
                    active=dto.active,
                    adapter_config=dto.adapter_config,
                    pagination_config=dto.pagination_config,
                    endpoint_config=dto.endpoint_config,
                    rate_limit_config=dto.rate_limit_config,
                    metadata=dto.metadata,
                )
                await self.repository.save(new_source)
                created += 1
            else:
                # Non-destructive update: preserve configs and manual active toggle
                merged_metadata = {**existing.metadata, **dto.metadata}
                combined_alt = set(existing.metadata.get("alternate_urls", []))
                combined_alt.update(dto.metadata.get("alternate_urls", []))
                if combined_alt:
                    merged_metadata["alternate_urls"] = sorted(combined_alt)

                # Prioritize identified ATS type over generic custom
                ats_type = (
                    dto.ats_type
                    if (existing.ats_type == "custom" and dto.ats_type != "custom")
                    else existing.ats_type
                )

                updated_source = Source(
                    id=existing.id,
                    name=dto.name or existing.name,
                    url=existing.url,
                    ats_type=ats_type,
                    company=dto.company or existing.company,
                    country=existing.country or dto.country or "TR",
                    active=existing.active,  # Preserve manual status
                    adapter_config=existing.adapter_config,  # Preserve custom config
                    pagination_config=existing.pagination_config,  # Preserve
                    endpoint_config=existing.endpoint_config,  # Preserve
                    rate_limit_config=existing.rate_limit_config,  # Preserve
                    metadata=merged_metadata,
                    created_at=existing.created_at,
                )
                await self.repository.save(updated_source)
                updated += 1

        return SyncResultDTO(
            total_scanned=total_scanned,
            created=created,
            updated=updated,
            skipped=skipped,
            errors=warnings,
        )

    async def sync_from_catalog(
        self,
        file_path: str | None = None,
    ) -> SyncResultDTO:
        """Parse canonical catalog file and synchronize sources into the registry."""
        if self.catalog_parser is None:
            raise RuntimeError(
                "Catalog parser port is not configured on SourceRegistryService."
            )

        path_to_use = file_path or self.default_catalog_path
        logger.info("Synchronizing sources from catalog file: %s", path_to_use)

        dtos, parse_warnings = self.catalog_parser.parse_file(path_to_use)
        return await self.sync_sources(dtos, initial_warnings=parse_warnings)

    async def probe_source(
        self,
        source_id: uuid.UUID,
    ) -> SourceProbeResultDTO | None:
        """Probe an individual registered source for HTTP health.

        Returns None if the source ID is not found in the repository.
        Does NOT modify Source.active or any database state.
        """
        if self.health_probe is None:
            raise RuntimeError(
                "Health probe port is not configured on SourceRegistryService."
            )

        source = await self.repository.get_by_id(source_id)
        if source is None:
            return None

        return await self.health_probe.probe(
            url=source.url,
            source_id=source.id,
            ats_type=source.ats_type,
        )

    async def probe_sources_batch(
        self,
        filter_: SourceFilterDTO | None = None,
        max_concurrency: int = 10,
    ) -> SourceBatchProbeResultDTO:
        """Probe multiple registered sources matching filters concurrently.

        Does NOT modify Source.active or any database state.
        """
        if self.health_probe is None:
            raise RuntimeError(
                "Health probe port is not configured on SourceRegistryService."
            )

        sources = await self.list_sources(filter_=filter_)
        if not sources:
            return SourceBatchProbeResultDTO(
                total_probed=0,
                reachable_count=0,
                unreachable_count=0,
                results=[],
            )

        probe_targets = [(source.id, source.url, source.ats_type) for source in sources]
        return await self.health_probe.probe_batch(
            sources=probe_targets,
            max_concurrency=max_concurrency,
        )
