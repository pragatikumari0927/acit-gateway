"""Mandate Vault (C3): identity, storage, TTL/revocation/denylist.

SQLModel + aiosqlite-backed. db_path injected. Public methods per spec — all async.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.core import make_engine
from src.db.models import AgentRow, DenylistRow, MandateRow
from src.models.mandate import Mandate
from src.utils.crypto import verify_jwt


class VaultError(Exception):
    """Vault domain failure with reason_code."""

    def __init__(self, reason_code: str, message: str | None = None) -> None:
        self.reason_code = reason_code
        super().__init__(message or reason_code)


class Vault:
    """SQLite-backed store for agents + mandates + denylist. db_path injected."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = make_engine(self.db_path)
        self._schema_initialized = False

    async def _ensure_schema_once(self) -> None:
        """Create tables if they don't exist (called once)."""
        if self._schema_initialized:
            return
        from sqlmodel import SQLModel

        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        self._schema_initialized = True

    async def register_agent(self, agent_id: str, public_key_pem: str) -> None:
        await self._ensure_schema_once()
        now = datetime.now(UTC).isoformat()
        async with AsyncSession(self.engine) as session:
            existing = await session.get(AgentRow, agent_id)
            if existing:
                existing.public_key_pem = public_key_pem
                existing.created_at = now
            else:
                session.add(AgentRow(agent_id=agent_id, public_key_pem=public_key_pem, created_at=now))
            await session.commit()

    async def store_mandate(self, mandate: Mandate) -> None:
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            existing = await session.get(MandateRow, mandate.mandate_id)
            if existing and existing.revoked:
                raise VaultError("mandate_revoked")
            payload = mandate.model_dump_json()
            exp = mandate.expires_at.isoformat()
            if existing:
                existing.agent_id = mandate.agent_id
                existing.payload = payload
                existing.expires_at = exp
                existing.revoked = 0
            else:
                session.add(
                    MandateRow(
                        mandate_id=mandate.mandate_id,
                        agent_id=mandate.agent_id,
                        payload=payload,
                        expires_at=exp,
                        revoked=0,
                    )
                )
            await session.commit()

    async def verify_signature(self, token: str, agent_id: str) -> dict[str, Any]:
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            row = await session.get(AgentRow, agent_id)
        if not row:
            raise VaultError("unknown_agent")
        pub = row.public_key_pem
        try:
            claims = verify_jwt(token, pub)
        except Exception as e:  # jwt errors
            raise VaultError("invalid_signature") from e
        if claims.get("sub") != agent_id:
            raise VaultError("invalid_signature")
        return claims

    async def validate_mandate(self, mandate_id: str) -> bool:
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(
                    MandateRow.expires_at,
                    MandateRow.revoked,
                    DenylistRow.agent_id.is_not(None).label("denied"),
                )
                .where(MandateRow.mandate_id == mandate_id)
                .outerjoin(DenylistRow, MandateRow.agent_id == DenylistRow.agent_id)
            )
            row = (await session.execute(stmt)).first()
        if not row:
            return False
        if row.revoked:
            return False
        if row.denied:
            return False
        try:
            exp = datetime.fromisoformat(row.expires_at)
        except Exception:  # noqa: BLE001 - tolerate bad stored data
            return False
        return not (datetime.now(UTC) >= exp)

    async def revoke_mandate(self, mandate_id: str) -> None:
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            row = await session.get(MandateRow, mandate_id)
            if row:
                row.revoked = 1
                session.add(row)
                await session.commit()

    async def is_denied(self, agent_id: str) -> bool:
        await self._ensure_schema_once()
        async with AsyncSession(self.engine) as session:
            row = await session.get(DenylistRow, agent_id)
        return row is not None

    async def add_to_denylist(self, agent_id: str) -> None:
        await self._ensure_schema_once()
        now = datetime.now(UTC).isoformat()
        async with AsyncSession(self.engine) as session:
            existing = await session.get(DenylistRow, agent_id)
            if existing:
                existing.added_at = now
            else:
                session.add(DenylistRow(agent_id=agent_id, added_at=now))
            await session.commit()
