"""User domain entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class User:
    """Domain representation of a user.

    Pure Python entity independent of persistence or ORM frameworks.
    """

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
    updated_at: datetime | None = None
