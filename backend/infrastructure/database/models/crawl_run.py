"""CrawlRun and CrawlRunJob ORM persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.crawl.entities import (
    CrawlRun,
    CrawlRunJob,
)
from backend.domain.crawl.enums import (
    CrawlJobAction,
    CrawlStatus,
)
from backend.infrastructure.database.base import (
    Base,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.infrastructure.database.models.job import JobModel
    from backend.infrastructure.database.models.source import SourceModel


class CrawlRunModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the crawl_runs table."""

    __tablename__ = "crawl_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[CrawlStatus] = mapped_column(
        SQLEnum(CrawlStatus, native_enum=False, length=50),
        default=CrawlStatus.RUNNING,
        server_default=sa.text("'RUNNING'"),
        nullable=False,
        index=True,
    )
    jobs_found: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        nullable=False,
    )
    jobs_created: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        nullable=False,
    )
    jobs_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        nullable=False,
    )
    jobs_closed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        nullable=False,
    )
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    source: Mapped[SourceModel] = relationship(
        "SourceModel",
        back_populates="crawl_runs",
    )
    crawl_run_jobs: Mapped[list[CrawlRunJobModel]] = relationship(
        "CrawlRunJobModel",
        back_populates="crawl_run",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> CrawlRun:
        """Convert ORM model to domain entity."""
        source_name = None
        ats_type = None
        if "source" in self.__dict__ and self.source is not None:
            source_name = self.source.name
            ats_type = self.source.ats_type

        return CrawlRun(
            id=self.id,
            source_id=self.source_id,
            status=self.status,
            started_at=self.started_at,
            finished_at=self.finished_at,
            jobs_found=self.jobs_found,
            jobs_created=self.jobs_created,
            jobs_updated=self.jobs_updated,
            jobs_closed=self.jobs_closed,
            error_count=self.error_count,
            created_at=self.created_at,
            source_name=source_name,
            ats_type=ats_type,
        )

    @classmethod
    def from_domain(cls, run: CrawlRun) -> CrawlRunModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": run.id,
            "source_id": run.source_id,
            "status": run.status,
            "jobs_found": run.jobs_found,
            "jobs_created": run.jobs_created,
            "jobs_updated": run.jobs_updated,
            "jobs_closed": run.jobs_closed,
            "error_count": run.error_count,
            "finished_at": run.finished_at,
        }
        if run.started_at is not None:
            kwargs["started_at"] = run.started_at
        if run.created_at is not None:
            kwargs["created_at"] = run.created_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        status_val = getattr(self.status, "value", self.status)
        return (
            f"<CrawlRunModel id={self.id} source_id={self.source_id} "
            f"status={status_val!r}>"
        )


class CrawlRunJobModel(Base):
    """SQLAlchemy ORM model for the crawl_run_jobs association table."""

    __tablename__ = "crawl_run_jobs"

    crawl_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("crawl_runs.id", ondelete="CASCADE"),
        primary_key=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    action: Mapped[CrawlJobAction] = mapped_column(
        SQLEnum(CrawlJobAction, native_enum=False, length=50),
        nullable=False,
    )

    # Relationships
    crawl_run: Mapped[CrawlRunModel] = relationship(
        "CrawlRunModel",
        back_populates="crawl_run_jobs",
    )
    job: Mapped[JobModel] = relationship(
        "JobModel",
        back_populates="crawl_run_jobs",
    )

    def to_domain(self) -> CrawlRunJob:
        """Convert ORM model to domain entity."""
        canonical_url = None
        title = None
        company = None
        location = None
        job_status = None
        first_seen_at = None
        last_seen_at = None
        if "job" in self.__dict__ and self.job is not None:
            canonical_url = self.job.canonical_url
            title = self.job.title
            company = self.job.company
            location = self.job.location
            job_status = getattr(self.job.status, "value", str(self.job.status))
            first_seen_at = self.job.first_seen_at
            last_seen_at = self.job.last_seen_at

        return CrawlRunJob(
            crawl_run_id=self.crawl_run_id,
            job_id=self.job_id,
            action=self.action,
            canonical_url=canonical_url,
            title=title,
            company=company,
            location=location,
            job_status=job_status,
            first_seen_at=first_seen_at,
            last_seen_at=last_seen_at,
        )

    @classmethod
    def from_domain(cls, link: CrawlRunJob) -> CrawlRunJobModel:
        """Construct ORM model from domain entity."""
        return cls(
            crawl_run_id=link.crawl_run_id,
            job_id=link.job_id,
            action=link.action,
        )

    def __repr__(self) -> str:
        action_val = getattr(self.action, "value", self.action)
        return (
            f"<CrawlRunJobModel crawl_run_id={self.crawl_run_id} "
            f"job_id={self.job_id} action={action_val!r}>"
        )
