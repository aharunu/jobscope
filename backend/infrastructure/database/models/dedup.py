"""Occurrence identity and durable review / retirement audit models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.infrastructure.database.base import BaseModel


class JobOccurrenceModel(BaseModel):
    __tablename__ = "job_occurrences"
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"), index=True
    )
    external_job_id: Mapped[str | None] = mapped_column(String(255))
    canonical_url: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE")
    content_hash: Mapped[str | None] = mapped_column(String(64))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reference: Mapped[str | None] = mapped_column(Text)
    projection: Mapped[dict] = mapped_column(JSONB, default=dict)
    dedup_outcome: Mapped[str] = mapped_column(String(20), default="NEW_JOB")
    dedup_score: Mapped[int] = mapped_column(Integer, default=0)
    dedup_signals: Mapped[dict] = mapped_column(JSONB, default=dict)
    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_job_id", name="uq_occurrence_source_external"
        ),
        UniqueConstraint("source_id", "canonical_url", name="uq_occurrence_source_url"),
        CheckConstraint("status IN ('ACTIVE','CLOSED')", name="ck_occurrence_status"),
        Index("ix_occurrence_source_status", "source_id", "status"),
    )


class DedupCandidateModel(BaseModel):
    __tablename__ = "dedup_candidates"
    left_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    right_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    score: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(20))
    signals: Mapped[dict] = mapped_column(JSONB)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(String(30))
    __table_args__ = (
        UniqueConstraint("left_job_id", "right_job_id", name="uq_dedup_pair"),
        CheckConstraint("left_job_id < right_job_id", name="ck_dedup_order"),
    )


class JobMergeRecordModel(BaseModel):
    __tablename__ = "job_merge_records"
    source_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), unique=True
    )
    target_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE")
    )
    reason: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)
    signals: Mapped[dict | None] = mapped_column(JSONB)
