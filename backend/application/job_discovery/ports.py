"""Job discovery application ports (interfaces)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from backend.application.job_discovery.dtos import (
    RuntimeSourceDTO,
    SourceBatchProbeResultDTO,
    SourceCreateDTO,
    SourceProbeResultDTO,
)


@runtime_checkable
class CatalogParser(Protocol):
    """Port for parsing job source catalog content or files into DTOs."""

    def parse_content(self, content: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse raw catalog text into SourceCreateDTOs and warning messages."""
        ...

    def parse_file(self, file_path: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse a catalog file into SourceCreateDTOs and warning messages."""
        ...


@runtime_checkable
class SourceHealthProbe(Protocol):
    """Port for probing source HTTP(S) health and reachability."""

    async def probe(
        self,
        url: str,
        source_id: uuid.UUID | None = None,
        ats_type: str | None = None,
    ) -> SourceProbeResultDTO:
        """Probe an individual source URL and return diagnostic metrics."""
        ...

    async def probe_batch(
        self,
        sources: Sequence[tuple[uuid.UUID, str, str | None]],
        max_concurrency: int = 10,
    ) -> SourceBatchProbeResultDTO:
        """Probe multiple sources concurrently with bounded concurrency."""
        ...


@runtime_checkable
class RuntimeSourceProvider(Protocol):
    """Port for retrieving crawlable active sources for crawler execution."""

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        """Retrieve deterministic list of active sources ready for crawling."""
        ...

    async def get_crawlable_source(
        self,
        source_id: uuid.UUID,
    ) -> RuntimeSourceDTO | None:
        """Retrieve a single active crawlable source by its ID."""
        ...
