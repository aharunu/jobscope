"""Base interfaces and data structures for category evaluators."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from backend.domain.job.entities import Job, JobRequirement
from backend.domain.matching.enums import MatchStatus
from backend.domain.profile.entities import BaseProfile
from backend.domain.search_profile.entities import SearchProfile


@dataclass(slots=True)
class EvaluatedRequirement:
    """Evaluation outcome for an individual JobRequirement."""

    requirement_id: uuid.UUID
    match_status: MatchStatus
    score: Decimal
    reason: str
    evidence: str | None = None
    is_blocker: bool = False


@dataclass(slots=True)
class CategoryEvaluationResult:
    """Evaluation outcome for an entire matching category."""

    category: str
    status: MatchStatus
    score: Decimal  # Normalized 0.0 - 1.0
    weight: Decimal
    reason: str
    evaluated_requirements: list[EvaluatedRequirement] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    total_signals: int = 1
    known_signals: int = 1


class CategoryEvaluator(Protocol):
    """Protocol for deterministic category evaluators."""

    def evaluate(
        self,
        job: Job,
        requirements: list[JobRequirement],
        base_profile: BaseProfile,
        search_profile: SearchProfile,
    ) -> CategoryEvaluationResult:
        """Evaluate a specific category deterministically."""
        ...
