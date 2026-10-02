"""Strict provider-neutral structured output. Scores are never final scores."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1"
Text = Annotated[str, Field(min_length=1, max_length=4000)]


class EvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claim: Text
    evidence_type: Literal["PROJECT", "EXPERIENCE", "EDUCATION", "SKILL", "NONE"]
    source_reference: Text
    source_quote: Annotated[str, Field(max_length=4000)]
    reason: Text


class AIOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ai_score: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    assessment: Literal["STRONG", "MODERATE", "LOW"]
    summary: Text
    strengths: Annotated[list[Text], Field(max_length=30)]
    gaps: Annotated[list[Text], Field(max_length=30)]
    risks: Annotated[list[Text], Field(max_length=30)]
    evidence: Annotated[list[EvidenceOutput], Field(max_length=50)]
