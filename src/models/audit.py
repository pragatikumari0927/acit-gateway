"""Pydantic AuditEntry mirroring AuditRow columns (C6)."""

from __future__ import annotations

from pydantic import BaseModel


class AuditEntry(BaseModel):
    """One hash-chained Audit event. Optional fields match AuditRow."""

    entry_id: str
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
