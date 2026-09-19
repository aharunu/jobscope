"""Job and RawJob ORM persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.job.entities import Job, RawJob
from backend.domain.job.enums import JobStatus
from backend.infrastructure.database.base import (
    Base,
    BaseModel,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.infrastructure.database.models.source import SourceModel


class JobModel(BaseModel):
    """SQLAlchemy ORM model for the canonical jobs table."""

    __tablename__ = "jobs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_job_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    canonical_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    salary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
        index=True,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus, native_enum=False, length=50),
        default=JobStatus.ACTIVE,
        server_default=sa.text("'ACTIVE'"),
        nullable=False,
        index=True,
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "external_job_id",
            name="uq_source_external_job_id",
        ),
    )

    # Relationships
    source: Mapped[SourceModel] = relationship(
        "SourceModel",
        back_populates="jobs",
    )
    raw_jobs: Mapped[list[RawJobModel]] = relationship(
        "RawJobModel",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> Job:
        """Convert ORM model to domain entity."""
        return Job(
            id=self.id,
            source_id=self.source_id,
            external_job_id=self.external_job_id,
            canonical_url=self.canonical_url,
            company=self.company,
            title=self.title,
            description=self.description,
            responsibilities=self.responsibilities,
            location=self.location,
            work_mode=self.work_mode,
            employment_type=self.employment_type,
            salary=self.salary,
            published_at=self.published_at,
            first_seen_at=self.first_seen_at,
            last_seen_at=self.last_seen_at,
            closed_at=self.closed_at,
            status=self.status,
            content_hash=self.content_hash,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, job: Job) -> JobModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": job.id,
            "source_id": job.source_id,
            "external_job_id": job.external_job_id,
            "canonical_url": job.canonical_url,
            "company": job.company,
            "title": job.title,
            "description": job.description,
            "responsibilities": job.responsibilities,
            "location": job.location,
            "work_mode": job.work_mode,
            "employment_type": job.employment_type,
            "salary": job.salary,
            "published_at": job.published_at,
            "closed_at": job.closed_at,
            "status": job.status,
            "content_hash": job.content_hash,
        }
        if job.first_seen_at is not None:
            kwargs["first_seen_at"] = job.first_seen_at
        if job.last_seen_at is not None:
            kwargs["last_seen_at"] = job.last_seen_at
        if job.created_at is not None:
            kwargs["created_at"] = job.created_at
        if job.updated_at is not None:
            kwargs["updated_at"] = job.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<JobModel id={self.id} company={self.company!r} title={self.title!r}>"


class RawJobModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the immutable raw_jobs table."""

    __tablename__ = "raw_jobs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    job: Mapped[JobModel] = relationship(
        "JobModel",
        back_populates="raw_jobs",
    )
    source: Mapped[SourceModel] = relationship("SourceModel")

    def to_domain(self) -> RawJob:
        """Convert ORM model to domain entity."""
        return RawJob(
            id=self.id,
            job_id=self.job_id,
            source_id=self.source_id,
            raw_content=self.raw_content,
            content_type=self.content_type,
            fetched_at=self.fetched_at,
        )

    @classmethod
    def from_domain(cls, raw_job: RawJob) -> RawJobModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": raw_job.id,
            "job_id": raw_job.job_id,
            "source_id": raw_job.source_id,
            "raw_content": raw_job.raw_content,
            "content_type": raw_job.content_type,
        }
        if raw_job.fetched_at is not None:
            kwargs["fetched_at"] = raw_job.fetched_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<RawJobModel id={self.id} content_type={self.content_type!r}>"
