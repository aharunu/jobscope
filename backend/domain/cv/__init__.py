"""CV domain package."""

from backend.domain.cv.entities import CV
from backend.domain.cv.enums import CVStatus

__all__ = [
    "CV",
    "CVStatus",
]
