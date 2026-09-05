"""SQLModel table classes mirroring the existing raw sqlite3 schema.

Names use `*Row` suffix to avoid clashing with the Pydantic `Mandate` in src/models/mandate.py.
"""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class AgentRow(SQLModel, table=True):
    __tablename__ = "agents"

    agent_id: str = Field(primary_key=True)
    public_key_pem: str
    created_at: str


class MandateRow(SQLModel, table=True):
    __tablename__ = "mandates"

    mandate_id: str = Field(primary_key=True)
    agent_id: str
    payload: str
    expires_at: str
    revoked: int = Field(default=0)


class DenylistRow(SQLModel, table=True):
    __tablename__ = "denylist"

    agent_id: str = Field(primary_key=True)
    added_at: str


class IdempotencyRow(SQLModel, table=True):
    __tablename__ = "idempotency_keys"

    event_id: str = Field(primary_key=True)
    created_at: str


class AuditRow(SQLModel, table=True):
    __tablename__ = "audit"

    entry_id: str = Field(primary_key=True)
    timestamp: str
    agent_id: str | None = None
    mandate_id: str | None = None
    action: str
    outcome: str
    request_hash: str | None = None
    response_hash: str | None = None
    metadata_json: str | None = None
    previous_hash: str
    entry_hash: str
