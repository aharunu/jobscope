"""Job discovery application ports (interfaces)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.application.job_discovery.dtos import SourceCreateDTO


@runtime_checkable
class CatalogParser(Protocol):
    """Port for parsing job source catalog content or files into DTOs."""

    def parse_content(self, content: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse raw catalog text into SourceCreateDTOs and warning messages."""
        ...

    def parse_file(self, file_path: str) -> tuple[list[SourceCreateDTO], list[str]]:
        """Parse a catalog file into SourceCreateDTOs and warning messages."""
        ...
