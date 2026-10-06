"""Strict input contracts for ingestion control."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.application.ingestion.policy import normalize_codes
from backend.domain.source.enums import is_known_ats_type


class PolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allowed_country_codes: list[str] = Field(default_factory=list, max_length=249)
    include_unknown_country: bool = False
    enabled: bool = True

    @field_validator("allowed_country_codes")
    @classmethod
    def codes(cls, value):
        return normalize_codes(value)


class StartIngestionRequest(PolicyRequest):
    mode: Literal["PREVIEW", "PERSIST"]
    from_preview_run_id: uuid.UUID | None = None
    source_ids: list[uuid.UUID] | None = None
    ats_types: list[str] | None = None
    active_sources_only: bool = True
    policy_mode: Literal["USE_SAVED_POLICIES", "OVERRIDE_SELECTED_SOURCES"] = (
        "USE_SAVED_POLICIES"
    )

    @field_validator("ats_types")
    @classmethod
    def ats(cls, value):
        if value is None:
            return value
        result = sorted({v.strip().lower() for v in value})
        if any(not is_known_ats_type(v) for v in result):
            raise ValueError("Unknown ATS type")
        return result

    @model_validator(mode="after")
    def no_ambiguous_scope(self):
        if self.from_preview_run_id is not None and (
            self.mode != "PERSIST"
            or self.model_fields_set - {"mode", "from_preview_run_id"}
        ):
            raise ValueError(
                "Preview persistence requires only mode and preview run ID"
            )
        if self.source_ids == [] or self.ats_types == []:
            raise ValueError("Empty scope selections are not allowed")
        return self
