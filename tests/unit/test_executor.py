"""Unit tests for PaymentExecutor. Razorpay client is mocked; no live calls."""

from __future__ import annotations

import os
import random
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("RAZORPAY_KEY_ID", "rzp_test_key")
os.environ.setdefault("RAZORPAY_KEY_SECRET", "rzp_test_secret")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
os.environ.setdefault("JWT_SECRET", "this_is_a_32_character_secret_xx")
os.environ.setdefault("API_KEY", "test_api_key")

from src.models.mandate import Mandate, OrderItem, Protocol
from src.models.proposal import Proposal
from src.services.chaos import ChaosInjector


def _mandate() -> Mandate:
    return Mandate(
        mandate_id="m-ex-1",
        agent_id="agent-ex-1",
        protocol=Protocol.AP2,
        max_amount_paise=50_000,
        sku_allowlist=["SKU-001"],
        expires_at=datetime.now(UTC).replace(year=2035),
        currency="INR",
    )


def _proposal() -> Proposal:
    return Proposal(
        mandate_id="m-ex-1",
        merchant_id="m_test",
        items=[OrderItem(sku="SKU-001", quantity=1, unit_amount_paise=19900)],
        quoted_total_paise=19900,
        quoted_discount_paise=0,
    )


def _executor(client, chaos=None, capture: bool = False):
    from src.services.executor import PaymentExecutor

    return PaymentExecutor(client=client, chaos=chaos, capture=capture)


def test_create_order_calls_client():
    client = MagicMock()
    client.order.create.return_value = {"id": "order_test_1", "amount": 19900}
    ex = _executor(client)
    result = ex.create_order(19900, currency="INR", receipt="m-ex-1")
    client.order.create.assert_called_once()
    payload = client.order.create.call_args[0][0]
    assert payload["amount"] == 19900
    assert payload["currency"] == "INR"
    assert payload["receipt"] == "m-ex-1"
    assert result["id"] == "order_test_1"


def test_capture_payment_calls_client():
    client = MagicMock()
    client.payment.capture.return_value = {"id": "pay_test_1", "status": "captured"}
    ex = _executor(client)
    result = ex.capture_payment("pay_test_1", 19900)
    client.payment.capture.assert_called_once_with("pay_test_1", 19900)
    assert result["status"] == "captured"


def test_execute_creates_order_without_capture_by_default():
    client = MagicMock()
    client.order.create.return_value = {"id": "order_test_2", "amount": 19900}
    ex = _executor(client)
    result = ex.execute(_mandate(), _proposal())
    client.order.create.assert_called_once()
    client.payment.capture.assert_not_called()
    assert result["id"] == "order_test_2"


def test_execute_chaos_create_raises():
    client = MagicMock()
    chaos = ChaosInjector(enabled=True, failure_rate=1.0, rng=random.Random(0))
    ex = _executor(client, chaos=chaos)
    with pytest.raises(TimeoutError):
        ex.execute(_mandate(), _proposal())
    client.order.create.assert_not_called()


def test_disabled_chaos_does_not_block_create():
    client = MagicMock()
    client.order.create.return_value = {"id": "order_ok"}
    chaos = ChaosInjector(enabled=False, failure_rate=1.0, rng=random.Random(0))
    ex = _executor(client, chaos=chaos)
    result = ex.create_order(100)
    assert result["id"] == "order_ok"
    client.order.create.assert_called_once()


def test_rejects_non_test_key(monkeypatch):
    from src.services.executor import PaymentExecutor

    monkeypatch.setattr(
        "src.services.executor.settings",
        type("S", (), {"RAZORPAY_KEY_ID": "rzp_live_xxx", "RAZORPAY_KEY_SECRET": "x"})(),
    )
    with pytest.raises(RuntimeError, match="TEST MODE"):
        PaymentExecutor(client=MagicMock())
