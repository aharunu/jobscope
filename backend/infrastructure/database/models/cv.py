"""CV ORM persistence model."""

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
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.cv.entities import CV
from backend.domain.cv.enums import CVStatus
from backend.infrastructure.database.base import (
    Base,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from backend.infrastructure.database.models.base_profile import BaseProfileModel


class CVModel(Base, UUIDPrimaryKeyMixin):
    """SQLAlchemy ORM model for the cvs table."""

    __tablename__ = "cvs"

    base_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("base_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    raw_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    parsed_data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    status: Mapped[CVStatus] = mapped_column(
        SQLEnum(CVStatus, native_enum=False, length=50),
        default=CVStatus.PENDING_REVIEW,
        server_default=sa.text("'PENDING_REVIEW'"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # Relationships
    base_profile: Mapped[BaseProfileModel] = relationship(
        "BaseProfileModel",
        back_populates="cvs",
    )

    def to_domain(self) -> CV:
        """Convert ORM model instance to pure domain entity."""
        return CV(
            id=self.id,
            base_profile_id=self.base_profile_id,
            filename=self.filename,
            file_type=self.file_type,
            raw_content=self.raw_content,
            parsed_data=dict(self.parsed_data) if self.parsed_data else {},
            status=self.status,
            created_at=self.created_at,
        )

    @classmethod
    def from_domain(cls, cv: CV) -> CVModel:
        """Construct ORM model instance from pure domain entity."""
        kwargs: dict[str, Any] = {
            "id": cv.id,
            "base_profile_id": cv.base_profile_id,
            "filename": cv.filename,
            "file_type": cv.file_type,
            "raw_content": cv.raw_content,
            "parsed_data": cv.parsed_data,
            "status": cv.status,
        }
        if cv.created_at is not None:
            kwargs["created_at"] = cv.created_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        status_val = getattr(self.status, "value", self.status)
        return (
            f"<CVModel id={self.id} base_profile_id={self.base_profile_id} "
            f"filename={self.filename!r} status={status_val!r}>"
        )
