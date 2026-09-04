"""Audit read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.dependencies import get_audit
from src.models.audit import AuditEntry
from src.services.audit import AuditLogger

router = APIRouter()


@router.get("/audit/mandate/{mandate_id}")
async def audit_for_mandate(
    mandate_id: str,
    audit: AuditLogger = Depends(get_audit),
) -> dict[str, list[AuditEntry] | str]:
    """Return the Audit chain slice for one Mandate, oldest first."""
    rows = await audit.get_chain(mandate_id)
    entries = [
        AuditEntry(
            entry_id=row.entry_id,
            timestamp=row.timestamp,
            agent_id=row.agent_id,
            mandate_id=row.mandate_id,
            action=row.action,
            outcome=row.outcome,
            request_hash=row.request_hash,
            response_hash=row.response_hash,
            metadata_json=row.metadata_json,
            previous_hash=row.previous_hash,
            entry_hash=row.entry_hash,
        )
        for row in rows
    ]
    return {"mandate_id": mandate_id, "entries": entries}


@router.get("/audit/export")
async def audit_export() -> dict[str, str | list]:
    """Full Audit export. Stub: chain verification lives on AuditLogger.verify_chain."""
    return {"status": "stub", "entries": []}
