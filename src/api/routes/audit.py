"""Audit read routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_audit, require_audit_admin
from src.db.models import AuditRow
from src.models.audit import AuditEntry
from src.services.audit import AuditLogger

router = APIRouter()


def _to_audit_entry(row: AuditRow) -> AuditEntry:
    return AuditEntry(
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


@router.get("/audit/mandate/{mandate_id}")
async def audit_for_mandate(
    mandate_id: str,
    audit: AuditLogger = Depends(get_audit),
) -> dict[str, list[AuditEntry] | str]:
    """Return the Audit chain slice for one Mandate, oldest first."""
    rows = await audit.get_chain(mandate_id)
    entries = [_to_audit_entry(row) for row in rows]
    return {"mandate_id": mandate_id, "entries": entries}


@router.get("/audit/export", dependencies=[Depends(require_audit_admin)])
async def audit_export(
    audit: AuditLogger = Depends(get_audit),
) -> dict[str, bool | list[AuditEntry]]:
    """Return the verified full Audit chain to an audit-admin operator."""
    if not await audit.verify_chain():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Audit chain verification failed",
        )
    rows = await audit.get_full_chain()
    return {"chain_ok": True, "entries": [_to_audit_entry(row) for row in rows]}
