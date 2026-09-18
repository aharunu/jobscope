"""Database dependencies for FastAPI route handlers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.infrastructure.database.session import get_db_session

# Type-annotated dependency alias for clean controller signatures
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

__all__ = ["DbSession", "get_db_session"]
