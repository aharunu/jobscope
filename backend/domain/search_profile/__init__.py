"""Search profile domain package."""

from backend.domain.search_profile.entities import SearchProfile
from backend.domain.search_profile.repositories import SearchProfileRepository

__all__ = ["SearchProfile", "SearchProfileRepository"]
