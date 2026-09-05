#!/usr/bin/env python
"""Integration tests for Razorpay webhook handler."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from src.api import dependencies as deps
from src.models.mandate import Mandate, Protocol
from src.services.audit import AuditLogger
from src.services.idempotency import IdempotencyStore
from src.services.vault import Vault


def _make_webhook_payload(
    event: str = "payment.captured",
    payment_id: str = "pay_test123",
    order_id: str = "order_test456",
    notes: dict | None = None,
):
    """Create a mock Razorpay webhook payload."""
    entity = {
        "id": payment_id,
        "entity": "payment",
        "amount": 1000,
        "currency": "INR",
        "status": "captured",
        "order_id": order_id,
        "method": "card",
        "captured": True,
        "created_at": 1699999999,
    }
    if notes is not None:
        entity["notes"] = notes
    return {
        "event": event,
        "created_at": 1699999999,
        "payload": {"payment": {"entity": entity}},
    }


def _sign_payload(body: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for testing."""
    import hashlib
    import hmac
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=body.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()


# Set environment variables before importing app
os.environ["RAZORPAY_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["RAZORPAY_KEY_ID"] = "rzp_test_key"
os.environ["RAZORPAY_KEY_SECRET"] = "rzp_test_secret"
os.environ["MCP_ENABLED"] = "false"
os.environ["JWT_SECRET"] = "this_is_a_32_character_secret_xx"
os.environ["API_KEY"] = "your_api_key_for_service_to_service_auth"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"


def _future():
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(year=2035)


def _mandate(*, mandate_id: str = "order_test456") -> Mandate:
    return Mandate(
        mandate_id=mandate_id,
        agent_id="agent-wh-1",
        protocol=Protocol.AP2,
        max_amount_paise=50_000,
        sku_allowlist=["SKU-001"],
        expires_at=_future(),
    )


@pytest.fixture(autouse=True)
def isolated_webhook_services(tmp_path):
    """One temp SQLite file for Vault, Audit, and idempotency."""
    from src.main import app

    db = tmp_path / "webhook.db"
    vault = Vault(db)
    audit = AuditLogger(db)
    store = IdempotencyStore(db)
    deps.get_idempotency.cache_clear()
    deps.get_vault.cache_clear()
    deps.get_audit.cache_clear()
    app.dependency_overrides[deps.get_idempotency] = lambda: store
    app.dependency_overrides[deps.get_vault] = lambda: vault
    app.dependency_overrides[deps.get_audit] = lambda: audit
    yield {"vault": vault, "audit": audit, "store": store}
    app.dependency_overrides.clear()
    deps.get_idempotency.cache_clear()
    deps.get_vault.cache_clear()
    deps.get_audit.cache_clear()


def _post_signed(client: TestClient, payload: dict, signature: str | None = None):
    body = json.dumps(payload)
    if signature is None:
        signature = _sign_payload(body, "test_webhook_secret")
    return client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )


def test_webhook_valid_signature():
    """Signed payload with no stored Mandate is 2xx not_applied."""
    from src.main import app

    client = TestClient(app)
    response = _post_signed(client, _make_webhook_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_applied"
    assert body["reason"] == "mandate_not_found"


def test_webhook_invalid_signature():
    """Test webhook with invalid signature returns 401."""
    from src.main import app
    
    client = TestClient(app)
    
    payload = _make_webhook_payload()
    body = json.dumps(payload)
    # Wrong signature
    signature = "invalid_signature"
    
    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )
    
    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]


def test_webhook_missing_signature():
    """Test webhook without signature header returns 400."""
    from src.main import app
    
    client = TestClient(app)
    
    payload = _make_webhook_payload()
    body = json.dumps(payload)
    
    response = client.post(
        "/webhooks/razorpay",
        content=body,
        # No X-Razorpay-Signature header
    )
    
    assert response.status_code == 400
    assert "Missing X-Razorpay-Signature header" in response.json()["detail"]


def test_webhook_idempotency():
    """Test webhook idempotency - duplicate payload returns already_processed."""
    from src.main import app
    
    client = TestClient(app)
    
    payload = _make_webhook_payload(payment_id="pay_idempotent123", order_id="order_idempotent123")
    body = json.dumps(payload)
    signature = _sign_payload(body, "test_webhook_secret")
    
    # First request
    response1 = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "not_applied"

    # Second request with same payload (same order_id -> same event key)
    response2 = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "already_processed"


def test_webhook_different_events_different_idempotency():
    """Test different events with same payment get different idempotency keys."""
    from src.main import app
    
    client = TestClient(app)
    
    # Event 1: payment.captured
    payload1 = _make_webhook_payload(event="payment.captured", payment_id="pay_same", order_id="order_same")
    body1 = json.dumps(payload1)
    sig1 = _sign_payload(body1, "test_webhook_secret")
    
    response1 = client.post(
        "/webhooks/razorpay",
        content=body1,
        headers={"X-Razorpay-Signature": sig1},
    )
    assert response1.status_code == 200
    assert response1.json()["status"] == "not_applied"

    # Event 2: payment.failed (different event type, same payment)
    payload2 = _make_webhook_payload(event="payment.failed", payment_id="pay_same", order_id="order_same")
    body2 = json.dumps(payload2)
    sig2 = _sign_payload(body2, "test_webhook_secret")

    response2 = client.post(
        "/webhooks/razorpay",
        content=body2,
        headers={"X-Razorpay-Signature": sig2},
    )
    assert response2.status_code == 200
    assert response2.json()["status"] == "not_applied"


