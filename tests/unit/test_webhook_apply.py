"""Unit tests for webhook Mandate lookup and event keys."""

from src.services.webhook_apply import event_idempotency_key, resolve_mandate_id


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
