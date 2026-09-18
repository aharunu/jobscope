"""Database health and connectivity check utility."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.infrastructure.database.engine import get_engine


async def check_database_health(
    engine: AsyncEngine | None = None,
) -> dict[str, Any]:
    """Verify database connectivity by executing a lightweight SELECT 1 query.

    Returns a structured health report without raising uncaught exceptions,
    allowing consumers to safely inspect database operational readiness.
    """
    if engine is None:
        engine = get_engine()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "reachable",
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "database": "unreachable",
            "error": str(exc),
        }
