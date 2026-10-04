"""Strict provider-neutral structured output. Scores are never final scores."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1"


def validate_provider_text(value: str) -> str:
    # JSON can encode NUL, but PostgreSQL text/JSONB cannot store it. Reject the
    # provider output before evidence sanitization or any persistence changes.
    if "\x00" in value:
        raise ValueError("AI text cannot contain NUL characters")
    return value


ProviderText = Annotated[str, AfterValidator(validate_provider_text)]
Text = Annotated[ProviderText, Field(min_length=1, max_length=4000)]


class EvidenceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    claim: Text
    evidence_type: Literal["PROJECT", "EXPERIENCE", "EDUCATION", "SKILL", "NONE"]
    source_reference: Text
    source_quote: Annotated[ProviderText, Field(max_length=4000)]
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
