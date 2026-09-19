"""Matching domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from backend.domain.matching.enums import MatchStatus


@dataclass(slots=True)
class MatchResult:
    """Domain entity representing matching evaluation between a job and a profile.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    job_id: uuid.UUID
    base_profile_id: uuid.UUID
    search_profile_id: uuid.UUID
    deterministic_score: Decimal
    final_score: Decimal
    confidence: Decimal
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    ai_score: Decimal | None = None
    ai_adjustment: Decimal | None = Decimal("0.0")
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class RequirementMatch:
    """Domain entity representing evaluation of a single requirement against a profile.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    match_result_id: uuid.UUID
    requirement_id: uuid.UUID
    match_status: MatchStatus
    score: Decimal
    reason: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    evidence: str | None = None
    is_blocker: bool = False


@dataclass(slots=True)
class AIAnalysis:
    """Domain entity representing LLM/AI detailed evaluation of a match result.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    match_result_id: uuid.UUID
    model: str
    provider: str
    ai_score: Decimal
    assessment: str
    summary: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    fingerprint: str | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class AIEvidence:
    """Domain entity representing a concrete claim and profile proof from AI analysis.

    Pure Python representation independent of persistence or ORM frameworks.
    """

    ai_analysis_id: uuid.UUID
    claim: str
    evidence_type: str
    source_reference: str
    reason: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
