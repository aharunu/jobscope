"""Short Source reads and cross-worker admission without an open SQL transaction."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.application.job_discovery.dtos import RuntimeSourceDTO
from backend.application.job_discovery.exceptions import SourceBusyError
from backend.domain.source.entities import Source
from backend.infrastructure.database.engine import get_engine
from backend.infrastructure.database.repositories.source_repository import (
    SQLAlchemySourceRepository,
)
from backend.infrastructure.database.session import get_session_factory


class SQLAlchemyRuntimeSourceProvider:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession] | None = None
    ) -> None:
        self._factory = session_factory or get_session_factory()

    async def get_crawlable_source(
        self, source_id: uuid.UUID
    ) -> RuntimeSourceDTO | None:
        source = await self.get_source(source_id)
        return (
            RuntimeSourceDTO.from_domain(source) if source and source.active else None
        )

    async def get_source(self, source_id: uuid.UUID) -> Source | None:
        async with self._factory() as session:
            source = await SQLAlchemySourceRepository(session).get_by_id(source_id)
            return source

    async def get_crawlable_sources(
        self,
        ats_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[RuntimeSourceDTO]:
        async with self._factory() as session:
            sources = await SQLAlchemySourceRepository(session).list_all(
                is_active=True,
                ats_type=ats_type,
                limit=limit,
                offset=offset,
            )
            return [RuntimeSourceDTO.from_domain(source) for source in sources]


class PostgreSQLCrawlAdmissionGuard:
    """Session lock on dedicated AUTOCOMMIT connection, held through finalization.

    Consumes one pool connection, but never a database transaction during HTTP.
    Invalidating on failed unlock prevents returning a locked session to the pool.
    """

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self._engine = engine or get_engine()

    @staticmethod
    def lock_key(source_id: uuid.UUID) -> int:
        digest = hashlib.sha256(b"jobscope:crawl:" + source_id.bytes).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    @asynccontextmanager
    async def hold(self, source_id: uuid.UUID) -> AsyncIterator[None]:
        async with self._engine.connect() as connection:
            connection = await connection.execution_options(
                isolation_level="AUTOCOMMIT"
            )
            acquired = False
            try:
                try:
                    acquired = bool(
                        await connection.scalar(
                            text("SELECT pg_try_advisory_lock(:key)"),
                            {"key": self.lock_key(source_id)},
                        )
                    )
                except BaseException:
                    # Cancellation/connection failure may arrive after the server
                    # acquired a lock but before the result was received.
                    await connection.invalidate()
                    raise
                if not acquired:
                    raise SourceBusyError()
                yield
            finally:
                if acquired:
                    try:
                        released = await connection.scalar(
                            text("SELECT pg_advisory_unlock(:key)"),
                            {"key": self.lock_key(source_id)},
                        )
                        if not released:
                            await connection.invalidate()
                    except BaseException:
                        await connection.invalidate()
                        raise
