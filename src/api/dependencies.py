"""FastAPI dependency injection for async DB sessions."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.db.core import get_session as _get_session


def _db_path_from_url(url: str) -> str:
    """Convert a sqlite URL to a filesystem path suitable for aiosqlite."""
    prefix = "sqlite+aiosqlite:///"
    if url.startswith(prefix):
        return url[len(prefix):]
    prefix2 = "sqlite:///"
    if url.startswith(prefix2):
        return url[len(prefix2):]
    return url


@lru_cache
def get_engine() -> AsyncEngine:
    from src.db.core import make_engine

    return make_engine(_db_path_from_url(settings.DATABASE_URL))


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in _get_session(get_engine()):
        yield session
