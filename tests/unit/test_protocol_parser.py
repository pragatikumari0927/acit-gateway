"""Unit tests for C1 Protocol Abstraction (TDD vertical slices).

Tests hit only public seams: Mandate model + parse_envelope / parse_* functions.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.mandate import InternalMandate, Mandate, OrderItem, Protocol
from src.services.protocol_parser import ProtocolParseError, parse_envelope


def test_mandate_valid_construction_and_alias():
    """Happy construction of Mandate with OrderItem and InternalMandate alias."""
    item = OrderItem(sku="SKU-1", quantity=2, unit_amount_paise=100)
    m = Mandate(
        mandate_id="mandate-001",
        agent_id="agent-001",
        protocol=Protocol.AP2,
        max_amount_paise=5000,
        currency="INR",
        sku_allowlist=["SKU-1"],
        expires_at=datetime.now(UTC),
        items=[item],
    )
    assert m.mandate_id == "mandate-001"
    assert m.agent_id == "agent-001"
    assert m.protocol == Protocol.AP2
    assert m.max_amount_paise == 5000
    assert m.sku_allowlist == ["SKU-1"]
    assert len(m.items) == 1
    assert m.items[0].sku == "SKU-1"
    assert InternalMandate is Mandate


def test_mandate_field_validation_rejects_bad_quantity():
    """OrderItem quantity must be > 0 (Field(gt=0))."""
    with pytest.raises(ValidationError) as exc:
        OrderItem(sku="SKU-2", quantity=0, unit_amount_paise=100)
    assert "greater than 0" in str(exc.value) or "gt" in str(exc.value).lower()


def test_mandate_requires_nonempty_sku_allowlist():
    """sku_allowlist must have min_length=1."""
    with pytest.raises(ValidationError):
        Mandate(
            mandate_id="mandate-002",
            agent_id="agent-002",
            protocol=Protocol.TAP,
            max_amount_paise=1000,
            sku_allowlist=[],  # invalid
            expires_at=datetime.now(UTC),
        )


def test_mandate_rejects_negative_max_amount():
    """max_amount_paise must be >= 0."""
    with pytest.raises(ValidationError):
        Mandate(
            mandate_id="mandate-003",
            agent_id="agent-003",
            protocol=Protocol.P3P,
            max_amount_paise=-1,
            sku_allowlist=["SKU-3"],
            expires_at=datetime.now(UTC),
        )


# --- Slice 1.2: parse_envelope dispatch + ProtocolParseError (red now) ---


def test_parse_envelope_unknown_protocol_raises_with_reason_code():
    """Unknown protocol string must raise ProtocolParseError with reason_code."""
    with pytest.raises(ProtocolParseError) as exc:
        parse_envelope("unknown-proto", {})
    assert getattr(exc.value, "reason_code", None) == "unknown_protocol"


def test_parse_envelope_invalid_envelope_raises():
    """Non-dict or structurally invalid envelope raises with reason_code."""
    with pytest.raises(ProtocolParseError) as exc:
        parse_envelope(Protocol.AP2, None)
    assert getattr(exc.value, "reason_code", None) is not None
    assert "invalid" in str(exc.value.reason_code).lower() or exc.value.reason_code


def test_parse_ap2_valid_returns_mandate():
    """parse_ap2 (via dispatch) produces a valid Mandate for a minimal AP2 envelope."""
    envelope = {
        "mandate_id": "m-ap2-001",
        "agent_id": "agent-ap2-001",
        "max_amount_paise": 10000,
        "sku_allowlist": ["SKU-42"],
        "expires_at": "2026-10-01T00:00:00+00:00",
        "items": [
            {"sku": "SKU-42", "quantity": 3, "unit_amount_paise": 2500, "name": "Test Item"},
        ],
    }
    m = parse_envelope(Protocol.AP2, envelope)
    assert m.protocol == Protocol.AP2
    assert m.mandate_id == "m-ap2-001"
    assert m.agent_id == "agent-ap2-001"
    assert m.max_amount_paise == 10000
    assert "SKU-42" in m.sku_allowlist
    assert len(m.items) == 1
    assert m.items[0].quantity == 3


def test_parse_tap_p3p_uap_dispatch_to_mandate():
    """Other protocols dispatch and produce Mandate with correct .protocol."""
    base = {
        "mandate_id": "m-x",
        "agent_id": "a-x",
        "max_amount_paise": 100,
        "sku_allowlist": ["S"],
        "expires_at": "2030-01-01T00:00:00+00:00",
    }
    for proto in (Protocol.TAP, Protocol.P3P, Protocol.UAP):
        m = parse_envelope(proto, base)
        assert m.protocol == proto


def test_parse_envelope_missing_required_field_raises_reason_code():
    """Missing mandate_id or agent_id produces specific reason_code."""
    bad = {"max_amount_paise": 10, "sku_allowlist": ["S"], "expires_at": "2030-01-01T00:00:00Z"}
    with pytest.raises(ProtocolParseError) as exc:
        parse_envelope(Protocol.AP2, bad)
    assert exc.value.reason_code == "missing_required_field"


def test_parse_envelope_missing_expires_at_raises_reason_code():
    """Missing expires_at must raise ProtocolParseError, not default to now()."""
    bad = {
        "mandate_id": "m-no-exp",
        "agent_id": "a-no-exp",
        "max_amount_paise": 10,
        "sku_allowlist": ["S"],
    }
    with pytest.raises(ProtocolParseError) as exc:
        parse_envelope(Protocol.AP2, bad)
    assert exc.value.reason_code == "missing_expires_at"
