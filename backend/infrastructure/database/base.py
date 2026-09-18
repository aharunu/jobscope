"""SQLAlchemy declarative base and common model mixins."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Top-level declarative base for all ORM entities in JobScope."""

    pass


class UUIDPrimaryKeyMixin:
    """Mixin for models using a UUID primary key.

    Uses PostgreSQL gen_random_uuid() as the server default and uuid.uuid4
    as the Python-side default.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(*args, **kwargs)


class TimestampMixin:
    """Mixin for models that track creation and update timestamps with timezone."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Abstract base model providing UUID primary key and timestamp tracking."""

    __abstract__ = True

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
