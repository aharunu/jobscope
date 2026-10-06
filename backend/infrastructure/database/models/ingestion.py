"""Independent ingestion audit and policy persistence; canonical data stays separate."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import BaseModel


class IngestionPolicyModel(BaseModel):
    __tablename__ = "ingestion_policies"
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), unique=True
    )
    allowed_country_codes: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    include_unknown_country: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    __table_args__ = (
        Index(
            "uq_ingestion_global_policy",
            text("(true)"),
            unique=True,
            postgresql_where=text("source_id IS NULL"),
        ),
    )


class CountsMixin:
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_closed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class IngestionRunModel(CountsMixin, BaseModel):
    __tablename__ = "ingestion_runs"
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    sources_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_partial: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    __table_args__ = (
        Index(
            "uq_ingestion_active_run",
            text("(true)"),
            unique=True,
            postgresql_where=text("status IN ('PENDING','RUNNING')"),
        ),
        Index("ix_ingestion_run_created", "created_at"),
    )


class IngestionSourceRunModel(CountsMixin, BaseModel):
    __tablename__ = "ingestion_source_runs"
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    ats_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    acquisition_complete: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    closure_authorized: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    closure_suppression_reason: Mapped[str | None] = mapped_column(Text)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("run_id", "source_id", name="uq_ingestion_run_source"),
    )


class IngestionDecisionModel(BaseModel):
    __tablename__ = "ingestion_decisions"
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"), index=True
    )
    source_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_source_runs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"), index=True)
    external_job_id: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(Text)
    resolved_country: Mapped[str | None] = mapped_column(String(2))
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    __table_args__ = (
        Index("ix_ingestion_decision_filter", "run_id", "decision", "source_id"),
    )
