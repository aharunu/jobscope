"""Job discovery application ports (interfaces)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from backend.application.job_discovery.dtos import (
    CrawlResultDTO,
    RuntimeSourceDTO,
    SafeHttpResponseDTO,
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


@runtime_checkable
class ATSAdapter(Protocol):
    """Port implemented by platform-specific ATS adapters (Lever, Greenhouse, etc.).

    Decouples crawler orchestration from platform-specific HTTP schemas,
    pagination conventions, and payload extraction.
    """

    @property
    def ats_type(self) -> str:
        """Canonical ATS platform identifier handled by this adapter (e.g. 'lever')."""
        ...

    async def crawl(self, source: RuntimeSourceDTO) -> CrawlResultDTO:
        """Execute job discovery against a target runtime source.

        Consumes immutable RuntimeSourceDTO and returns a CrawlResultDTO containing
        discovered job items without touching canonical DB models.
        """
        ...


@runtime_checkable
class SafeHttpClient(Protocol):
    """Port for executing outbound HTTP requests with mandatory SSRF protection."""

    async def get(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SafeHttpResponseDTO:
        """Perform an SSRF-validated GET request."""
        ...


@runtime_checkable
class CrawlPersistenceManager(Protocol):
    """Port for managing CrawlRun lifecycle and transactional persistence boundaries."""

    async def create_initial_run(self, source_id: uuid.UUID) -> uuid.UUID:
        """Transaction A: Persist initial CrawlRun with RUNNING status and commit.

        Returns the persistent crawl_run_id.
        """
        ...

    async def mark_run_failed(
        self,
        crawl_run_id: uuid.UUID,
        error_count: int = 1,
        error_message: str | None = None,
    ) -> None:
        """Failure Transaction: Update existing CrawlRun to FAILED status
        in a fresh transaction and commit.
        """
        ...

    async def execute_ingestion(
        self,
        source: RuntimeSourceDTO,
        crawl_result: CrawlResultDTO,
        crawl_run_id: uuid.UUID,
    ) -> Any:
        """Transaction B: Ingest crawl result and finalize CrawlRun
        in an atomic transaction.

        Rolls back on error.
        """
        ...
