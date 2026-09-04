"""Async DB engine + session factory with WAL pragmas for SQLite."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession


def make_engine(db_path: str | Path) -> AsyncEngine:
    """Create an async engine for SQLite with WAL pragmas applied on every connection."""
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, echo=False, future=True)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


async def get_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession bound to the given engine."""
    async with AsyncSession(engine) as session:
        yield session
