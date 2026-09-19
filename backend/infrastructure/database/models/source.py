"""Source ORM persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.domain.source.entities import Source
from backend.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from backend.infrastructure.database.models.crawl_run import CrawlRunModel
    from backend.infrastructure.database.models.job import JobModel


class SourceModel(BaseModel):
    """SQLAlchemy ORM model for the sources table."""

    __tablename__ = "sources"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    company: Mapped[str | None] = mapped_column(String(150), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ats_type: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=sa.text("true"),
        nullable=False,
    )
    adapter_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    pagination_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    endpoint_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    rate_limit_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )

    # Relationships
    jobs: Mapped[list[JobModel]] = relationship(
        "JobModel",
        back_populates="source",
    )
    crawl_runs: Mapped[list[CrawlRunModel]] = relationship(
        "CrawlRunModel",
        back_populates="source",
        cascade="all, delete-orphan",
    )

    def to_domain(self) -> Source:
        """Convert ORM model to domain entity."""
        return Source(
            id=self.id,
            name=self.name,
            company=self.company,
            url=self.url,
            country=self.country,
            ats_type=self.ats_type,
            active=self.active,
            adapter_config=dict(self.adapter_config) if self.adapter_config else {},
            pagination_config=dict(self.pagination_config)
            if self.pagination_config
            else {},
            endpoint_config=dict(self.endpoint_config) if self.endpoint_config else {},
            rate_limit_config=dict(self.rate_limit_config)
            if self.rate_limit_config
            else {},
            metadata=dict(self.metadata_) if self.metadata_ else {},
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, source: Source) -> SourceModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {
            "id": source.id,
            "name": source.name,
            "company": source.company,
            "url": source.url,
            "country": source.country,
            "ats_type": source.ats_type,
            "active": source.active,
            "adapter_config": source.adapter_config,
            "pagination_config": source.pagination_config,
            "endpoint_config": source.endpoint_config,
            "rate_limit_config": source.rate_limit_config,
            "metadata_": source.metadata,
        }
        if source.created_at is not None:
            kwargs["created_at"] = source.created_at
        if source.updated_at is not None:
            kwargs["updated_at"] = source.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<SourceModel id={self.id} name={self.name!r} ats_type={self.ats_type!r}>"
        )
