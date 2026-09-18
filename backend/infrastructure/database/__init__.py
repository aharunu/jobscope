"""Database infrastructure package.

Exposes declarative base, common mixins, engine, session factory,
and health inspection utilities.
"""

from backend.infrastructure.database.base import (
    Base,
    BaseModel,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from backend.infrastructure.database.engine import (
    create_database_engine,
    dispose_engine,
    get_engine,
)
from backend.infrastructure.database.health import check_database_health
from backend.infrastructure.database.session import (
    create_session_factory,
    get_db_context,
    get_db_session,
    get_session_factory,
)

__all__ = [
    "Base",
    "BaseModel",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "create_database_engine",
    "get_engine",
    "dispose_engine",
    "create_session_factory",
    "get_session_factory",
    "get_db_session",
    "get_db_context",
    "check_database_health",
]
