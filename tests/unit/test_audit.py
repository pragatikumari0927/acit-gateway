"""Unit tests for C7 Audit Logger SHA-256 hash chain."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_audit_hash_chain_genesis(tmp_path):
    """First entry's previous_hash must be 64 zeros; chain verifies."""
    from src.services.audit import AuditLogger, GENESIS_HASH

    db = tmp_path / "a1.db"
    audit = AuditLogger(db)
    eid = await audit.log_entry(
        {"action": "payment.create", "outcome": "ok", "agent_id": "agent-1"}
    )
    assert eid
    assert await audit.verify_chain() is True
    # genesis previous_hash is 0*64
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    async with AsyncSession(audit.engine) as session:
        row = (await session.exec(select(__import__("src.db.models", fromlist=["AuditRow"]).AuditRow))).first()
    assert row.previous_hash == GENESIS_HASH


@pytest.mark.asyncio
async def test_audit_hash_chain_links(tmp_path):
    """Three entries chain correctly and verify."""
    from src.services.audit import AuditLogger

    db = tmp_path / "a2.db"
    audit = AuditLogger(db)
    for i in range(3):
        await audit.log_entry(
            {
                "action": "payment.create",
                "outcome": "ok" if i % 2 == 0 else "refusal",
                "agent_id": f"agent-{i}",
                "mandate_id": f"m-{i}",
            }
        )
    assert await audit.verify_chain() is True


@pytest.mark.asyncio
async def test_audit_hash_chain_tamper_detected(tmp_path):
    """Tampering with a stored entry's outcome must break verification."""
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession

    from src.db.models import AuditRow
    from src.services.audit import AuditLogger

    db = tmp_path / "a3.db"
    audit = AuditLogger(db)
    await audit.log_entry({"action": "payment.create", "outcome": "ok", "agent_id": "a1"})
    await audit.log_entry({"action": "payment.refund", "outcome": "ok", "agent_id": "a2"})

    # Tamper: change the second row's outcome directly in DB
    async with AsyncSession(audit.engine) as session:
        rows = (await session.exec(select(AuditRow).order_by(AuditRow.timestamp))).all()
        rows[1].outcome = "tampered"
        session.add(rows[1])
        await session.commit()

    assert await audit.verify_chain() is False