def test_webhook_captured_updates_mandate_and_writes_audit(isolated_webhook_services):
    """Signed payment.captured applies Mandate state and a chained Audit row."""
    import asyncio

    from src.main import app

    vault = isolated_webhook_services["vault"]
    audit = isolated_webhook_services["audit"]
    mandate = _mandate(mandate_id="order_test456")
    asyncio.run(vault.store_mandate(mandate))

    client = TestClient(app)
    response = _post_signed(
        client,
        _make_webhook_payload(
            event="payment.captured",
            payment_id="pay_apply_1",
            order_id="order_test456",
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"

    stored = asyncio.run(vault.get_mandate("order_test456"))
    assert stored is not None
    assert stored.payment_status == "captured"
    assert stored.last_payment_id == "pay_apply_1"

    chain = asyncio.run(audit.get_chain("order_test456"))
    assert len(chain) == 1
    assert chain[0].action == "webhook.apply"
    assert chain[0].outcome == "captured"
    assert chain[0].mandate_id == "order_test456"
    assert chain[0].agent_id == "agent-wh-1"
    assert "pay_apply_1" in (chain[0].metadata_json or "")
    assert asyncio.run(audit.verify_chain()) is True


def test_webhook_captured_redelivery_is_single_apply(isolated_webhook_services):
    """Same signed event twice: one Mandate update, one Audit row, 2xx duplicate."""
    import asyncio

    from src.main import app

    vault = isolated_webhook_services["vault"]
    audit = isolated_webhook_services["audit"]
    asyncio.run(vault.store_mandate(_mandate(mandate_id="order_test456")))

    client = TestClient(app)
    payload = _make_webhook_payload(
        event="payment.captured",
        payment_id="pay_dup_1",
        order_id="order_test456",
    )
    first = _post_signed(client, payload)
    second = _post_signed(client, payload)

    assert first.status_code == 200
    assert first.json()["status"] == "applied"
    assert second.status_code == 200
    assert second.json()["status"] == "already_processed"

    stored = asyncio.run(vault.get_mandate("order_test456"))
    assert stored is not None
    assert stored.payment_status == "captured"
    assert stored.last_payment_id == "pay_dup_1"
    assert len(asyncio.run(audit.get_chain("order_test456"))) == 1
    assert asyncio.run(audit.verify_chain()) is True


def test_webhook_tampered_signature_leaves_state_untouched(isolated_webhook_services):
    """401 on bad HMAC: no Mandate change, no Audit, event unmarked."""
    import asyncio

    from src.main import app

    vault = isolated_webhook_services["vault"]
    audit = isolated_webhook_services["audit"]
    store = isolated_webhook_services["store"]
    asyncio.run(vault.store_mandate(_mandate(mandate_id="order_test456")))

    client = TestClient(app)
    payload = _make_webhook_payload(
        event="payment.captured",
        payment_id="pay_tamper_1",
        order_id="order_test456",
    )
    response = _post_signed(client, payload, signature="deadbeef" * 8)

    assert response.status_code == 401
    assert "Invalid webhook signature" in response.json()["detail"]

    stored = asyncio.run(vault.get_mandate("order_test456"))
    assert stored is not None
    assert stored.payment_status is None
    assert stored.last_payment_id is None
    assert asyncio.run(audit.get_chain("order_test456")) == []
    assert asyncio.run(store.seen("payment.captured:order_test456")) is False


def test_webhook_unknown_event_type_is_not_applied(isolated_webhook_services):
    """Unknown event type is 2xx not_applied and does not change Mandate/Audit."""
    import asyncio

    from src.main import app

    vault = isolated_webhook_services["vault"]
    audit = isolated_webhook_services["audit"]
    asyncio.run(vault.store_mandate(_mandate(mandate_id="order_test456")))

    client = TestClient(app)
    response = _post_signed(
        client,
        _make_webhook_payload(event="invoice.paid", order_id="order_test456"),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_applied"
    assert body["reason"] == "unknown_event"

    stored = asyncio.run(vault.get_mandate("order_test456"))
    assert stored is not None
    assert stored.payment_status is None
    assert asyncio.run(audit.get_chain("order_test456")) == []


def test_webhook_unknown_mandate_is_not_applied(isolated_webhook_services):
    """Missing Mandate is 2xx with an explicit not-applied reason, never 500."""
    from src.main import app

    client = TestClient(app)
    response = _post_signed(
        client,
        _make_webhook_payload(
            event="payment.failed",
            payment_id="pay_missing",
            order_id="order_does_not_exist",
        ),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_applied"
    assert body["reason"] == "mandate_not_found"


def test_webhook_malformed_json_after_valid_signature(isolated_webhook_services):
    """Malformed JSON after a valid HMAC is 2xx error and does not mark."""
    import asyncio

    from src.main import app

    store = isolated_webhook_services["store"]
    raw = '{"event": "payment.captured",'
    signature = _sign_payload(raw, "test_webhook_secret")

    client = TestClient(app)
    response = client.post(
        "/webhooks/razorpay",
        content=raw,
        headers={"X-Razorpay-Signature": signature},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["reason"] == "malformed_json"
    assert asyncio.run(store.seen("payment.captured:order_test456")) is False


def test_webhook_resolves_mandate_from_notes(isolated_webhook_services):
    """notes.mandate_id wins over Razorpay order_id for Mandate lookup."""
    import asyncio

    from src.main import app

    vault = isolated_webhook_services["vault"]
    asyncio.run(vault.store_mandate(_mandate(mandate_id="man_notes_1")))

    client = TestClient(app)
    response = _post_signed(
        client,
        _make_webhook_payload(
            event="payment.failed",
            payment_id="pay_notes_1",
            order_id="order_unrelated",
            notes={"mandate_id": "man_notes_1"},
        ),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    stored = asyncio.run(vault.get_mandate("man_notes_1"))
    assert stored is not None
    assert stored.payment_status == "failed"
    assert stored.last_payment_id == "pay_notes_1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])