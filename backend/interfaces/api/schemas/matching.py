"""Pydantic schemas for the Matching API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.domain.matching.enums import MatchStatus


class MatchRequest(BaseModel):
    """Payload to trigger deterministic matching evaluation."""

    model_config = ConfigDict(extra="forbid")

    job_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the target canonical job",
    )
    search_profile_id: uuid.UUID = Field(
        ...,
        description="Unique identifier of the candidate search profile",
    )


class RequirementMatchResponse(BaseModel):
    """Individual evaluated requirement result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_id: uuid.UUID
    match_status: MatchStatus
    score: Decimal
    reason: str
    evidence: str | None = None
    is_blocker: bool = False


class CategoryExplanationResponse(BaseModel):
    """Structured explanation for a single evaluation category."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    status: MatchStatus
    score: Decimal
    reason: str
    details: list[str] = Field(default_factory=list)


class MatchExplanationResponse(BaseModel):
    """Comprehensive structured explanation of the deterministic match."""

    model_config = ConfigDict(from_attributes=True)

    summary: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    role_result: str = ""
    experience_result: str = ""
    education_result: str = ""
    location_result: str = ""
    blockers: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    category_explanations: dict[str, CategoryExplanationResponse] = Field(
        default_factory=dict
    )


class MatchResultResponse(BaseModel):
    """Response payload for a deterministic match evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    base_profile_id: uuid.UUID
    search_profile_id: uuid.UUID
    overall_score: Decimal = Field(
        ...,
        description="Deterministic overall score on a 0 - 100 scale",
    )
    deterministic_score: Decimal
    final_score: Decimal
    confidence: Decimal = Field(
        ...,
        description="Evidence-based deterministic confidence percentage (0 - 100%)",
    )
    category_scores: dict[str, Decimal] = Field(
        default_factory=dict,
        description="Normalized category scores (0.0 - 1.0)",
    )
    requirement_matches: list[RequirementMatchResponse] = Field(
        default_factory=list,
        description="Detailed evaluations for each requirement",
    )
    explanation: MatchExplanationResponse | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
