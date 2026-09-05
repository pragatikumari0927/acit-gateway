"""Durable webhook idempotency store (H2).

SQLite-backed on the same db_path seam as Vault/Audit. Stores event ids only.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.core import make_engine
from src.db.models import IdempotencyRow


class IdempotencyStore:
    """SQLite-backed event-id dedup. db_path injected."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = make_engine(self.db_path)
        self._schema_initialized = False

    @staticmethod
    def _create_table(sync_conn: object) -> None:
        IdempotencyRow.__table__.create(sync_conn, checkfirst=True)

    async def _ensure_schema_once(self) -> None:
        if self._schema_initialized:
            return
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(self._create_table)
        except OperationalError as exc:
            if "already exists" not in str(exc).lower():
                raise
        self._schema_initialized = True

    async def seen(self, event_id: str) -> bool:
        """Return True if this event_id was already marked."""
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            row = await session.get(IdempotencyRow, event_id)
        return row is not None

    async def mark(self, event_id: str) -> None:
        """Record event_id. Unique-constraint and SQLite lock races are absorbed."""
        await self._ensure_schema_once()
        now = datetime.now(UTC).isoformat()
        last_error: Exception | None = None
        for _ in range(5):
            async with AsyncSession(self.engine) as session:
                session.add(IdempotencyRow(event_id=event_id, created_at=now))
                try:
                    await session.commit()
                    return
                except IntegrityError:
                    await session.rollback()
                    return
                except OperationalError as exc:
                    await session.rollback()
                    last_error = exc
                    text = str(exc).lower()
                    if "locked" not in text and "busy" not in text:
                        raise
            if await self.seen(event_id):
                return
        if last_error is not None:
            raise last_error
