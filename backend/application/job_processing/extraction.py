"""Job requirement extraction application service and extractor protocol."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.job.repositories import JobRequirementRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class RequirementExtractor(Protocol):
    """Protocol for extracting structured JobRequirements from a canonical Job."""

    def extract(self, job: Job) -> list[JobRequirement]:
        """Extract structured requirements from canonical job content."""
        ...


@dataclass(slots=True)
class RequirementExtractionService:
    """Application service orchestrating requirement extraction and persistence.

    Upholds Clean Architecture:
    - Pure application service independent of specific persistence ORMs.
    - Coordinates deterministic extraction and atomic database replacement.
    - Empty extraction safely persists zero requirements without errors.
    """

    requirement_repo: JobRequirementRepository
    extractor: RequirementExtractor

    async def extract_and_persist(self, job: Job) -> list[JobRequirement]:
        """Extract structured requirements from job and persist them atomically."""
        requirements = self.extractor.extract(job)
        saved = await self.requirement_repo.save_requirements(job.id, requirements)
        logger.debug(
            "Extracted and persisted %d requirement(s) for job %s",
            len(saved),
            job.id,
        )
        return saved
