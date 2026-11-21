"""Unit tests for webhook Mandate lookup, event keys, and payment transitions."""

from datetime import UTC, datetime, timedelta

import pytest

from src.models.mandate import Mandate, Protocol
from src.services.audit import AuditLogger
from src.services.vault import Vault
from src.services.webhook_apply import apply_verified_event, event_idempotency_key, resolve_mandate_id


def test_resolve_prefers_notes_mandate_id():
    assert (
        resolve_mandate_id(
            {"order_id": "order_rzp", "notes": {"mandate_id": "man_1"}}
        )
        == "man_1"
    )


def test_resolve_falls_back_to_order_id():
    assert resolve_mandate_id({"order_id": "order_rzp"}) == "order_rzp"


def test_resolve_missing_ids_is_none():
    assert resolve_mandate_id({"id": "pay_only"}) is None


def test_event_key_uses_event_and_order():
    key = event_idempotency_key(
        {
            "event": "payment.captured",
            "payload": {"payment": {"entity": {"order_id": "order_1", "id": "pay_1"}}},
        }
    )
    assert key == "payment.captured:order_1"


def test_event_key_tolerates_non_dict_payment():
    key = event_idempotency_key(
        {"event": "payment.captured", "payload": {"payment": "x"}, "created_at": 1}
    )
    assert key == "payment.captured_1"


def _future():
    return datetime.now(UTC) + timedelta(days=3650)


def _mandate(mandate_id: str = "man_pay") -> Mandate:
    return Mandate(
        mandate_id=mandate_id,
        agent_id="agent-wh-unit",
        protocol=Protocol.AP2,
        max_amount_paise=50_000,
        sku_allowlist=["SKU-001"],
        expires_at=_future(),
    )


def _payload(event: str, mandate_id: str, payment_id: str) -> dict:
    return {
        "event": event,
        "created_at": 1699999999,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": mandate_id,
                    "notes": {"mandate_id": mandate_id},
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_failed_event_does_not_overwrite_captured_payment(tmp_path):
    db = tmp_path / "wh-order.db"
    vault = Vault(db)
    audit = AuditLogger(db)
    await vault.store_mandate(_mandate("man_cap"))

    captured = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=_payload("payment.captured", "man_cap", "pay_ok"),
        event_id="payment.captured:man_cap",
    )
    assert captured == {"status": "applied"}

    failed = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=_payload("payment.failed", "man_cap", "pay_late"),
        event_id="payment.failed:man_cap",
    )
    assert failed == {"status": "not_applied", "reason": "already_captured"}

    stored = await vault.get_mandate("man_cap")
    assert stored is not None
    assert stored.payment_status == "captured"
    assert stored.last_payment_id == "pay_ok"


@pytest.mark.asyncio
async def test_captured_event_can_follow_failed_payment(tmp_path):
    db = tmp_path / "wh-promote.db"
    vault = Vault(db)
    audit = AuditLogger(db)
    await vault.store_mandate(_mandate("man_fail"))

    failed = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=_payload("payment.failed", "man_fail", "pay_fail"),
        event_id="payment.failed:man_fail",
    )
    assert failed == {"status": "applied"}

    captured = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=_payload("payment.captured", "man_fail", "pay_ok"),
        event_id="payment.captured:man_fail",
    )
    assert captured == {"status": "applied"}

    stored = await vault.get_mandate("man_fail")
    assert stored is not None
    assert stored.payment_status == "captured"
    assert stored.last_payment_id == "pay_ok"


@pytest.mark.asyncio
async def test_payment_update_does_not_revert_other_mandate_fields(tmp_path):
    db = tmp_path / "wh-fields.db"
    vault = Vault(db)
    audit = AuditLogger(db)
    original = _mandate("man_fields")
    await vault.store_mandate(original)
    lowered = original.model_copy(update={"max_amount_paise": 1_000})
    await vault.store_mandate(lowered)

    result = await apply_verified_event(
        vault=vault,
        audit=audit,
        payload=_payload("payment.captured", "man_fields", "pay_fields"),
        event_id="payment.captured:man_fields",
    )
    assert result == {"status": "applied"}
    stored = await vault.get_mandate("man_fields")
    assert stored is not None
    assert stored.max_amount_paise == 1_000
    assert stored.payment_status == "captured"
    assert stored.last_payment_id == "pay_fields"
