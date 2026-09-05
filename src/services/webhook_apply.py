"""Apply verified Razorpay payment events to Mandate state and Audit.

HMAC and idempotency claim stay in the route. This module only runs after
a successful signature check and an atomic mark().
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.services.audit import AuditLogger
from src.services.vault import Vault

logger = logging.getLogger(__name__)

APPLYABLE_EVENTS = frozenset({"payment.captured", "payment.failed"})


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _payment_entity(payload: dict[str, Any]) -> dict[str, Any]:
    payment = _as_dict(_as_dict(payload.get("payload")).get("payment"))
    return _as_dict(payment.get("entity"))


def event_idempotency_key(payload: dict[str, Any]) -> str:
    """Stable event key: `{event_type}:{order_id or payment id}`."""
    event_type = payload.get("event")
    entity = _payment_entity(payload)
    base_id = entity.get("order_id") or entity.get("id")
    if base_id:
        return f"{event_type}:{base_id}"
    return f"{event_type}_{payload.get('created_at', '')}"


def resolve_mandate_id(entity: dict[str, Any]) -> str | None:
    """Prefer notes.mandate_id; fall back to order_id as Mandate id."""
    notes = entity.get("notes") or {}
    if isinstance(notes, dict):
        mid = notes.get("mandate_id")
        if mid:
            return str(mid)
    order_id = entity.get("order_id")
    if order_id:
        return str(order_id)
    return None


def _status_for_event(event_type: str) -> str:
    return "captured" if event_type == "payment.captured" else "failed"


async def apply_verified_event(
    *,
    vault: Vault,
    audit: AuditLogger,
    payload: dict[str, Any],
    event_id: str,
) -> dict[str, str]:
    """Update Mandate + Audit for a claimed payment event.

    Returns a 2xx body: applied, or not_applied with an explicit reason.
    Never logs the raw payload or webhook secret.
    """
    event_type = payload.get("event")
    if event_type not in APPLYABLE_EVENTS:
        logger.info(
            "webhook outcome event_id=%s event_type=%s outcome=not_applied",
            event_id,
            event_type,
        )
        return {"status": "not_applied", "reason": "unknown_event"}

    entity = _payment_entity(payload)
    mandate_id = resolve_mandate_id(entity)
    if not mandate_id:
        logger.info(
            "webhook outcome event_id=%s event_type=%s outcome=not_applied",
            event_id,
            event_type,
        )
        return {"status": "not_applied", "reason": "mandate_not_found"}

    mandate = await vault.get_mandate(mandate_id)
    if mandate is None:
        logger.info(
            "webhook outcome event_id=%s event_type=%s outcome=not_applied",
            event_id,
            event_type,
        )
        return {"status": "not_applied", "reason": "mandate_not_found"}

    payment_status = _status_for_event(str(event_type))
    payment_id = entity.get("id")
    updated = mandate.model_copy(
        update={
            "payment_status": payment_status,
            "last_payment_id": str(payment_id) if payment_id else None,
        }
    )
    await vault.store_mandate(updated)
    await audit.log_entry(
        {
            "action": "webhook.apply",
            "outcome": payment_status,
            "mandate_id": mandate.mandate_id,
            "agent_id": mandate.agent_id,
            "metadata_json": json.dumps(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "payment_id": payment_id,
                },
                separators=(",", ":"),
            ),
        }
    )
    logger.info(
        "webhook outcome event_id=%s event_type=%s outcome=applied",
        event_id,
        event_type,
    )
    return {"status": "applied"}
