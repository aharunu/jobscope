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


class AIRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AIEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    claim: str
    evidence_type: str
    source_reference: str
    source_quote: str | None = None
    reason: str


class AIAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    match_result_id: uuid.UUID
    provider: str
    model: str
    ai_score: Decimal
    assessment: str
    summary: str
    strengths: list[str]
    gaps: list[str]
    risks: list[str]
    evidence: list[AIEvidenceResponse]
    created_at: datetime | None = None
    cached: bool = True


class MatchResultResponse(BaseModel):
    """Response payload for a deterministic match evaluation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    base_profile_id: uuid.UUID
    search_profile_id: uuid.UUID
    overall_score: Decimal = Field(
        ...,
        description="Final score (deterministic plus optional AI adjustment), 0–100",
    )
    deterministic_score: Decimal
    ai_score: Decimal | None = None
    ai_adjustment: Decimal | None = None
    ai_analysis: AIAnalysisResponse | None = None
    final_score: Decimal
    confidence: Decimal = Field(
        ...,
        description="Backend-calculated evidence confidence percentage (0 - 100%)",
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


class MatchListResponse(BaseModel):
    items: list[MatchResultResponse]
    total: int
    limit: int
    offset: int
