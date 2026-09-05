#!/usr/bin/env python
"""Integration tests for Razorpay webhook handler."""

import json
import os

import pytest
from fastapi.testclient import TestClient


def _make_webhook_payload(event: str = "payment.captured", payment_id: str = "pay_test123", order_id: str = "order_test456"):
    """Create a mock Razorpay webhook payload."""
    return {
        "event": event,
        "created_at": 1699999999,
        "payload": {
            "payment": {
                "entity": {
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
            }
        }
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


@pytest.fixture(autouse=True)
def clear_idempotency_keys():
    """Clear idempotency keys before each test."""
    from src.main import _idempotency_keys
    _idempotency_keys.clear()
    yield


def test_webhook_valid_signature():
    """Test webhook with valid signature returns success."""
    from src.main import app
    
    client = TestClient(app)
    
    payload = _make_webhook_payload()
    body = json.dumps(payload)
    signature = _sign_payload(body, "test_webhook_secret")
    
    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"X-Razorpay-Signature": signature},
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"


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
    assert response1.json()["status"] == "success"
    
    # Second request with same payload (same order_id -> same mandate_id)
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
    assert response1.json()["status"] == "success"
    
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
    assert response2.json()["status"] == "success"  # Different mandate_id due to event type


if __name__ == "__main__":
    pytest.main([__file__, "-v"])