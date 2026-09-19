"""User ORM persistence model."""

from __future__ import annotations

from typing import Any

from backend.domain.user.entities import User
from backend.infrastructure.database.base import BaseModel


class UserModel(BaseModel):
    """SQLAlchemy ORM model for the users table."""

    __tablename__ = "users"

    def to_domain(self) -> User:
        """Convert ORM model to domain entity."""
        return User(
            id=self.id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_domain(cls, user: User) -> UserModel:
        """Construct ORM model from domain entity."""
        kwargs: dict[str, Any] = {"id": user.id}
        if user.created_at is not None:
            kwargs["created_at"] = user.created_at
        if user.updated_at is not None:
            kwargs["updated_at"] = user.updated_at
        return cls(**kwargs)

    def __repr__(self) -> str:
        return f"<UserModel id={self.id}>"
