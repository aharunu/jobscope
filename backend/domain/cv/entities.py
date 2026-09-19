"""CV domain entity."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.domain.cv.enums import CVStatus


@dataclass(slots=True)
class CV:
    """Domain entity representing a candidate's uploaded CV and parsed profile draft.

    Pure Python representation completely decoupled from persistence or ORM frameworks.
    """

    base_profile_id: uuid.UUID
    filename: str
    file_type: str
    raw_content: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    parsed_data: dict[str, Any] = field(default_factory=dict)
    status: CVStatus = CVStatus.PENDING_REVIEW
    created_at: datetime | None = None
