"""API dependencies package."""

from backend.interfaces.api.dependencies.database import DbSession, get_db_session

__all__ = ["DbSession", "get_db_session"]
