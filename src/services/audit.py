"""Audit Logger (C7): SHA-256 hash-chained append-only event log.

Deterministic. No LLM. Each entry's `entry_hash = sha256(previous_hash + canonical_fields)`.
Genesis entry uses `previous_hash = "0" * 64`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.core import make_engine
from src.db.models import AuditRow

GENESIS_HASH = "0" * 64


def _canonical_fields(entry: dict[str, Any]) -> str:
    """Stable canonical form of audit-relevant fields for hashing."""
    payload = {
        "entry_id": entry["entry_id"],
        "timestamp": entry["timestamp"],
        "agent_id": entry.get("agent_id"),
        "mandate_id": entry.get("mandate_id"),
        "action": entry["action"],
        "outcome": entry["outcome"],
        "request_hash": entry.get("request_hash"),
        "response_hash": entry.get("response_hash"),
        "metadata_json": entry.get("metadata_json"),
        "previous_hash": entry["previous_hash"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _compute_entry_hash(entry: dict[str, Any]) -> str:
    return hashlib.sha256(
        (entry["previous_hash"] + _canonical_fields(entry)).encode("utf-8")
    ).hexdigest()


class AuditLogger:
    """Append-only SHA-256 hash-chained audit log backed by SQLite."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = make_engine(self.db_path)
        self._schema_initialized = False

    async def _ensure_schema_once(self) -> None:
        if self._schema_initialized:
            return
        from sqlmodel import SQLModel

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        self._schema_initialized = True

    async def _last_entry_hash(self, session: AsyncSession) -> str:
        stmt = select(AuditRow).order_by(AuditRow.timestamp.desc(), AuditRow.entry_id.desc())
        row = (await session.exec(stmt)).first()
        if row is None:
            return GENESIS_HASH
        return row.entry_hash

    async def log_entry(self, entry: dict[str, Any]) -> str:
        """Append an audit entry. Returns the entry_id.

        Required keys: action, outcome. Optional: agent_id, mandate_id,
        request_hash, response_hash, metadata_json, timestamp, entry_id.
        """
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            entry_id = entry.get("entry_id") or str(uuid.uuid4())
            timestamp = entry.get("timestamp") or datetime.now(UTC).isoformat()
            previous_hash = await self._last_entry_hash(session)
            record = {
                "entry_id": entry_id,
                "timestamp": timestamp,
                "agent_id": entry.get("agent_id"),
                "mandate_id": entry.get("mandate_id"),
                "action": entry["action"],
                "outcome": entry["outcome"],
                "request_hash": entry.get("request_hash"),
                "response_hash": entry.get("response_hash"),
                "metadata_json": entry.get("metadata_json"),
                "previous_hash": previous_hash,
            }
            record["entry_hash"] = _compute_entry_hash(record)
            session.add(AuditRow(**record))
            await session.commit()
        return entry_id

    async def verify_chain(self) -> bool:
        """Recompute every entry_hash; assert each matches stored and chains to previous."""
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            stmt = select(AuditRow).order_by(AuditRow.timestamp.asc(), AuditRow.entry_id.asc())
            rows = (await session.exec(stmt)).all()
        expected_prev = GENESIS_HASH
        for row in rows:
            record = {
                "entry_id": row.entry_id,
                "timestamp": row.timestamp,
                "agent_id": row.agent_id,
                "mandate_id": row.mandate_id,
                "action": row.action,
                "outcome": row.outcome,
                "request_hash": row.request_hash,
                "response_hash": row.response_hash,
                "metadata_json": row.metadata_json,
                "previous_hash": row.previous_hash,
            }
            if row.previous_hash != expected_prev:
                return False
            if _compute_entry_hash(record) != row.entry_hash:
                return False
            expected_prev = row.entry_hash
        return True

    async def get_full_chain(self) -> list[AuditRow]:
        """Return the complete Audit chain, oldest first."""
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            stmt = select(AuditRow).order_by(AuditRow.timestamp.asc(), AuditRow.entry_id.asc())
            return list((await session.exec(stmt)).all())

    async def get_chain(self, mandate_id: str) -> list[AuditRow]:
        """Return Audit rows for one Mandate, oldest first.

        Does not verify the global chain; use verify_chain() for that.
        """
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(AuditRow)
                .where(AuditRow.mandate_id == mandate_id)
                .order_by(AuditRow.timestamp.asc(), AuditRow.entry_id.asc())
            )
            return list((await session.exec(stmt)).all())
