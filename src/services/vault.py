"""Vault: Agent identity material, stored Mandates, and denylist."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models.mandate import Mandate, OrderItem, Protocol
from src.utils.crypto import InvalidToken, sign_jwt, unverified_header, verify_jwt


class VaultError(Exception):
    """Identity, expiry, revocation, or denylist Refusal."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


class Vault:
    """SQLite-backed Vault. Pass `db_path` so tests can use a temp file."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def register_agent(self, agent_id: str, public_key_pem: str) -> None:
        """Store an Agent's ES256 public key."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO agents (agent_id, public_key_pem, created_at) VALUES (?, ?, ?)",
                    (agent_id, public_key_pem, _now_iso()),
                )
        except sqlite3.IntegrityError as exc:
            raise VaultError("duplicate_agent") from exc

    def store_mandate(self, mandate: Mandate) -> None:
        """Persist an active Mandate."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO mandates (mandate_id, agent_id, payload_json, status, expires_at, created_at)
                VALUES (?, ?, ?, 'active', ?, ?)
                """,
                (
                    mandate.mandate_id,
                    mandate.agent_id,
                    mandate.model_dump_json(),
                    mandate.expires_at.astimezone(timezone.utc).isoformat(),
                    _now_iso(),
                ),
            )

    def verify_signature(self, token: str) -> Mandate:
        """Verify an Agent-signed Mandate JWT and rebuild the Mandate from claims."""
        try:
            header = unverified_header(token)
        except InvalidToken as exc:
            raise VaultError(exc.reason_code) from exc
        agent_id = header.get("kid")
        if not isinstance(agent_id, str) or not agent_id:
            raise VaultError("missing_agent_id")
        public_key_pem = self._public_key(agent_id)
        try:
            claims = verify_jwt(token, public_key_pem)
        except InvalidToken as exc:
            raise VaultError(exc.reason_code) from exc
        if claims.get("sub") != agent_id:
            raise VaultError("invalid_signature")
        return _mandate_from_claims(claims)

    def validate_mandate(self, mandate: Mandate) -> Mandate:
        """Check registration, denylist, storage, revocation, and TTL. Not Guardrails."""
        if self.is_denied(mandate.agent_id):
            raise VaultError("denied")
        if self._public_key_or_none(mandate.agent_id) is None:
            raise VaultError("unknown_agent")
        row = self._mandate_row(mandate.mandate_id)
        if row is None:
            raise VaultError("unknown_mandate")
        if row["status"] != "active":
            raise VaultError("revoked")
        if mandate.expires_at.astimezone(timezone.utc) <= datetime.now(timezone.utc):
            raise VaultError("expired")
        return mandate

    def revoke_mandate(self, mandate_id: str) -> None:
        """Mark a stored Mandate revoked."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE mandates SET status = 'revoked' WHERE mandate_id = ?",
                (mandate_id,),
            )
            if cur.rowcount == 0:
                raise VaultError("unknown_mandate")

    def add_to_denylist(self, agent_id: str, reason: str = "") -> None:
        """Deny an Agent. Upserts the reason."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO denylist (agent_id, reason, created_at) VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET reason = excluded.reason
                """,
                (agent_id, reason, _now_iso()),
            )

    def is_denied(self, agent_id: str) -> bool:
        """True if the Agent is on the denylist."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM denylist WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return row is not None

    def sign_mandate(self, mandate: Mandate, private_pem: str) -> str:
        """Sign Mandate claims with the Agent's private key (tests and callers)."""
        return sign_jwt(_claims_from_mandate(mandate), private_pem, kid=mandate.agent_id)

    def _init_schema(self) -> None:
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
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS denylist (
                    agent_id TEXT PRIMARY KEY,
                    reason TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _public_key(self, agent_id: str) -> str:
        pem = self._public_key_or_none(agent_id)
        if pem is None:
            raise VaultError("unknown_agent")
        return pem

    def _public_key_or_none(self, agent_id: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT public_key_pem FROM agents WHERE agent_id = ?",
                (agent_id,),
            ).fetchone()
        return None if row is None else row["public_key_pem"]

    def _mandate_row(self, mandate_id: str) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute(
                "SELECT mandate_id, agent_id, payload_json, status, expires_at FROM mandates WHERE mandate_id = ?",
                (mandate_id,),
            ).fetchone()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _claims_from_mandate(mandate: Mandate) -> dict[str, Any]:
    return {
        "sub": mandate.agent_id,
        "mandate_id": mandate.mandate_id,
        "max_amount_paise": mandate.max_amount_paise,
        "sku_allowlist": mandate.sku_allowlist,
        "exp": int(mandate.expires_at.timestamp()),
        "protocol": mandate.protocol.value,
        "items": [item.model_dump() for item in mandate.items],
        "currency": mandate.currency,
        "user_id": mandate.user_id,
    }


def _mandate_from_claims(claims: dict[str, Any]) -> Mandate:
    items = [OrderItem.model_validate(item) for item in claims.get("items") or []]
    return Mandate(
        mandate_id=str(claims["mandate_id"]),
        agent_id=str(claims["sub"]),
        user_id=claims.get("user_id"),
        protocol=Protocol(claims["protocol"]),
        max_amount_paise=int(claims["max_amount_paise"]),
        currency=str(claims.get("currency") or "INR"),
        sku_allowlist=list(claims["sku_allowlist"]),
        expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc),
        items=items,
    )
