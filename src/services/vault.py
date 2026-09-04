"""Mandate Vault (C3): identity, storage, TTL/revocation/denylist.

Injected db_path only. Uses sqlite3 with asyncio.to_thread for async compatibility.
WAL pragmas applied on connection.
Public methods per spec — all async.
"""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.models.mandate import Mandate
from src.utils.crypto import verify_jwt


class VaultError(Exception):
    """Vault domain failure with reason_code."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


def _apply_wal_pragmas(conn: sqlite3.Connection) -> None:
    """Apply WAL pragmas for better concurrency."""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")


class Vault:
    """SQLite-backed store for agents + mandates + denylist. db_path injected."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._schema_initialized = False

    def _connect(self) -> sqlite3.Connection:
        """Create a new connection with WAL pragmas."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        _apply_wal_pragmas(conn)
        return conn

    async def _ensure_schema_once(self) -> None:
        """Create tables if they don't exist (called once)."""
        if self._schema_initialized:
            return
        await asyncio.to_thread(self._ensure_schema_sync)
        self._schema_initialized = True

    def _ensure_schema_sync(self) -> None:
        """Sync schema creation."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    public_key_pem TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS mandates (
                    mandate_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS denylist (
                    agent_id TEXT PRIMARY KEY,
                    added_at TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def _execute_sync(self, query: str, params: tuple = ()) -> None:
        """Execute a query without returning results (sync)."""
        with self._connect() as conn:
            conn.execute(query, params)
            conn.commit()

    async def _execute(self, query: str, params: tuple = ()) -> None:
        """Execute a query without returning results (async)."""
        await asyncio.to_thread(self._execute_sync, query, params)

    def _fetchone_sync(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute a query and return one row (sync)."""
        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    async def _fetchone(self, query: str, params: tuple = ()) -> sqlite3.Row | None:
        """Execute a query and return one row (async)."""
        return await asyncio.to_thread(self._fetchone_sync, query, params)

    async def register_agent(self, agent_id: str, public_key_pem: str) -> None:
        await self._ensure_schema_once()
        now = datetime.now(UTC).isoformat()
        await self._execute(
            "INSERT OR REPLACE INTO agents (agent_id, public_key_pem, created_at) VALUES (?,?,?)",
            (agent_id, public_key_pem, now),
        )

    async def store_mandate(self, mandate: Mandate) -> None:
        await self._ensure_schema_once()
        existing = await self._fetchone(
            "SELECT revoked FROM mandates WHERE mandate_id=?", (mandate.mandate_id,)
        )
        if existing and existing["revoked"]:
            raise VaultError("mandate_revoked")
        payload = mandate.model_dump_json()
        exp = mandate.expires_at.isoformat()
        await self._execute(
            "INSERT OR REPLACE INTO mandates (mandate_id, agent_id, payload, expires_at, revoked) VALUES (?,?,?,?,0)",
            (mandate.mandate_id, mandate.agent_id, payload, exp),
        )

    async def verify_signature(self, token: str, agent_id: str) -> dict[str, Any]:
        await self._ensure_schema_once()
        row = await self._fetchone(
            "SELECT public_key_pem FROM agents WHERE agent_id=?", (agent_id,)
        )
        if not row:
            raise VaultError("unknown_agent")
        pub = row["public_key_pem"]
        try:
            claims = verify_jwt(token, pub)
        except Exception as e:  # jwt errors
            raise VaultError("invalid_signature") from e
        if claims.get("sub") != agent_id:
            raise VaultError("invalid_signature")
        return claims

    async def validate_mandate(self, mandate_id: str) -> bool:
        await self._ensure_schema_once()
        row = await self._fetchone(
            "SELECT m.agent_id, m.expires_at, m.revoked, d.agent_id IS NOT NULL AS denied "
            "FROM mandates m LEFT JOIN denylist d ON m.agent_id = d.agent_id "
            "WHERE m.mandate_id = ?",
            (mandate_id,),
        )
        if not row:
            return False
        if row["revoked"]:
            return False
        if row["denied"]:
            return False
        try:
            exp = datetime.fromisoformat(row["expires_at"])
        except Exception:  # noqa: BLE001 - tolerate bad stored data
            return False
        return not (datetime.now(UTC) >= exp)

    async def revoke_mandate(self, mandate_id: str) -> None:
        await self._ensure_schema_once()
        await self._execute("UPDATE mandates SET revoked=1 WHERE mandate_id=?", (mandate_id,))

    async def is_denied(self, agent_id: str) -> bool:
        await self._ensure_schema_once()
        row = await self._fetchone("SELECT 1 FROM denylist WHERE agent_id=?", (agent_id,))
        return row is not None

    async def add_to_denylist(self, agent_id: str) -> None:
        await self._ensure_schema_once()
        now = datetime.now(UTC).isoformat()
        await self._execute("INSERT OR IGNORE INTO denylist (agent_id, added_at) VALUES (?,?)", (agent_id, now))