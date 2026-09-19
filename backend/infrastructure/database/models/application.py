"""Application tracking ORM persistence models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.application.entities import (
    Application,
    ApplicationStatusHistory,
)
from backend.domain.application.enums import ApplicationStatus
from backend.infrastructure.database.base import (
    Base,
    BaseModel,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.infrastructure.database.models.job import JobModel
    from backend.infrastructure.database.models.user import UserModel


class ApplicationModel(BaseModel):
    """SQLAlchemy ORM model for the applications table."""

    __tablename__ = "applications"

    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        default=ApplicationStatus.INTERESTED,
        server_default=sa.text("'INTERESTED'"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "user_id",
            name="uq_applications_job_user",
        ),
    )

    # Relationships
    job: Mapped[JobModel] = relationship(
        "JobModel",
        back_populates="applications",
    )
    user: Mapped[UserModel] = relationship(
        "UserModel",
        back_populates="applications",
    )
    status_history: Mapped[list[ApplicationStatusHistoryModel]] = relationship(
        "ApplicationStatusHistoryModel",
        back_populates="application",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> Application:
        """Convert ORM model to domain entity."""
        return Application(
            id=self.id,
            job_id=self.job_id,
            user_id=self.user_id,
            status=self.status,
            notes=self.notes,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, app: Application) -> ApplicationModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": app.id,
            "job_id": app.job_id,
            "user_id": app.user_id,
            "status": app.status,
            "notes": app.notes,
        }
        if app.created_at is not None:
            kwargs["created_at"] = app.created_at
        if app.updated_at is not None:
            kwargs["updated_at"] = app.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        status_val = getattr(self.status, "value", self.status)
        return (
            f"<ApplicationModel id={self.id} status={status_val!r} "
            f"job_id={self.job_id}>"
        )


class ApplicationStatusHistoryModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the application_status_history table."""

    __tablename__ = "application_status_history"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        nullable=False,
    )
    to_status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False, length=50),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    application: Mapped[ApplicationModel] = relationship(
        "ApplicationModel",
        back_populates="status_history",
    )

    def to_domain(self) -> ApplicationStatusHistory:
        """Convert ORM model to domain entity."""
        return ApplicationStatusHistory(
            id=self.id,
            application_id=self.application_id,
            from_status=self.from_status,
            to_status=self.to_status,
            changed_at=self.changed_at,
        )

    @classmethod
    def from_domain(
        cls, hist: ApplicationStatusHistory
    ) -> ApplicationStatusHistoryModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": hist.id,
            "application_id": hist.application_id,
            "from_status": hist.from_status,
            "to_status": hist.to_status,
        }
        if hist.changed_at is not None:
            kwargs["changed_at"] = hist.changed_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        from_val = getattr(self.from_status, "value", self.from_status)
        to_val = getattr(self.to_status, "value", self.to_status)
        return (
            f"<ApplicationStatusHistoryModel id={self.id} "
            f"from_status={from_val!r} to_status={to_val!r}>"
        )
